"""
fetch_us_polls.py

  1. downloads the latest US pollster predictions CSV from the net
  2. runs the stan model
  3. stores the model output on Azure

Environment variables:
    AZURE_STORAGE_CONNECTION_STRING  — blob storage connection string
    US_POLLS_BLOB_CONTAINER          — container name, e.g. "polling-data"
    US_POLLS_OUTPUT_BLOB_NAME        — output blob, e.g. "us_polls_model_output.json"
    US_POLLS_ARCHIVE                 — "true"/"false", whether to keep dated archive copies
"""

from __future__ import annotations

import io
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from azure.storage.blob import BlobServiceClient, ContentSettings
from cmdstanpy import CmdStanModel, install_cmdstan
from scipy.special import softmax

logger = logging.getLogger(__name__)

# config
_CSV_URL = ( 
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vRsvXNCZ0ubJr8D_yNcU5q6C0_HBa35K7oDK03KpO7Ca43UwdXaIdvVLWoXEmHHph0EREz5430Hm5yZ"
    "/pub?output=csv"
)

_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
_CONTAINER         = os.environ.get("US_POLLS_BLOB_CONTAINER", "us-pollster-data")
_OUTPUT_BLOB_NAME  = os.environ.get("US_POLLS_OUTPUT_BLOB_NAME", "us_pollster_model_output.json")
_ARCHIVE           = os.environ.get("US_POLLS_ARCHIVE", "false").lower() == "true"
_REQUEST_TIMEOUT   = 60

PARTY_COLS = ["democrat", "republican", "other"]

STAN_MODEL = """
data {
  int<lower=1> N;
  int<lower=1> H;
  int<lower=1> G;
  int<lower=1> T;
  int<lower=2> K;

  array[N] int<lower=1, upper=H> h;
  array[N] int<lower=1, upper=G> g;
  array[N] int<lower=1, upper=T> t;

  array[N, K] int<lower=0> y;
}

parameters {
  vector[K - 1] alpha;

  array[K - 1] sum_to_zero_vector[H] house_raw;
  vector<lower=0>[K - 1] sigma_house;

  array[K - 1] sum_to_zero_vector[G] population_raw;
  vector<lower=0>[K - 1] sigma_population;

  array[K - 1] sum_to_zero_vector[T] time_raw;
  vector<lower=0>[K - 1] sigma_time;
}

transformed parameters {
  matrix[H, K - 1] house;
  matrix[G, K - 1] population;
  matrix[T, K - 1] time;

  for (k in 1:(K - 1)) {
    house[, k] = sigma_house[k] * house_raw[k];
    population[, k] = sigma_population[k] * population_raw[k];
    time[, k] = sigma_time[k] * time_raw[k];
  }
}

model {
  alpha ~ normal(0, 5);

  sigma_house ~ normal(0, 1);
  sigma_population ~ normal(0, 1);
  sigma_time ~ normal(0, 1);

  for (k in 1:(K - 1)) {
    house_raw[k] ~ normal(0, 1);
    population_raw[k] ~ normal(0, 1);
    time_raw[k][2:T] - time_raw[k][1:(T - 1)] ~ normal(0, 1);
  }

  for (i in 1:N) {
    vector[K] eta;

    for (k in 1:(K - 1)) {
      eta[k] =
        alpha[k]
        + house[h[i], k]
        + population[g[i], k]
        + time[t[i], k];
    }

    eta[K] = 0;

    y[i] ~ multinomial_logit(eta);
  }
}
"""


