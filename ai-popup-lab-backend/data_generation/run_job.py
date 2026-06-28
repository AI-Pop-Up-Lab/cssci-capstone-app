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
import sys
import tempfile
from datetime import date
from pathlib import Path
import pandas as pd

from .generate_panel_results import generate_panel_results
from .job_guard import already_ran_typed, mark_ran_typed
from .run_scripts import check_r_available, run_extension_script
from .store_data import CONTAINER_NAME, get_blob_client, store_frame, results_blob_name, download_blob_to_path
from .aggregate_longitudinal import update_longitudinal_aggregates

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

    frame_path = STRAT_FRAMES_DIR / country_data[country]["stratification_frame_filename"]

    survey_blob_name = results_blob_name(country, year, week)

    with tempfile.TemporaryDirectory() as tmp:
        survey_path = Path(tmp) / f"{country}_{year}_{week:02d}_panel_results.csv"
        try:
            download_blob_to_path(blob_client, survey_blob_name, survey_path)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"No panel results found for {country} {year}-W{week:02d} "
                f"(expected blob: {survey_blob_name}). "
                f"Panel must run successfully before MRP for the same week."
            )

        output_dir = Path(tmp) / "output"
        output_dir.mkdir()
        run_extension_script(
            survey_path=survey_path,
            frame_path=frame_path,
            output_dir=output_dir,
            country=country,
        )
        frame_blob_name = store_frame(filepath=output_dir, country=country, client=blob_client)

        frame_path_local = Path(tmp) / "extended_frame.csv"
        download_blob_to_path(blob_client, frame_blob_name, frame_path_local)
        extended_frame = pd.read_csv(frame_path_local)

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

    if JOB_TYPE in ("panel", "both"):
        if already_ran_typed(blob_client, CONTAINER_NAME, country, "panel", year, week):
            logger.info("[%s] Panel already ran for %d-W%02d — skipping.", country, year, week)
        else:
            logger.info("[%s] Running panel survey (%d-W%02d)...", country, year, week)
            generate_panel_results(
                country=country,
                year=year,
                week=week,
                force=False,
                client=blob_client,
            )
            mark_ran_typed(blob_client, CONTAINER_NAME, country, "panel", year, week)
            logger.info("[%s] Panel survey done.", country)

    if JOB_TYPE in ("mrp", "both"):
        if already_ran_typed(blob_client, CONTAINER_NAME, country, "mrp", year, week):
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