from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from .store_data import get_blob_client, CONTAINER_NAME
from .aggregate_longitudinal import update_longitudinal_aggregates

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


def _extended_frame_blob_name(country: str, year: int, week: int) -> str:
    """Same convention as store_frame(), but keyed by explicit year/week
    instead of today's date — store_frame()'s get_file_suffix() always
    uses today, which would silently mislabel a backfilled historical week."""
    return f"extended-frames/{country}/{year}_{week:02d}_extended_frame.csv"


def _parse_frame_arg(raw: str) -> tuple[int, int, Path]:
    """Parse 'YYYY-WW:/path/to/frame.csv'."""
    week_part, path_part = raw.split(":", 1)
    year_str, week_str = week_part.split("-")
    return int(year_str), int(week_str), Path(path_part)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", required=True)
    parser.add_argument(
        "--frame", action="append", required=True,
        help="YYYY-WW:/local/path/to/extended_frame.csv — repeat per week",
    )
    args = parser.parse_args()

    blob_client = get_blob_client()
    failed = []

    for raw in args.frame:
        year, week, local_path = _parse_frame_arg(raw)
        label = f"{args.country} {year}-W{week:02d}"
        try:
            if not local_path.exists():
                raise FileNotFoundError(f"Frame file not found: {local_path}")

            extended_frame = pd.read_csv(local_path)

            missing_cols = [c for c in ("party", "prob_raked") if c not in extended_frame.columns]
            if missing_cols:
                raise ValueError(
                    f"{label}: frame missing expected column(s) {missing_cols}. "
                    f"Columns present: {list(extended_frame.columns)}"
                )

            blob_name = _extended_frame_blob_name(args.country, year, week)
            blob = blob_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
            with open(local_path, "rb") as f:
                blob.upload_blob(f, overwrite=True)
            logger.info("[%s] Uploaded frame → %s", label, blob_name)

            update_longitudinal_aggregates(
                country=args.country,
                extended_frame=extended_frame,
                year=year,
                week=week,
                blob_client=blob_client,
                container=CONTAINER_NAME,
            )
            logger.info("[%s] Longitudinal aggregates updated.", label)

        except Exception:
            logger.exception("Failed: %s", label)
            failed.append(label)

    if failed:
        logger.error("Finished with failures: %s", failed)
        raise SystemExit(1)
    logger.info("All frames processed.")


if __name__ == "__main__":
    main()