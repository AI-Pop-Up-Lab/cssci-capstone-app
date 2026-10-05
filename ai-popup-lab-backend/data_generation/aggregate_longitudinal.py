from __future__ import annotations

import io
import logging
from pathlib import Path

import pandas as pd
from azure.core.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)

from azure_storage_utils import (
    get_simple_frame_aggregate_path,
    get_demographic_frame_aggregate_path,
    get_district_frame_aggregate_path,
)

# ── column config ────────────────────────────────────────────────────────────

DEMOGRAPHIC_COLS = ["age_group", "gender", "race", "state_abbrv", "education_level"]
PARTY_COL        = "party"
WEIGHT_COL       = "prob_raked"
DISTRICT_COL     = "state_cd"   # congressional district, e.g. "AK-1"

# ── internal helpers ─────────────────────────────────────────────────────────

def _download_csv_or_none(client, container: str, blob_name: str) -> pd.DataFrame | None:
    try:
        blob = client.get_container_client(container).get_blob_client(blob_name)
        data = blob.download_blob().readall().decode("utf-8")
    except ResourceNotFoundError:
        return None
    return pd.read_csv(io.StringIO(data))


def _upload_csv(client, container: str, blob_name: str, df: pd.DataFrame) -> None:
    blob = client.get_container_client(container).get_blob_client(blob_name)
    blob.upload_blob(df.to_csv(index=False).encode("utf-8"), overwrite=True)


def _week_label(year: int, week: int) -> str:
    return f"{year}-W{week:02d}"


def _build_baseline_row(frame: pd.DataFrame, week: str) -> pd.DataFrame:
    by_party = frame.groupby(PARTY_COL)[WEIGHT_COL].sum().reset_index()
    total = by_party[WEIGHT_COL].sum()
    by_party["share"] = (by_party[WEIGHT_COL] / total * 100).round(2)
    by_party["week"]  = week
    return by_party[["week", PARTY_COL, "share"]].rename(columns={PARTY_COL: "vote_choice"})
    

def _build_demographic_rows(frame: pd.DataFrame, week: str) -> pd.DataFrame:
    demo_cols = [c for c in DEMOGRAPHIC_COLS if c in frame.columns]

    # Sum weight across every raw extended-frame row (one per synthetic cell)
    # that shares the same party + demographic combination. Without this the
    # output has one row per input row -- i.e. the full synthetic population,
    # not an aggregate -- and grows unboundedly week over week.
    grouped = (
        frame.groupby([PARTY_COL] + demo_cols, as_index=False, dropna=False)[WEIGHT_COL]
        .sum()
    )
    grouped["week"] = week
    grouped = grouped.rename(columns={PARTY_COL: "vote_choice", WEIGHT_COL: "weight"})
    return grouped[["week", "vote_choice"] + demo_cols + ["weight"]]


def _build_district_rows(frame: pd.DataFrame, week: str) -> pd.DataFrame:
    """
    Compact district-level aggregate: one row per week x district x party.
    Kept separate from the demographic aggregate on purpose -- adding state_cd
    to the demographic grouping would multiply its row count several times
    over, whereas this file is only (districts x parties) rows per week.
    Returns an empty frame if the frame has no state_cd column (non-US countries).
    """
    cols = ["week", "vote_choice", DISTRICT_COL, "weight"]
    if DISTRICT_COL not in frame.columns:
        return pd.DataFrame(columns=cols)

    grouped = (
        frame.groupby([PARTY_COL, DISTRICT_COL], as_index=False, dropna=True)[WEIGHT_COL]
        .sum()
    )
    grouped["week"] = week
    grouped = grouped.rename(columns={PARTY_COL: "vote_choice", WEIGHT_COL: "weight"})
    grouped["weight"] = grouped["weight"].round(2)
    return grouped[cols]


def _merge_and_upload(
    client,
    container: str,
    blob_name: str,
    new_parts: list[pd.DataFrame],
    week_labels: list[str],
) -> pd.DataFrame:
    """
    Download the existing aggregate once, drop rows for the weeks being
    replaced, append the new rows, sort, and upload once.
    """
    parts: list[pd.DataFrame] = []
    existing = _download_csv_or_none(client, container, blob_name)
    if existing is not None:
        parts.append(existing[~existing["week"].isin(week_labels)])
    parts.extend(new_parts)

    merged = (
        pd.concat(parts, ignore_index=True)
        .sort_values(["week", "vote_choice"])
        .reset_index(drop=True)
    )
    _upload_csv(client, container, blob_name, merged)
    return merged


# ── public entry points ──────────────────────────────────────────────────────

def build_week_aggregates(
    extended_frame: pd.DataFrame, year: int, week: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate one extended frame into (baseline_rows, demographic_rows). No I/O."""
    label = _week_label(year, week)
    return (
        _build_baseline_row(extended_frame, label),
        _build_demographic_rows(extended_frame, label),
    )


def build_week_district_aggregate(
    extended_frame: pd.DataFrame, year: int, week: int
) -> pd.DataFrame:
    """District-level rows (week, vote_choice, state_cd, weight) for one frame. No I/O.
    Empty if the frame has no state_cd column."""
    return _build_district_rows(extended_frame, _week_label(year, week))


def upload_longitudinal_aggregates(
    country: str,
    baseline_parts: list[pd.DataFrame],
    demographic_parts: list[pd.DataFrame],
    week_labels: list[str],
    blob_client,
    container: str,
    district_parts: list[pd.DataFrame] | None = None,
) -> None:
    """Merge any number of weeks' aggregate rows into the stored files with one download/upload each.

    `district_parts` is optional so existing callers keep working; empty parts
    (frames without state_cd) are ignored and the district file is only touched
    for the weeks that actually produced rows.
    """
    baseline_blob = get_simple_frame_aggregate_path(country)
    demo_blob     = get_demographic_frame_aggregate_path(country)

    baseline = _merge_and_upload(blob_client, container, baseline_blob, baseline_parts, week_labels)
    logger.info("[%s] Baseline longitudinal updated -> %s (%d rows)", country, baseline_blob, len(baseline))

    demographic = _merge_and_upload(blob_client, container, demo_blob, demographic_parts, week_labels)
    logger.info("[%s] Demographic longitudinal updated -> %s (%d rows)", country, demo_blob, len(demographic))

    non_empty = [p for p in (district_parts or []) if not p.empty]
    if non_empty:
        district_weeks = sorted({w for p in non_empty for w in p["week"].unique()})
        district_blob  = get_district_frame_aggregate_path(country)
        district = _merge_and_upload(blob_client, container, district_blob, non_empty, district_weeks)
        logger.info("[%s] District longitudinal updated -> %s (%d rows)", country, district_blob, len(district))


def update_longitudinal_aggregates(
    country: str,
    extended_frame: pd.DataFrame,
    year: int,
    week: int,
    blob_client,
    container: str,
) -> None:
    """Single-week update used by the weekly pipeline (signature unchanged)."""
    baseline_rows, demo_rows = build_week_aggregates(extended_frame, year, week)
    district_rows = build_week_district_aggregate(extended_frame, year, week)
    upload_longitudinal_aggregates(
        country,
        [baseline_rows],
        [demo_rows],
        [_week_label(year, week)],
        blob_client,
        container,
        district_parts=[district_rows],
    )
