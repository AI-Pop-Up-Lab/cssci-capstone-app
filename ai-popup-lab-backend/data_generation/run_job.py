"""
Entry point for the weekly data generation worker container.

Run locally (no Docker):
    export $(cat .env | xargs)
    python -m data_generation.run_job

Env variables:
    COUNTRIES  comma-separated country names, e.g. "usa" or "usa,sweden"
    JOB_TYPE   panel | mrp | both  (default: panel)

Countries are processed one after another in a simple loop — the pipeline
runs identically regardless of how many countries are listed, so adding a
second/third country later (e.g. "usa,sweden") needs no code changes here,
only a COUNTRIES value and a configured entry in country_data_info.json.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

from .generate_panel_results import generate_panel_results, iso_week_label, isoweek_to_panel_date
from .run_scripts import check_r_available, run_extension_script
from .aggregate_longitudinal import update_longitudinal_aggregates
from .fetch_us_polls import fetch_and_store_us_polls

import azure_storage_utils as storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
COUNTRY_INFO_PATH = BASE_DIR / "country_data" / "country_data_info.json"

# Comma-separated list of country names, e.g. "usa" or "usa,sweden"
COUNTRIES = [c.strip() for c in os.environ.get("COUNTRIES", "usa").split(",") if c.strip()]

# What to run: "panel", "mrp", or "both"
JOB_TYPE = os.environ.get("JOB_TYPE", "panel").lower()


def _this_week() -> tuple[int, int]:
    today = date.today()
    year, week, _ = today.isocalendar()
    return year, week


def _panel_configured(country: str) -> bool:
    """
    True when `country` has a panel configured in country_data_info.json
    (a non-null `question_id`). An unconfigured or unknown country can never
    have panel results, so MRP skips it with a warning instead of failing the
    whole job — and never writes a lock, since a lock without results would
    permanently wedge MRP for that country+week.
    """
    with open(COUNTRY_INFO_PATH) as f:
        country_data = json.load(f)
    return bool(country_data.get(country, {}).get("question_id"))


def _rename_state_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    The post-stratification R module (post_strat_module.R, currently the US
    variant) expects a `state_abbrv` column with no alias fallback — unlike
    most of its other required columns, it will NOT fall back to `state`.
    Our pipeline uses `state` everywhere else, so rename here rather than
    upstream, since `state` is the established name for every other
    consumer of the frame/panel.
    """
    if "state" in df.columns and "state_abbrv" not in df.columns:
        df = df.rename(columns={"state": "state_abbrv"})
    return df


