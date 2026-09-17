"""
Hotfix backfill — stage 1: attrition + biography/media_diet, USA only.

This is the *sequential* half of the split hotfix backfill. For a given ISO
week it:
  1. Retires ~10% of the panel and replaces them with a fresh weighted draw
     from the stratification frame (or draws a full panel from scratch if
     none exists yet) — panel.attrition.
  2. Generates biography + media_diet for this cycle's new joiners only —
     panel.biography.

It deliberately stops there. It does NOT run the survey wave (news read +
vote choice) or the R extended-frame step — those belong to stage 2
(hotfix_backfill_stage2.py), which is safe to run in parallel across weeks
*because* every week's stage-1 output is fully self-contained before stage 2
ever touches it.

Weeks MUST be run through this module in ascending chronological order,
one after another — week N's attrition step reads whatever
`get_hotfix_backfill_active_panel_path` currently holds, which has to be
week N-1's post-attrition, post-biography panel. See
hotfix_backfill_stage1_entry.py for the sequential driver that enforces
this ordering; nothing in this module reorders or parallelizes weeks
itself.

This track is entirely separate from both production
(get_active_panel_path) and the older full-cycle backfill track
(get_backfill_active_panel_path) — see azure_storage_utils.py's
hotfix_backfill_* path helpers.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pandas as pd

import azure_storage_utils as storage
from .panel.attrition import apply_attrition_and_replacement, PANEL_SIZE, ATTRITION_RATE
from .panel.biography import populate_panel
from .generate_panel_results import (
    iso_week_label,
    isoweek_to_panel_date,
    _load_country_info,
    _download_strat_frame,
)

logger = logging.getLogger(__name__)

STAGE1_JOB_TYPE = "hotfix_backfill_stage1"


def run_stage1_week(country: str, year: int, week: int, force: bool = False) -> pd.DataFrame:
    """
    Run attrition/replacement + biography/media_diet for one ISO week, on
    the hotfix-backfill storage track, and persist a per-week snapshot to
    `get_hotfix_backfill_biography_panel_path`.

    Before calling this for the *first* week of a run, seed
    `get_hotfix_backfill_active_panel_path(country)` with a genuine
    week-(t-1) panel (e.g. a copy of the production active panel, or a
    prior historical/backfill panel for the week immediately before). This
    function never seeds that blob itself — if it's missing, attrition
    treats it as a cold start and draws a brand-new panel, which is only
    correct if you actually mean to start from scratch.

    Idempotent per (country, week): if a lock already exists for this week
    and `force` is False, this returns the already-written biography-panel
    snapshot rather than redoing the work.
    """
    week_label = iso_week_label(year, week)

    if not force and storage.already_ran(country, STAGE1_JOB_TYPE, week_label):
        logger.info("[%s %s] Stage 1 already completed — returning existing snapshot.", country, week_label)
        return storage.read_dataframe(storage.get_hotfix_backfill_biography_panel_path(country, week_label))

    info = _load_country_info(country)
    display_name = info.get("alias", country.title())
    panel_date = isoweek_to_panel_date(year, week)

    active_panel_path = storage.get_hotfix_backfill_active_panel_path(country)
    biography_panel_path = storage.get_hotfix_backfill_biography_panel_path(country, week_label)

    with tempfile.TemporaryDirectory() as tmp:
        panel_df = storage.read_dataframe_or_none(active_panel_path)

        # ── Attrition + replacement ─────────────────────────────────────
        strat_frame_path = _download_strat_frame(country, Path(tmp))
        panel_df = apply_attrition_and_replacement(
            panel_df,
            strat_frame_path,
            panel_date=panel_date,
            panel_size=PANEL_SIZE,
            attrition_rate=ATTRITION_RATE,
        )
        # Persist immediately so a crash mid-biography resumes from this
        # week's post-attrition state (new joiners included, biography
        # null) rather than re-drawing replacements on retry.
        storage.upload_dataframe(panel_df, active_panel_path)

        # ── Biographies + media_diet for this cycle's new joiners ────────
        missing_bio = int(panel_df["biography"].isna().sum())
        if missing_bio:
            logger.info("[%s %s] Generating %d new-joiner biographies...", country, week_label, missing_bio)

            def bio_checkpoint(current_panel: pd.DataFrame) -> None:
                storage.upload_dataframe(current_panel, active_panel_path)

            panel_df = populate_panel(
                panel_df,
                display_name,
                delay_seconds=0.01,
                date=panel_date,
                on_checkpoint=bio_checkpoint,
            )
            storage.upload_dataframe(panel_df, active_panel_path)

    # Snapshot this week's fully-biographied panel under its own per-week
    # blob. This — not the ever-advancing active panel — is what stage 2
    # reads: stage 2 runs per-week, potentially in several containers at
    # once, so it needs a stable input that later weeks won't overwrite.
    storage.upload_dataframe(panel_df, biography_panel_path)
    storage.mark_job_ran(country, STAGE1_JOB_TYPE, week_label)
    logger.info("[%s %s] Stage 1 complete — biography panel snapshot written to %s.",
                country, week_label, biography_panel_path)

    return panel_df
