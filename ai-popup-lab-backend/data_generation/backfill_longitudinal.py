from __future__ import annotations

import argparse
import gc
import logging
import re

from azure.core.exceptions import ResourceNotFoundError

from azure_storage_utils import (
    get_blob_service_client,
    read_dataframe,
    CONTAINER_NAME,
)
from .aggregate_longitudinal import (
    build_week_aggregates,
    build_week_district_aggregate,
    build_week_national_summary_aggregate,
    upload_longitudinal_aggregates,
    upload_longitudinal_national_summary,
    _week_label,
    DEMOGRAPHIC_COLS,
    PARTY_COL,
    WEIGHT_COL,
    DISTRICT_COL,
)

logger = logging.getLogger(__name__)

# frame column name -> pipeline column name
COLUMN_RENAME = {
    "vote_2026": PARTY_COL,
    "expected_N": WEIGHT_COL,
}

# Matches get_extended_frame_path: {country}/extended_frames/{YYYY}_{WW}_extended_frame.csv
# Applied with fullmatch to the part of the blob name AFTER the extended_frames/ prefix,
# so blobs in subfolders (e.g. backup_old_pipeline/...) can never match.
_FRAME_RE = re.compile(r"(\d{4})_(\d{2})_extended_frame\.csv")

# Matches get_national_summary_path: {country}/national_summary/{YYYY}_{WW}_national_summary_95ci.csv
_NATIONAL_SUMMARY_RE = re.compile(r"(\d{4})_(\d{2})_national_summary_95ci\.csv")


def _list_frames(client, country: str) -> list[tuple[int, int, str]]:
    """
    Return sorted (year, week, blob_name) for every extended frame of this country
    that sits directly in {country}/extended_frames/. Blob storage has no real
    folders, so subfolder blobs share the prefix and must be excluded explicitly.
    """
    container = client.get_container_client(CONTAINER_NAME)
    prefix = f"{country}/extended_frames/"
    frames = []
    for blob in container.list_blobs(name_starts_with=prefix):
        m = _FRAME_RE.fullmatch(blob.name[len(prefix):])
        if m:
            frames.append((int(m[1]), int(m[2]), blob.name))
        else:
            logger.debug("[%s] Skipping non-frame blob: %s", country, blob.name)
    return sorted(frames)


def _list_national_summaries(client, country: str) -> list[tuple[int, int, str]]:
    """
    Return sorted (year, week, blob_name) for every national summary of this
    country directly in {country}/national_summary/ (production track only --
    backfill_storage/ and hotfix_backfill/ live under different prefixes).
    """
    container = client.get_container_client(CONTAINER_NAME)
    prefix = f"{country}/national_summary/"
    found = []
    for blob in container.list_blobs(name_starts_with=prefix):
        m = _NATIONAL_SUMMARY_RE.fullmatch(blob.name[len(prefix):])
        if m:
            found.append((int(m[1]), int(m[2]), blob.name))
        else:
            logger.debug("[%s] Skipping non-summary blob: %s", country, blob.name)
    return sorted(found)


def parse_weeks(raw: str | None) -> set[tuple[int, int]] | None:
    """'2026-14,2026-15' -> {(2026, 14), (2026, 15)}. Blank or 'all' -> None (every frame)."""
    if raw is None or not raw.strip() or raw.strip().lower() == "all":
        return None
    out = set()
    for token in raw.split(","):
        token = token.strip()
        if token:
            year, week = token.split("-")
            out.add((int(year), int(week)))
    return out