def _prepare_frame_for_r(frame_df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename `state` -> `state_abbrv`, and disambiguate the frame's two
    population-weight columns for R's `expected_N_raked` alias.

    The frame carries both `expected_N` (= old_N * prob, i.e. UNraked) and
    `N` (= cell total * prob_raked, i.e. the properly RAKED/corrected
    weight — verified against the actual sample data: old_N * prob equals
    expected_N exactly, and cell_total_N * prob_raked equals N exactly).
    R's alias list for `expected_N_raked` checks `expected_N` before `N`,
    which would silently pick the unraked figure. Rename `N` explicitly
    instead of relying on that alias order, and drop `expected_N` so
    there's no ambiguity even if R's alias list changes later. This also
    keeps the frame consistent with panel.attrition, which already samples
    replacement panellists weighted by `N`.
    """
    frame_df = _rename_state_column(frame_df)
    if "expected_N_raked" not in frame_df.columns:
        if "N" in frame_df.columns:
            frame_df = frame_df.rename(columns={"N": "expected_N_raked"})
        if "expected_N" in frame_df.columns:
            frame_df = frame_df.drop(columns=["expected_N"])
    return frame_df


# Raw vote-choice text may be a bare "Did not vote", or a district-race
# answer in the "Name (Party Party)" format `survey.py` generates options
# in (e.g. "Jane Smith (Democratic Party)", "Pat Lee (Libertarian Party)").
# R's model treats every distinct `predicted_vote` value as its own outcome
# category, so left unnormalized this would produce a one-off category per
# candidate name instead of collapsing to the three-party view
# country_data_info.json's `party_colours` expects. "Did not vote" is left
# untouched — aggregate_longitudinal.py specifically filters on that exact
# string to exclude non-voters from party-share calculations.
def _normalize_party(raw_vote) -> str:
    if pd.isna(raw_vote):
        return raw_vote
    text = str(raw_vote).strip()
    if text.lower() == "did not vote":
        return "Did not vote"
    lowered = text.lower()
    if "democrat" in lowered:
        return "Democrat"
    if "republican" in lowered:
        return "Republican"
    return "Other"


def _prepare_survey_for_r(survey_df: pd.DataFrame, panel_date: str) -> pd.DataFrame:
    """
    Rename `state` -> `state_abbrv`, and build a `predicted_vote` (aliased
    to `vote_2026`) column — the panel stores this week's answers as
    `{panel_date}_vote` dynamically (every week's answers accumulate as
    their own column), so copy that week's column over under the name R
    expects, normalized down to Democrat / Republican / Other / Did not vote.
    """
    survey_df = _rename_state_column(survey_df)
    vote_col = f"{panel_date}_vote"
    if vote_col not in survey_df.columns:
        raise ValueError(
            f"Expected this week's vote column '{vote_col}' in the survey results, "
            f"but it wasn't found. Panel/survey must have completed for this week "
            f"before MRP can run."
        )
    survey_df = survey_df.copy()
    survey_df["predicted_vote"] = survey_df[vote_col].apply(_normalize_party)
    return survey_df


def _prepare_extended_frame_for_longitudinal(extended_frame: pd.DataFrame) -> pd.DataFrame:
    """
    aggregate_longitudinal.py expects columns named `party` (outcome) and
    `prob_raked` (weight) — but the US R module's extended-frame output
    names these `vote_2026` and `expected_N`. Rename on a copy here rather
    than upstream, so the blob uploaded to get_extended_frame_path keeps
    the R script's native column names for any other consumer.
    """
    return extended_frame.rename(columns={"vote_2026": "party", "expected_N": "prob_raked"})


def _run_mrp(country: str, year: int, week: int, backfill: bool = False, force: bool = False) -> None:
    """
    Run the MRP extended-frame R script for `country` / ISO week
    `year`-W`week` and fold the result into the longitudinal aggregates.

    `backfill=True` reads this week's survey results from the backfill
    historical-panel track (get_backfill_historical_panel_path) instead of
    the production one, and locks under a separate "mrp_backfill" job type
    so a backfill MRP run never collides with, or gets skipped by, a
    production MRP run for the same week.
    """
    if not _panel_configured(country):
        # MRP needs this week's panel results, which an unconfigured country
        # can never have — skip with a warning rather than failing the job
        logger.warning("[%s] Panel not configured — skipping MRP, no lock written.", country)
        return

    week_label = iso_week_label(year, week)
    panel_date = isoweek_to_panel_date(year, week)
    job_type = "mrp_backfill" if backfill else "mrp"

    if not force and storage.already_ran(country, job_type, week_label):
        logger.info("MRP already ran for %s %s (job_type=%s) — skipping.", country, week_label, job_type)
        return

    survey_blob_path = (
        storage.get_backfill_historical_panel_path(country, week_label)
        if backfill else
        storage.get_historical_panel_path(country, week_label)
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        frame_path = tmp_path / f"{country}_strat_frame.csv"
        frame_df = storage.read_dataframe(storage.get_stratification_frame_path(country))
        frame_df = _prepare_frame_for_r(frame_df)
        frame_df.to_csv(frame_path, index=False)

        survey_df = storage.read_dataframe_or_none(survey_blob_path)
        if survey_df is None:
            raise FileNotFoundError(
                f"No panel results found for {country} {week_label} "
                f"(expected blob: {survey_blob_path}). "
                f"Panel must run successfully before MRP for the same week."
            )
        survey_df = _prepare_survey_for_r(survey_df, panel_date)
        survey_path = tmp_path / f"{country}_{week_label}_panel_results.csv"
        survey_df.to_csv(survey_path, index=False)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        run_extension_script(
            survey_path=survey_path,
            frame_path=frame_path,
            output_dir=output_dir,
            country=country,
        )

        r_output_path = output_dir / "mrp_extended_frame_predictions.csv"
        if not r_output_path.exists():
            raise FileNotFoundError(f"Expected R output not found: {r_output_path}")

        extended_frame = pd.read_csv(r_output_path)
        storage.upload_dataframe(extended_frame, storage.get_extended_frame_path(country, week_label))
        logger.info("[%s] Extended frame uploaded for %s.", country, week_label)

        update_longitudinal_aggregates(
            country=country,
            extended_frame=_prepare_extended_frame_for_longitudinal(extended_frame),
            year=year,
            week=week,
            blob_client=storage.get_blob_service_client(),
            container=storage.CONTAINER_NAME,
        )

    storage.mark_job_ran(country, job_type, week_label)
    logger.info("MRP complete: %s %s (job_type=%s)", country, week_label, job_type)


def run_country_job(country: str, year: int, week: int) -> None:
    """
    Run the configured job(s) for a single country. Each step manages its
    own job-lock check/skip internally (see generate_panel_results and
    _run_mrp above), so this function is just sequencing, not lock
    bookkeeping.
    """
    if JOB_TYPE in ("panel", "both"):
        logger.info("[%s] Running panel cycle (%d-W%02d)...", country, year, week)
        generate_panel_results(country=country, year=year, week=week, force=False)
        logger.info("[%s] Panel cycle done.", country)

    if JOB_TYPE in ("mrp", "both"):
        logger.info("[%s] Running MRP...", country)
        _run_mrp(country=country, year=year, week=week, backfill=False, force=False)
        logger.info("[%s] MRP done.", country)


def main() -> None:
    if JOB_TYPE in ("mrp", "both"):
        check_r_available()

    year, week = _this_week()
    failed: list[str] = []

    try:
        fetch_and_store_us_polls()
    except Exception:
        logger.exception("US polls pipeline failed")
        failed.append("usa_pollsters_download")

    for country in COUNTRIES:
        logger.info("Processing country: %s", country)
        try:
            run_country_job(country, year, week)
        except Exception:
            logger.exception("Country failed: %s", country)
            failed.append(country)

    if failed:
        logger.error("Job finished with failures: %s", failed)
        sys.exit(1)
    else:
        logger.info("All countries succeeded.")


if __name__ == "__main__":
    main()
