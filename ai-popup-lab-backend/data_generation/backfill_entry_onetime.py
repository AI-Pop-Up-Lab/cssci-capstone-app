"""
one-off vote-choice backfill entry point for a single historical week,
reusing a biography-only panel from a DIFFERENT week.

ran with: python -m data_generation.backfill_entry_onetime
env variables:
    COUNTRY                       single country name, e.g. "usa"
    TARGET_YEAR / TARGET_WEEK     ISO week the survey is dated as, e.g. 2024 / 46
    SOURCE_YEAR / SOURCE_WEEK     ISO week whose biography panel to reuse, e.g. 2026 / 16
    BACKFILL_FORCE                true | false (default: false)
"""
from __future__ import annotations

import logging
import os
import sys

from .generate_panel_results import generate_vote_choice_backfill_onetime
from .store_data import get_blob_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    country = os.environ["COUNTRY"]
    target_year = int(os.environ["TARGET_YEAR"])
    target_week = int(os.environ["TARGET_WEEK"])
    source_year = int(os.environ["SOURCE_YEAR"])
    source_week = int(os.environ["SOURCE_WEEK"])
    force = os.environ.get("BACKFILL_FORCE", "false").lower() == "true"

    logger.info(
        "One-time backfill: %s target=%d-W%02d source=%d-W%02d force=%s",
        country, target_year, target_week, source_year, source_week, force,
    )

    blob_client = get_blob_client()
    try:
        generate_vote_choice_backfill_onetime(
            country=country,
            target_year=target_year,
            target_week=target_week,
            source_year=source_year,
            source_week=source_week,
            force=force,
            client=blob_client,
        )
    except Exception:
        logger.exception("One-time backfill failed")
        sys.exit(1)

    logger.info("One-time backfill complete.")


if __name__ == "__main__":
    main()