def _rebuild_frame_aggregates(client, country: str, weeks: set[tuple[int, int]] | None) -> list[str]:
    """
    Rebuild the baseline / demographic / district aggregates for `country` from
    the extended frames in Azure. `weeks=None` means every frame found.
    Returns labels of failed weeks.
    """
    frames = _list_frames(client, country)

    if weeks is not None:
        found = {(y, w) for y, w, _ in frames}
        for y, w in sorted(weeks - found):
            logger.error("[%s] No extended frame found for %d-W%02d", country, y, w)
        frames = [f for f in frames if (f[0], f[1]) in weeks]
        failed = [f"{country} {y}-W{w:02d}" for y, w in sorted(weeks - found)]
    else:
        failed = []

    if not frames and not failed:
        logger.error("No extended frames found for %s.", country)
        return [f"{country} (no frames)"]

    logger.info(
        "[%s] Rebuilding from %d frame(s): %s",
        country, len(frames), ", ".join(_week_label(y, w) for y, w, _ in frames),
    )

    # Only the small per-week aggregates are kept; each full frame is released
    # before the next one loads, and the CSVs are written once at the end.
    baseline_parts: list = []
    demographic_parts: list = []
    district_parts: list = []
    done_weeks: list[str] = []

    for year, week, blob_name in frames:
        label = f"{country} {year}-W{week:02d}"
        frame = None
        try:
            try:
                frame = read_dataframe(blob_name)
            except ResourceNotFoundError as exc:
                raise FileNotFoundError(f"Frame blob missing: {blob_name}") from exc

            frame = frame.rename(columns={k: v for k, v in COLUMN_RENAME.items() if k in frame.columns})

            missing = [c for c in (PARTY_COL, WEIGHT_COL) if c not in frame.columns]
            if missing:
                raise ValueError(
                    f"{label}: frame missing expected column(s) {missing}. "
                    f"Columns present: {list(frame.columns)}"
                )

            missing_demo = [c for c in DEMOGRAPHIC_COLS if c not in frame.columns]
            if missing_demo:
                logger.warning(
                    "[%s] Frame missing demographic column(s) %s -- omitted from the demographic aggregate.",
                    label, missing_demo,
                )

            if DISTRICT_COL not in frame.columns:
                logger.warning(
                    "[%s] Frame has no '%s' column -- no district aggregate (seat projection) for this week.",
                    label, DISTRICT_COL,
                )

            baseline_rows, demo_rows = build_week_aggregates(frame, year, week)
            baseline_parts.append(baseline_rows)
            demographic_parts.append(demo_rows)
            district_parts.append(build_week_district_aggregate(frame, year, week))
            done_weeks.append(_week_label(year, week))
            logger.info("[%s] Aggregated from %s", label, blob_name)

        except Exception:
            logger.exception("Failed: %s", label)
            failed.append(label)
        finally:
            frame = None
            gc.collect()

    if done_weeks:
        upload_longitudinal_aggregates(
            country=country,
            baseline_parts=baseline_parts,
            demographic_parts=demographic_parts,
            district_parts=district_parts,
            week_labels=done_weeks,
            blob_client=client,
            container=CONTAINER_NAME,
        )
        logger.info("[%s] Uploaded aggregates for %d week(s).", country, len(done_weeks))

    return failed


def _rebuild_national_summary_aggregate(client, country: str, weeks: set[tuple[int, int]] | None) -> list[str]:
    """
    Rebuild the national-summary aggregate for `country` from the per-week
    national summaries in Azure. `weeks=None` means every summary found.
    Returns labels of failed weeks.
    """
    summaries = _list_national_summaries(client, country)

    if weeks is not None:
        found = {(y, w) for y, w, _ in summaries}
        for y, w in sorted(weeks - found):
            logger.error("[%s] No national summary found for %d-W%02d", country, y, w)
        summaries = [s for s in summaries if (s[0], s[1]) in weeks]
        failed = [f"{country} national summary {y}-W{w:02d}" for y, w in sorted(weeks - found)]
    else:
        failed = []

    if not summaries and not failed:
        logger.error("No national summaries found for %s.", country)
        return [f"{country} (no national summaries)"]

    logger.info(
        "[%s] Rebuilding national summary aggregate from %d file(s): %s",
        country, len(summaries), ", ".join(_week_label(y, w) for y, w, _ in summaries),
    )

    parts: list = []
    done_weeks: list[str] = []

    for year, week, blob_name in summaries:
        label = f"{country} national summary {year}-W{week:02d}"
        try:
            try:
                summary = read_dataframe(blob_name)
            except ResourceNotFoundError as exc:
                raise FileNotFoundError(f"National summary blob missing: {blob_name}") from exc
            parts.append(build_week_national_summary_aggregate(summary, year, week))
            done_weeks.append(_week_label(year, week))
            logger.info("[%s] Aggregated from %s", label, blob_name)
        except Exception:
            logger.exception("Failed: %s", label)
            failed.append(label)

    if done_weeks:
        upload_longitudinal_national_summary(
            country=country,
            summary_parts=parts,
            week_labels=done_weeks,
            blob_client=client,
            container=CONTAINER_NAME,
        )
        logger.info("[%s] Uploaded national summary aggregate for %d week(s).", country, len(done_weeks))

    return failed


def rebuild(country: str, weeks: set[tuple[int, int]] | None = None) -> list[str]:
    """
    Rebuild all longitudinal aggregates for `country` from Azure: the
    frame-based ones (baseline / demographic / district, from extended frames)
    and the national-summary one (from the per-week national summaries).
    The two are independent -- a failure in one never prevents the other from
    running. `weeks=None` means everything found. Returns labels of failures.
    """
    client = get_blob_service_client()
    failed: list[str] = []

    for name, step in (
        ("frame aggregates", _rebuild_frame_aggregates),
        ("national summary aggregate", _rebuild_national_summary_aggregate),
    ):
        try:
            failed.extend(step(client, country, weeks))
        except Exception:
            logger.exception("[%s] %s step crashed", country, name)
            failed.append(f"{country} ({name} step crashed)")

    return failed


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    logging.getLogger("azure").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(
        description="Rebuild longitudinal aggregates from the extended frames and national summaries in Azure."
    )
    parser.add_argument("--country", required=True)
    parser.add_argument("--weeks", help="Comma-separated YYYY-WW list. Default: every frame / summary found.")
    args = parser.parse_args()

    failed = rebuild(args.country, parse_weeks(args.weeks))
    if failed:
        logger.error("Finished with failures: %s", failed)
        raise SystemExit(1)
    logger.info("All weeks processed.")


if __name__ == "__main__":
    main()
