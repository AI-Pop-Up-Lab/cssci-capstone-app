from __future__ import annotations

import io
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ── blob name helpers ────────────────────────────────────────────────────────

def _longitudinal_blob_name(country: str) -> str:
    return f"{country}/longitudinal/{country}_vote_shares.csv"

def _longitudinal_demographic_blob_name(country: str) -> str:
    return f"{country}/longitudinal/{country}_vote_shares_demographic.csv"

# ── column config ────────────────────────────────────────────────────────────

DEMOGRAPHIC_COLS = ["gender", "age_group", "municipality", "education_level"]
PARTY_COL        = "party"
WEIGHT_COL       = "prob_raked"

# ── internal helpers ─────────────────────────────────────────────────────────

def _download_csv_or_none(client, container: str, blob_name: str) -> pd.DataFrame | None:
    """Download a CSV blob and return as DataFrame, or None if it doesn't exist."""
    try:
        blob = client.get_container_client(container).get_blob_client(blob_name)
        data = blob.download_blob().readall().decode("utf-8")
        return pd.read_csv(io.StringIO(data))
    except Exception:
        return None


def _upload_csv(client, container: str, blob_name: str, df: pd.DataFrame) -> None:
    blob = client.get_container_client(container).get_blob_client(blob_name)
    blob.upload_blob(df.to_csv(index=False).encode("utf-8"), overwrite=True)


def _week_label(year: int, week: int) -> str:
    return f"{year}-W{week:02d}"


def _build_baseline_row(frame: pd.DataFrame, week: str) -> pd.DataFrame:
    """
    Aggregate a single week's extended frame into (week, party, share) rows.
    Excludes 'Did not vote' from the share denominator so shares sum to 100%
    across parties only — adjust if you want to include non-voters.
    """
    voting = frame[frame[PARTY_COL] != "Did not vote"].copy() # remove if 'did not vote' should be kept in longitudinal graph
    by_party = voting.groupby(PARTY_COL)[WEIGHT_COL].sum().reset_index()
    total = by_party[WEIGHT_COL].sum()
    by_party["share"] = (by_party[WEIGHT_COL] / total * 100).round(2)
    by_party["week"]  = week
    return by_party[["week", PARTY_COL, "share"]].rename(columns={PARTY_COL: "vote_choice"})


def _build_demographic_rows(frame: pd.DataFrame, week: str) -> pd.DataFrame:
    """
    Retain the full demographic breakdown for a single week.
    Keeps only the columns needed for client-side filtering.
    """
    cols = [PARTY_COL, WEIGHT_COL] + [c for c in DEMOGRAPHIC_COLS if c in frame.columns]
    out = frame[cols].copy()
    out["week"] = week
    out = out.rename(columns={PARTY_COL: "vote_choice", WEIGHT_COL: "weight"})
    return out[["week", "vote_choice"] + [c for c in DEMOGRAPHIC_COLS if c in frame.columns] + ["weight"]]


# ── public entry point ───────────────────────────────────────────────────────

def update_longitudinal_aggregates(
    country: str,
    extended_frame: pd.DataFrame,
    year: int,
    week: int,
    blob_client,          # BlobServiceClient
    container: str,
) -> None:
    """
    Append this week's extended frame to the longitudinal aggregates for `country`.
    Creates the aggregate files if they don't yet exist.
    Called once per country after MRP completes successfully.
    """
    week_label    = _week_label(year, week)
    baseline_blob = _longitudinal_blob_name(country)
    demo_blob     = _longitudinal_demographic_blob_name(country)

    # ── baseline ─────────────────────────────────────────────────────────────
    new_baseline_rows = _build_baseline_row(extended_frame, week_label)

    existing_baseline = _download_csv_or_none(blob_client, container, baseline_blob)

    if existing_baseline is not None:
        # drop any existing rows for this week (safe to re-run)
        existing_baseline = existing_baseline[existing_baseline["week"] != week_label]
        baseline = pd.concat([existing_baseline, new_baseline_rows], ignore_index=True)
    else:
        baseline = new_baseline_rows

    baseline = baseline.sort_values(["week", "vote_choice"]).reset_index(drop=True)
    _upload_csv(blob_client, container, baseline_blob, baseline)
    logger.info("[%s] Baseline longitudinal updated → %s (%d rows)", country, baseline_blob, len(baseline))

    # ── demographic ───────────────────────────────────────────────────────────
    new_demo_rows = _build_demographic_rows(extended_frame, week_label)

    existing_demo = _download_csv_or_none(blob_client, container, demo_blob)

    if existing_demo is not None:
        existing_demo = existing_demo[existing_demo["week"] != week_label]
        demographic = pd.concat([existing_demo, new_demo_rows], ignore_index=True)
    else:
        demographic = new_demo_rows

    demographic = demographic.sort_values(["week", "vote_choice"]).reset_index(drop=True)
    _upload_csv(blob_client, container, demo_blob, demographic)
    logger.info("[%s] Demographic longitudinal updated → %s (%d rows)", country, demo_blob, len(demographic))