# step 1: download csv from url
def _download_csv(url: str) -> pd.DataFrame:
    logger.info("Downloading US polls CSV from %s", url)
    resp = requests.get(url, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    logger.info("Downloaded %d rows, %d columns", len(df), len(df.columns))
    return df


def _validate(df: pd.DataFrame) -> None:
    required = {"pollster", "startdate", "enddate", "samplesize", "dem", "rep"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Downloaded CSV is missing expected columns: {missing}")
    if len(df) == 0:
        raise ValueError("Downloaded CSV is empty.")


# step 2: prepare data 
def _prepare_stan_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    df = df.dropna(subset=["pollster", "startdate", "enddate", "samplesize", "dem", "rep"]).copy()

    df["start_date"] = pd.to_datetime(df["startdate"])
    df["end_date"]   = pd.to_datetime(df["enddate"])
    df["samplesize"] = df["samplesize"].round().astype(int)

    df["dem_share"]   = df["dem"] / 100
    df["rep_share"]   = df["rep"] / 100
    df["other_share"] = (1 - df["dem_share"] - df["rep_share"]).clip(lower=0)

    share_sum = df[["dem_share", "rep_share", "other_share"]].sum(axis=1)
    df["dem_share"]   /= share_sum
    df["rep_share"]   /= share_sum
    df["other_share"] /= share_sum

    df["democrat"]   = np.floor(df["samplesize"] * df["dem_share"]).astype(int)
    df["republican"] = np.floor(df["samplesize"] * df["rep_share"]).astype(int)
    df["other"]      = df["samplesize"] - df["democrat"] - df["republican"]

    df["population"] = df["population"].str.strip().str.upper()
    df["g"] = pd.factorize(df["population"])[0] + 1

    population_lookup = (
        df[["g", "population"]]
        .drop_duplicates()
        .sort_values("g")
    )

    daily_rows = []
    count_cols = ["samplesize"] + PARTY_COLS
    for _, row in df.iterrows():
        dates = pd.date_range(row["start_date"], row["end_date"], freq="D")
        ndays = len(dates)
        for d in dates:
            new_row = row.copy()
            new_row["date"] = d
            for col in count_cols:
                new_row[col] = row[col] / ndays
            daily_rows.append(new_row)

    daily_df = pd.DataFrame(daily_rows)

    first_date = daily_df["date"].min()
    last_date  = daily_df["date"].max()

    daily_df["week"] = ((daily_df["date"] - first_date).dt.days // 7).astype(int)

    all_weeks = pd.DataFrame({
        "week": range(0, ((last_date - first_date).days // 7) + 1)
    })
    all_weeks["week_start"] = first_date + pd.to_timedelta(all_weeks["week"] * 7, unit="D")
    all_weeks["week_end"]   = all_weeks["week_start"] + pd.Timedelta(days=6)
    all_weeks["week_label"] = (
        all_weeks["week_start"].dt.strftime("%d %b %Y")
        + " – "
        + all_weeks["week_end"].dt.strftime("%d %b %Y")
    )

    weekly_df = (
        daily_df
        .groupby(["pollster", "population", "week"], as_index=False)
        .agg(
            samplesize=("samplesize", "sum"),
            democrat=("democrat", "sum"),
            republican=("republican", "sum"),
            other=("other", "sum"),
        )
    )
    for col in ["samplesize"] + PARTY_COLS:
        weekly_df[col] = weekly_df[col].round().astype(int)

    week_to_t = {week: i + 1 for i, week in enumerate(all_weeks["week"])}
    weekly_df["h"] = pd.factorize(weekly_df["pollster"])[0] + 1
    weekly_df["t"] = weekly_df["week"].map(week_to_t).astype(int)
    weekly_df["g"] = pd.factorize(weekly_df["population"])[0] + 1

    stan_data = {
        "N": len(weekly_df),
        "H": weekly_df["h"].nunique(),
        "G": weekly_df["g"].nunique(),
        "T": len(all_weeks),
        "K": len(PARTY_COLS),
        "h": weekly_df["h"].astype(int).tolist(),
        "g": weekly_df["g"].astype(int).tolist(),
        "t": weekly_df["t"].astype(int).tolist(),
        "y": weekly_df[PARTY_COLS].astype(int).values.tolist(),
    }

    return weekly_df, all_weeks, week_to_t, stan_data, population_lookup


# step 3: run stan
def _run_model(stan_data: dict, population_lookup) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    install_cmdstan(version="2.36.0")

    stan_file = Path(tempfile.gettempdir()) / "us_polls_model.stan"
    stan_file.write_text(STAN_MODEL)

    model = CmdStanModel(stan_file=str(stan_file))
    fit = model.sample(
        data=stan_data,
        chains=4,
        iter_sampling=1000,
        iter_warmup=1000,
        seed=123,
    )

    alpha = fit.stan_variable("alpha")
    time  = fit.stan_variable("time")
    population = fit.stan_variable("population")

    lv_index = (
    population_lookup
        .query("population == 'LV'")
        .g
        .iloc[0]
        - 1
    )

    draws = alpha.shape[0]
    T = time.shape[1]
    K_minus_1 = alpha.shape[1]
    K = K_minus_1 + 1

    # reference category is the last party: Other
    eta = np.zeros((draws, T, K))

    for k in range(K_minus_1):
        eta[:, :, k] = (
            alpha[:, k, None]
            + time[:, :, k]
            + population[:, lv_index, k][:, None]
        )

    eta[:, :, K - 1] = 0

    p = softmax(eta, axis=2)

    p_mean = p.mean(axis=0)
    p_low  = np.quantile(p, 0.025, axis=0)
    p_high = np.quantile(p, 0.975, axis=0)

    return p_mean, p_low, p_high


# step 4: builf output payload + upload
def _build_output(
    p_mean: np.ndarray,
    p_low: np.ndarray,
    p_high: np.ndarray,
    weekly_df: pd.DataFrame,
    all_weeks: pd.DataFrame,
    week_to_t: dict,
) -> dict:
    """
    Serialise model output to a JSON-friendly dict.

    Shape of p_* arrays: (T, K) where K = [democrat, republican, other]
    """
    T = p_mean.shape[0]

    time_lookup = all_weeks.copy()
    time_lookup["t"] = time_lookup["week"].map(week_to_t)

    # observations for scatter overlay
    obs_rows = []
    for party in PARTY_COLS:
        tmp = weekly_df[["t", "pollster", party, "samplesize"]].copy()
        tmp["party"] = party
        tmp["share"] = (tmp[party] / tmp["samplesize"]).round(6)
        obs_rows.append(tmp[["t", "pollster", "party", "share"]])
    obs_df = pd.concat(obs_rows, ignore_index=True)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parties": PARTY_COLS,
        "T": T,
        "time_lookup": time_lookup[["t", "week_label"]].to_dict(orient="records"),
        "posterior": {
            party: {
                "mean": p_mean[:, k].round(6).tolist(),
                "low":  p_low[:, k].round(6).tolist(),
                "high": p_high[:, k].round(6).tolist(),
            }
            for k, party in enumerate(PARTY_COLS)
        },
        "observations": obs_df.to_dict(orient="records"),
    }


def _upload_json(payload: dict, blob_name: str) -> None:
    if not _CONNECTION_STRING:
        raise EnvironmentError("AZURE_STORAGE_CONNECTION_STRING is not set.")

    json_bytes = json.dumps(payload).encode("utf-8")

    client = BlobServiceClient.from_connection_string(_CONNECTION_STRING)
    container_client = client.get_container_client(_CONTAINER)

    if not container_client.exists():
        container_client.create_container()
        logger.info("Created blob container: %s", _CONTAINER)

    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(
        json_bytes,
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json"),
    )
    logger.info("Uploaded %d bytes → %s/%s", len(json_bytes), _CONTAINER, blob_name)


# entry point
def fetch_and_store_us_polls(
    url: str       = _CSV_URL,
    blob_name: str = _OUTPUT_BLOB_NAME,
    archive: bool  = _ARCHIVE,
) -> dict:
    """
    full pipeline: download CSV --> run Stan model --> upload output JSON to blob.

    returns the output payload dict so the caller can use it immediately if needed
    """

    # download
    raw_df = _download_csv(url)
    _validate(raw_df)

    # process innit
    logger.info("preparing data...")
    weekly_df, all_weeks, week_to_t, stan_data, population_lookup = _prepare_stan_data(raw_df)

    # model
    logger.info("running Stan model")
    p_mean, p_low, p_high = _run_model(stan_data, population_lookup)

    # make output
    payload = _build_output(p_mean, p_low, p_high, weekly_df, all_weeks, week_to_t)

    # upload
    _upload_json(payload, blob_name)

    # if archive env variable is true then archives
    if archive:
        stamp        = datetime.now(timezone.utc).strftime("%Y%m%d")
        archive_name = blob_name.replace(".json", f"_{stamp}.json")
        _upload_json(payload, archive_name)
        logger.info("archived copy stored as %s", archive_name)

    logger.info("US pollster pipeline doneeeeee.")
    return payload