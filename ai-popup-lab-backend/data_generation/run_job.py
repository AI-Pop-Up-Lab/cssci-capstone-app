"""
entry point for the weekly data generation worker container.

Run locally (no Docker):
    export $(cat .env | xargs)
    python -m data_generation.run_job

Test locally with Docker:
    docker build -f Dockerfile.worker -t worker-test .
    docker run --rm \\
        -e AZURE_STORAGE_CONNECTION_STRING="..." \\
        -e COUNTRIES="sweden" \\
        -e BLOB_CONTAINER_NAME="generated-data" \\
        -e JOB_TYPE="panel" \\
        worker-test
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path
import pandas as pd

from .generate_panel_results import generate_panel_results, isoweek_to_panel_date
from .job_guard import already_ran_typed, mark_ran_typed
from .run_scripts import check_r_available, run_extension_script
from .store_data import (
    CONTAINER_NAME, get_blob_client, store_frame, results_blob_name,
    download_blob_to_path, strat_frame_blob_name,
)
from .aggregate_longitudinal import update_longitudinal_aggregates
from .fetch_us_polls import fetch_and_store_us_polls


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR        = Path(__file__).resolve().parent.parent
STRAT_FRAMES_DIR = BASE_DIR / "country_data" / "stratification_frames"
SURVEYS_DIR      = BASE_DIR / "country_data" / "surveys"

# Comma-separated list of country names, e.g. "sweden" or "sweden,denmark"
COUNTRIES = [c.strip() for c in os.environ.get("COUNTRIES", "sweden").split(",") if c.strip()]

# What to run: "panel", "mrp", or "both"
JOB_TYPE  = os.environ.get("JOB_TYPE", "panel").lower()


def _this_week() -> tuple[int, int]:
    today = date.today()
    year, week, _ = today.isocalendar()
    return year, week


def _run_mrp(country: str, blob_client, year: int, week: int) -> None:
    """Run the MRP extended-frame R script and upload result."""
    with open(BASE_DIR / "country_data" / "country_data_info.json") as f:
        country_data = json.load(f)


    survey_blob_name = results_blob_name(country, year, week)

    with tempfile.TemporaryDirectory() as tmp:
        # retrieve strat frame from local file if present, else pull from blob storage on azure

        local_frame_path = STRAT_FRAMES_DIR / country_data[country]["stratification_frame_filename"]
        if local_frame_path and local_frame_path.exists():
            frame_path = local_frame_path
        else:
            frame_path = Path(tmp) / f"{country}_strat_frame.csv"
            try:
                download_blob_to_path(blob_client, strat_frame_blob_name(country), frame_path)
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"No stratification frame found locally at {local_frame_path} "
                    f"or in blob at {strat_frame_blob_name(country)} for '{country}'."
                )

        survey_path = Path(tmp) / f"{country}_{year}_{week:02d}_panel_results.csv"
        try:
            download_blob_to_path(blob_client, survey_blob_name, survey_path)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"No panel results found for {country} {year}-W{week:02d} "
                f"(expected blob: {survey_blob_name}). "
                f"Panel must run successfully before MRP for the same week."
            )

        # panel results store the vote answer in a wave column named {YYYYMMDD}_vote,
        # but the R script only accepts 'predicted_vote' (or its alias 'vote_2026').
        # prefer the wave matching THIS job's week — a backfilled snapshot of the shared
        # active panel can carry later weeks' wave columns, and the newest is then wrong
        survey_df = pd.read_csv(survey_path)
        if "predicted_vote" not in survey_df.columns and "vote_2026" not in survey_df.columns:
            this_week_col = f"{isoweek_to_panel_date(year, week)}_vote"
            if this_week_col in survey_df.columns:
                vote_col = this_week_col
            else:
                wave_vote_cols = sorted(c for c in survey_df.columns if re.fullmatch(r"\d{8}_vote", c))
                if not wave_vote_cols:
                    raise ValueError(
                        f"No vote column found in panel results for '{country}' "
                        f"(expected 'predicted_vote', 'vote_2026', or a 'YYYYMMDD_vote' wave column)."
                    )
                vote_col = wave_vote_cols[-1]
                logger.warning(
                    "[%s] No wave column %s in panel results — falling back to newest wave %s.",
                    country, this_week_col, vote_col,
                )
            survey_df = survey_df.rename(columns={vote_col: "predicted_vote"})
            survey_df.to_csv(survey_path, index=False)

        output_dir = Path(tmp) / "output"
        output_dir.mkdir()
        run_extension_script(
            survey_path=survey_path,
            frame_path=frame_path,
            output_dir=output_dir,
            country=country,
        )
        frame_blob_name = store_frame(filepath=output_dir, country=country, client=blob_client, year=year, week=week)

        frame_path_local = Path(tmp) / "extended_frame.csv"
        download_blob_to_path(blob_client, frame_blob_name, frame_path_local)
        extended_frame = pd.read_csv(frame_path_local)

        # R output columns differ from what the aggregator expects
        # (same rename convention as backfill_longitudinal_entry.py)
        extended_frame = extended_frame.rename(
            columns={"predicted_vote_party": "party", "expected_N": "prob_raked"}
        )

        update_longitudinal_aggregates(
            country=country,
            extended_frame=extended_frame,
            year=year,
            week=week,
            blob_client=blob_client,
            container=CONTAINER_NAME,
        )


def run_country_job(country: str, blob_client, year: int, week: int) -> None:
    """Run the configured job(s) for a single country."""

    with open(BASE_DIR / "country_data" / "country_data_info.json") as f:
        country_data = json.load(f)
    info = country_data.get(country, {})
    panel_configured = bool(info.get("panel_filename")) and bool(info.get("question_id"))

    if JOB_TYPE in ("panel", "both"):
        if not panel_configured:
            # don't write the panel lock here — a lock without panel results would
            # permanently wedge MRP for this country+week
            logger.warning(
                "[%s] Panel not configured (panel_filename/question_id missing in "
                "country_data_info.json) — skipping panel stage, no lock written.", country
            )
        elif already_ran_typed(blob_client, CONTAINER_NAME, country, "panel", year, week):
            logger.info("[%s] Panel already ran for %d-W%02d — skipping.", country, year, week)
        else:
            logger.info("[%s] Running panel survey (%d-W%02d)...", country, year, week)
            panel_ran = generate_panel_results(
                country=country,
                year=year,
                week=week,
                force=False,
                client=blob_client,
            )
            if panel_ran:
                mark_ran_typed(blob_client, CONTAINER_NAME, country, "panel", year, week)
                logger.info("[%s] Panel survey done.", country)
            else:
                logger.warning("[%s] Panel produced no results — no lock written.", country)

    if JOB_TYPE in ("mrp", "both"):
        if not panel_configured:
            # MRP needs this week's panel results, which an unconfigured country can never have
            logger.warning("[%s] Panel not configured — skipping MRP stage, no lock written.", country)
        elif already_ran_typed(blob_client, CONTAINER_NAME, country, "mrp", year, week):
            logger.info("[%s] MRP already ran for %d-W%02d — skipping.", country, year, week)
        else:
            logger.info("[%s] Running MRP...", country)
            _run_mrp(country, blob_client, year, week)
            mark_ran_typed(blob_client, CONTAINER_NAME, country, "mrp", year, week)
            logger.info("[%s] MRP done.", country)


def main() -> None:
    if JOB_TYPE in ("mrp", "both"):
        check_r_available()

    blob_client = get_blob_client()
    year, week  = _this_week()
    failed: list[str] = []

    try:
        fetch_and_store_us_polls()
    except Exception:
        logger.exception("US polls pipeline failed")
        failed.append("usa_pollsters_download")

    for country in COUNTRIES:
        logger.info("Processing country: %s", country)
        try:
            run_country_job(country, blob_client, year, week)
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