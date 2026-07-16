from __future__ import annotations

import io
import logging
import os
import sys

import pandas as pd

from .store_data import get_blob_client, CONTAINER_NAME
from .aggregate_longitudinal import update_longitudinal_aggregates

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

# teammate export column name -> pipeline convention column name
COLUMN_RENAME = {
    "vote_2026": "party",
    "expected_N": "prob_raked",
}


def _staging_blob_name(country: str, year: int, week: int) -> str:
    return f"staging/extended-frames/{country}/{year}_{week:02d}_extended_frame.csv"


def _canonical_blob_name(country: str, year: int, week: int) -> str:
    return f"extended-frames/{country}/{year}_{week:02d}_extended_frame.csv"


def _parse_weeks(raw: str) -> list[tuple[int, int]]:
    result = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        year_str, week_str = token.split("-")
        result.append((int(year_str), int(week_str)))
    return result


def main() -> None:
    country = os.environ["COUNTRY"]
    weeks = _parse_weeks(os.environ["FRAMES"])
    if not weeks:
        logger.error("No weeks provided. Set FRAMES=YYYY-WW[,YYYY-WW,...]")
        sys.exit(1)

    blob_client = get_blob_client()
    failed: list[str] = []

    for year, week in weeks:
        label = f"{country} {year}-W{week:02d}"
        staging_blob = _staging_blob_name(country, year, week)
        canonical_blob = _canonical_blob_name(country, year, week)
        try:
            blob = blob_client.get_blob_client(container=CONTAINER_NAME, blob=staging_blob)
            try:
                data = blob.download_blob().readall()
            except Exception as exc:
                raise FileNotFoundError(f"No staging blob at {staging_blob}") from exc

            raw_frame = pd.read_csv(io.BytesIO(data))

            missing_cols = [c for c in COLUMN_RENAME if c not in raw_frame.columns]
            if missing_cols:
                raise ValueError(
                    f"{label}: frame missing expected column(s) {missing_cols}. "
                    f"Columns present: {list(raw_frame.columns)}"
                )

            extended_frame = raw_frame.rename(columns=COLUMN_RENAME)

            # Upload the RAW (un-renamed) frame as the canonical extended-frame
            # blob, so anything downstream that expects the teammate's original
            # column names (e.g. manual inspection) still sees them as-is.
            canonical = blob_client.get_blob_client(container=CONTAINER_NAME, blob=canonical_blob)
            canonical.upload_blob(data, overwrite=True)
            logger.info("[%s] Copied staging → canonical (%s)", label, canonical_blob)

            update_longitudinal_aggregates(
                country=country,
                extended_frame=extended_frame,  # renamed version, for correct aggregation
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
        sys.exit(1)
    logger.info("All frames processed.")


if __name__ == "__main__":
    main()