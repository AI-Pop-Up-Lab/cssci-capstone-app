"""
Container entrypoint for the GitHub Actions / ACI longitudinal backfill.

Env vars:
  COUNTRY  required
  FRAMES   optional, comma-separated YYYY-WW list; blank or 'all' = every extended frame
"""
from __future__ import annotations

import logging
import os
import sys

from .backfill_longitudinal import rebuild, parse_weeks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logging.getLogger("azure").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main() -> None:
    country = os.environ["COUNTRY"]
    weeks = parse_weeks(os.environ.get("FRAMES"))

    failed = rebuild(country, weeks)
    if failed:
        logger.error("Finished with failures: %s", failed)
        sys.exit(1)
    logger.info("All frames processed.")


if __name__ == "__main__":
    main()
