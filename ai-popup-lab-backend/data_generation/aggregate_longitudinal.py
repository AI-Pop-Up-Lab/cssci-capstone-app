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
)

# ── column config ────────────────────────────────────────────────────────────

DEMOGRAPHIC_COLS = ["age_group", "gender", "race", "state_abbrv", "education_level"]
PARTY_COL        = "party"
WEIGHT_COL       = "prob_raked"

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


def upload_longitudinal_aggregates(
    country: str,
    baseline_parts: list[pd.DataFrame],
    demographic_parts: list[pd.DataFrame],
    week_labels: list[str],
    blob_client,
    container: str,
) -> None:
    """Merge any number of weeks' aggregate rows into the stored files with one download/upload each."""
    baseline_blob = get_simple_frame_aggregate_path(country)
    demo_blob     = get_demographic_frame_aggregate_path(country)

    baseline = _merge_and_upload(blob_client, container, baseline_blob, baseline_parts, week_labels)
    logger.info("[%s] Baseline longitudinal updated -> %s (%d rows)", country, baseline_blob, len(baseline))

    demographic = _merge_and_upload(blob_client, container, demo_blob, demographic_parts, week_labels)
    logger.info("[%s] Demographic longitudinal updated -> %s (%d rows)", country, demo_blob, len(demographic))


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
    upload_longitudinal_aggregates(
        country,
        [baseline_rows],
        [demo_rows],
        [_week_label(year, week)],
        blob_client,
        container,
    )
