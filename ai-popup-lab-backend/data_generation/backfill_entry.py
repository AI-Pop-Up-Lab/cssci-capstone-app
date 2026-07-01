"""
backfill entry point.
ran with: python -m data_generation.backfill_entry
env variables:
    COUNTRIES       comma-separated country names, e.g. "sweden"
    BACKFILL_WEEKS  comma-separated ISO weeks, e.g. "2026-20,2026-21,2026-22"
    JOB_TYPE        panel | mrp | both  (default: panel)
    BACKFILL_FORCE  true | false        (default: false)
"""
from __future__ import annotations

import logging
import os
import sys

from .generate_panel_results import (
    generate_panel_results,
    generate_panel_biographies_only,
    isoweek_to_panel_date,
)
from .job_guard import already_ran_typed, mark_ran_typed
from .run_scripts import check_r_available, run_extension_script
from .store_data import CONTAINER_NAME, get_blob_client, store_frame
from .run_job import _run_mrp, COUNTRIES, JOB_TYPE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

FORCE = os.environ.get("BACKFILL_FORCE", "false").lower() == "true"
GENERATE_EVENTS = os.environ.get("GENERATE_EVENTS", "false").lower() == "true"
ARTICLES_PATH = os.environ.get("ARTICLES_PATH")  # required only if GENERATE_EVENTS=true

_RAW_WEEKS = os.environ.get("BACKFILL_WEEKS", "")


def _parse_weeks(raw: str) -> list[tuple[int, int]]:
    """Parse "2026-20,2026-21" → [(2026, 20), (2026, 21)]."""
    result = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        parts = token.split("-")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid week format: '{token}'. Expected YYYY-WW (e.g. 2026-20)."
            )
        result.append((int(parts[0]), int(parts[1])))
    return result


def main() -> None:
    weeks = _parse_weeks(_RAW_WEEKS)
    if not weeks:
        logger.error("No weeks provided. Set BACKFILL_WEEKS=YYYY-WW[,YYYY-WW,...]")
        sys.exit(1)

    if JOB_TYPE in ("mrp", "both"):
        check_r_available()

    blob_client = get_blob_client()
    failed: list[str] = []

    for year, week in weeks:
        for country in COUNTRIES:
            label = f"{country} {year}-W{week:02d}"
            logger.info("Backfilling: %s [job_type=%s, force=%s]", label, JOB_TYPE, FORCE)
            try:
                if JOB_TYPE in ("panel", "both"):
                    if not FORCE and already_ran_typed(
                        blob_client, CONTAINER_NAME, country, "panel", year, week
                    ):
                        logger.info("[%s] Panel lock exists — skipping (use force=true to override).", label)
                    else:
                        generate_panel_results(
                            country=country,
                            year=year,
                            week=week,
                            force=FORCE,
                            client=blob_client,
                        )
                        mark_ran_typed(blob_client, CONTAINER_NAME, country, "panel", year, week)

                if JOB_TYPE in ("mrp", "both"):
                    if not FORCE and already_ran_typed(
                        blob_client, CONTAINER_NAME, country, "mrp", year, week
                    ):
                        logger.info("[%s] MRP lock exists — skipping.", label)
                    else:
                        _run_mrp(country, blob_client)
                        mark_ran_typed(blob_client, CONTAINER_NAME, country, "mrp", year, week)

                if JOB_TYPE == "biography":
                    if not FORCE and already_ran_typed(
                        blob_client, CONTAINER_NAME, country, "biography", year, week
                    ):
                        logger.info("[%s] Biography lock exists — skipping (use force=true to override).", label)
                    else:
                        generate_panel_biographies_only(
                            country=country,
                            year=year,
                            week=week,
                            client=blob_client,
                            generate_events=GENERATE_EVENTS,
                            articles_path=ARTICLES_PATH,
                        )
                        mark_ran_typed(blob_client, CONTAINER_NAME, country, "biography", year, week)

                logger.info("Done: %s", label)
            except Exception:
                logger.exception("Failed: %s", label)
                failed.append(label)

    if failed:
        logger.error("Backfill finished with failures: %s", failed)
        sys.exit(1)
    else:
        logger.info("Backfill complete.")


if __name__ == "__main__":
    main()