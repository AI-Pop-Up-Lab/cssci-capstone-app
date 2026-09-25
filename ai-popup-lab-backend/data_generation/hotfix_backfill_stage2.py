"""
Hotfix backfill — stage 2: survey wave (vote choice) + MRP extended frame,
USA only.

This is the *parallel-safe* half of the split hotfix backfill. For a given
ISO week it:
  1. Reads the biography-only panel that stage 1
     (hotfix_backfill_stage1.py) already produced for that week —
     `get_hotfix_backfill_biography_panel_path` — every panellist already
     has a biography and media_diet at this point, nothing here touches
     attrition or biography generation.
  2. Runs that week's survey wave: GDELT news read, Cohere RAG article
     interpretation, and vote-choice generation — panel.runner.run_survey.
  3. Runs the US post-stratification R script on the resulting panel to
     produce that week's MRP extended frame.

Unlike stage 1, weeks are independent of each other here: each week's
stage-1 biography panel is already fully formed, and the survey wave for
week N only needs week N's own panel + that week's news, never another
week's vote-choice results. That's exactly what makes it safe to call
`run_stage2_week` for several different weeks concurrently (e.g. from
separate parallel ACI containers, see hotfix_backfill_stage2_entry.py) —
each call only reads/writes blobs scoped to its own week, aside from the
shared GDELT cache, which is itself keyed per week so different weeks'
containers never contend over the same cache blob.

Like the existing production MRP backfill path, this never touches
production's longitudinal aggregates — it's a standalone hotfix track.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pandas as pd

import azure_storage_utils as storage
from .panel.runner import run_survey
from .generate_panel_results import iso_week_label, isoweek_to_panel_date, _load_country_info
from .run_scripts import run_extension_script
from .run_job import _prepare_frame_for_r, _prepare_survey_for_r, COMPUTE_MRP_DRAWS

logger = logging.getLogger(__name__)

STAGE2_JOB_TYPE = "hotfix_backfill_stage2"


def run_stage2_week(country: str, year: int, week: int, force: bool = False) -> None:
    """
    Run the survey wave + R extended frame for one week that stage 1 has
    already finished. Safe to call concurrently for different weeks — each
    call is scoped to its own week's blobs (biography panel in, vote-choice
    panel + extended frame out), plus the shared per-week GDELT cache.

    Idempotent per (country, week): if a lock already exists for this week
    and `force` is False, this is a no-op.
    """
    week_label = iso_week_label(year, week)

    if not force and storage.already_ran(country, STAGE2_JOB_TYPE, week_label):
        logger.info("[%s %s] Stage 2 already completed — skipping.", country, week_label)
        return

    info = _load_country_info(country)
    question_id = info.get("question_id")
    if not question_id:
        logger.info("[%s] Panel not configured — skipping stage 2 for %s.", country, week_label)
        return

    panel_date = isoweek_to_panel_date(year, week)
    biography_panel_path = storage.get_hotfix_backfill_biography_panel_path(country, week_label)
    vote_panel_path = storage.get_hotfix_backfill_vote_panel_path(country, week_label)
    extended_frame_path = storage.get_hotfix_backfill_extended_frame_path(country, week_label)
    gdelt_cache_path = storage.get_gdelt_cache_path(country, week_label)

    panel_df = storage.read_dataframe_or_none(biography_panel_path)
    if panel_df is None:
        raise FileNotFoundError(
            f"No stage-1 biography panel found for {country} {week_label} "
            f"(expected blob: {biography_panel_path}). Run hotfix-backfill stage 1 "
            f"for this week before stage 2."
        )

    # ── Step 3: survey wave (news read + vote choice) ──────────────────────
    news_df = storage.read_dataframe_or_none(gdelt_cache_path)
    if news_df is not None:
        logger.info("[%s %s] Loaded GDELT cache from blob (%d rows).", country, week_label, len(news_df))
    else:
        logger.info("[%s %s] No GDELT cache found — runner will download from GDELT.", country, week_label)

    def survey_checkpoint(current_panel: pd.DataFrame) -> None:
        storage.upload_dataframe(current_panel, vote_panel_path)

    panel_df, news_df = run_survey(
        question_id=question_id,
        panel_df=panel_df,
        panel_date=panel_date,
        news_df=news_df,
        on_checkpoint=survey_checkpoint,
    )

    storage.upload_dataframe(panel_df, vote_panel_path)
    logger.info("[%s %s] Vote-choice panel uploaded to %s.", country, week_label, vote_panel_path)

    if news_df is not None:
        storage.upload_dataframe(news_df, gdelt_cache_path)
        logger.info("[%s %s] GDELT cache updated.", country, week_label)

    # ── Step 4: MRP extended frame via R ────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        frame_path = tmp_path / f"{country}_strat_frame.csv"
        frame_df = storage.read_dataframe(storage.get_stratification_frame_path(country))
        frame_df = _prepare_frame_for_r(frame_df)
        frame_df.to_csv(frame_path, index=False)

        area_shares_path = None
        if country.lower() == "usa":
            area_shares_blob = storage.get_area_level_vote_shares_path(country)
            area_shares_df = storage.read_dataframe_or_none(area_shares_blob)
            if area_shares_df is None:
                raise FileNotFoundError(
                    f"No area-level vote shares file found for {country} "
                    f"(expected blob: {area_shares_blob}). Upload it before running "
                    f"hotfix backfill stage 2 — post_strat_module_us.R requires it."
                )
            area_shares_path = tmp_path / f"{country}_area_level_vote_shares.csv"
            area_shares_df.to_csv(area_shares_path, index=False)

        survey_df = _prepare_survey_for_r(panel_df, panel_date)
        survey_path = tmp_path / f"{country}_{week_label}_panel_results.csv"
        survey_df.to_csv(survey_path, index=False)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        run_extension_script(
            survey_path=survey_path,
            frame_path=frame_path,
            output_dir=output_dir,
            country=country,
            compute_draws=COMPUTE_MRP_DRAWS,
            area_shares_path=area_shares_path,
        )

        r_output_path = output_dir / "mrp_extended_frame_predictions.csv"
        if not r_output_path.exists():
            raise FileNotFoundError(f"Expected R output not found: {r_output_path}")

        extended_frame = pd.read_csv(r_output_path)
        storage.upload_dataframe(extended_frame, extended_frame_path)
        logger.info("[%s %s] Extended frame uploaded to %s.", country, week_label, extended_frame_path)

    # Hotfix-backfill track — like the existing MRP backfill path, this
    # never updates production's longitudinal aggregates.
    storage.mark_job_ran(country, STAGE2_JOB_TYPE, week_label)
    logger.info("[%s %s] Stage 2 complete.", country, week_label)
