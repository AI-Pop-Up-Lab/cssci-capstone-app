"""
Attrition + replacement for the synthetic panel.

Each cycle, a fixed fraction of the active panel is retired and replaced with
an equal number of fresh panellists, weighted-sampled from the country's
stratification frame. This runs *before* the survey wave — replacements are
returned with `biography` (and every wave/survey column) null, so the caller
should run `panel.biography.populate_panel` on the result next (which only
fills in null-biography rows — i.e. only this cycle's new joiners) and then
`panel.runner.run_survey` on the full panel, existing panellists and new
joiners together.

Every panellist gets a persistent, globally-unique `panelist_id` at draw time.
Because the ID is unique per *draw* — not tied to `cell_id`, which repeats
across past_vote splits in the stratification frame and was never a stable
per-panellist identity — there's no need to track or exclude previously-used
cell_ids when sampling replacements. Duplicate cell_id draws across weeks are
expected and fine: they represent different synthetic people sampled from the
same demographic/past-vote cell, not the same person twice.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Hardcoded and shared across every country using this pipeline.
PANEL_SIZE = 4000
ATTRITION_RATE = 0.10


def _assign_ages(df: pd.DataFrame) -> pd.DataFrame:
    """Assign a random concrete age within each row's age_group bucket."""
    df = df.copy()
    df["age"] = df["age_group"].apply(
        lambda x: np.random.randint(int(x[:-1]), 101) if "+" in x
        else np.random.randint(int(x.split("-")[0]), int(x.split("-")[1]) + 1)
    )
    return df


def draw_new_panelists(
    strat_frame_path: str | Path,
    n: int,
    random_state: int | None = None,
) -> pd.DataFrame:
    """
    Weighted (by cell size `N`) sample of `n` fresh panellists from the full
    stratification frame. Each row gets a fresh, globally-unique
    `panelist_id`, a concrete `age`, and a null `biography`.

    Any column not produced here (e.g. wave/survey columns from prior weeks)
    is simply absent — callers concatenating this onto an existing panel
    should reindex so those come through as null for the new rows.
    """
    frame = pd.read_csv(strat_frame_path)
    if len(frame) == 0:
        raise ValueError(f"Stratification frame at {strat_frame_path} is empty.")

    if n > len(frame):
        logger.warning(
            "Requested %d panellists but stratification frame only has %d rows — sampling with replacement.",
            n, len(frame),
        )
        sampled = frame.sample(n=n, weights="N", random_state=random_state, replace=True).reset_index(drop=True)
    else:
        sampled = frame.sample(n=n, weights="N", random_state=random_state).reset_index(drop=True)

    sampled = _assign_ages(sampled)
    sampled["panelist_id"] = [str(uuid.uuid4()) for _ in range(len(sampled))]
    sampled["biography"] = pd.NA
    return sampled


def apply_attrition_and_replacement(
    panel_df: pd.DataFrame | None,
    strat_frame_path: str | Path,
    panel_date: str,
    panel_size: int = PANEL_SIZE,
    attrition_rate: float = ATTRITION_RATE,
) -> pd.DataFrame:
    """
    Cold start: if `panel_df` is None/empty, draw a fresh panel of
    `panel_size` panellists entirely from the stratification frame.

    Otherwise: retire `round(panel_size * attrition_rate)` random rows and
    replace them with an equal number of fresh draws, keeping the panel at a
    constant `panel_size`. New joiners have no biography yet — run
    `populate_panel` on the result before surveying.

    `panel_date` (YYYYMMDD) seeds the random retirement/replacement draw, so
    a given week's attrition is reproducible if this needs to be rerun.
    """
    seed = int(panel_date)

    if panel_df is None or len(panel_df) == 0:
        logger.info("No existing panel — cold-starting %d panellists from %s.", panel_size, strat_frame_path)
        return draw_new_panelists(strat_frame_path, panel_size, random_state=seed)

    attrition_count = min(int(round(panel_size * attrition_rate)), len(panel_df))
    if attrition_count <= 0:
        return panel_df

    retired_idx = panel_df.sample(n=attrition_count, random_state=seed).index
    logger.info("Retiring %d/%d panellists.", attrition_count, len(panel_df))
    survivors = panel_df.drop(index=retired_idx).reset_index(drop=True)

    replacements = draw_new_panelists(strat_frame_path, attrition_count, random_state=seed)

    # Align columns both ways: new joiners get null for wave/history columns
    # they don't have; the union preserves both frames' columns.
    all_columns = survivors.columns.union(replacements.columns, sort=False)
    survivors = survivors.reindex(columns=all_columns, fill_value=pd.NA)
    replacements = replacements.reindex(columns=all_columns, fill_value=pd.NA)

    updated = pd.concat([survivors, replacements], ignore_index=True)
    logger.info("Panel replenished: %d new joiners, %d total.", attrition_count, len(updated))
    return updated
