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
     produce that week's MRP extended frame, and stores EVERY CSV the R
     script writes (not just the extended frame) on the hotfix track.

Two modes (`mrp_only`):
  * default      — steps 1-3 above.
  * mrp_only     — skips steps 1-2 and runs step 3 against the vote-choice
                   panel already saved at `get_hotfix_backfill_vote_panel_path`
                   (written by a previous run whose R step failed or was never
                   reached). Refuses to run if that panel is missing or its
                   vote column isn't fully populated — the survey wave
                   checkpoints a *partial* panel to the same blob while it
                   runs, so blob existence alone doesn't mean "finished".

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
from .run_job import _prepare_frame_for_r, _prepare_survey_for_r

logger = logging.getLogger(__name__)

STAGE2_JOB_TYPE = "hotfix_backfill_stage2"

# The hotfix wants every output the R script can produce. (For country ==
# "usa" the R module currently computes the simulation draws regardless of
# this flag, but keep it True so the intent is explicit and nothing silently
# changes if the module ever reintroduces a real gate.) Deliberately NOT
# imported from run_job.COMPUTE_MRP_DRAWS, which is the production setting.
STAGE2_COMPUTE_DRAWS = True

# Also write the raw per-cell draw matrix (mrp_cell_draws.csv). Large: rows =
# frame cells x parties, columns = n_sims draws — watch container memory.
STAGE2_EXPORT_CELL_DRAWS = True

EXTENDED_FRAME_FILENAME = "mrp_extended_frame_predictions.csv"

# Files write_post_strat_outputs() always writes for the US module. Missing
# any of these means the R run didn't finish cleanly, so we refuse to mark the
# week done. (mrp_margin_*.csv are variable in number; mrp_cell_draws.csv
# only appears with config$export_cell_draws, so it's listed only because
# STAGE2_EXPORT_CELL_DRAWS is on — drop it from here if you turn that off.)
EXPECTED_R_OUTPUTS = (
    "mrp_point_estimates.csv",
    "mrp_national_summary_95ci.csv",
    EXTENDED_FRAME_FILENAME,
    "mrp_stage_diagnostics.csv",
    "mrp_aggregate_counts.csv",
    "mrp_share_draws.csv",
    "mrp_share_draws_long.csv",
    "mrp_cell_party_probabilities.csv",
    "mrp_stickbreaking_conditional_probs.csv",
    "mrp_cd_party_point_estimates.csv",
    "mrp_cd_party_draws_long.csv",
    "mrp_cd_party_95ci.csv",
    "mrp_cell_draws.csv",
)

# Column names the vote outcome can have (mirrors survey_aliases in
# post_strat_module_us.R). Used only for the completeness check.
VOTE_COLUMN_CANDIDATES = ("vote_2026", "predicted_vote")


def _vote_completeness(df: pd.DataFrame) -> tuple[str | None, int, int]:
    """(column used, rows with a non-empty vote, total rows); column is None if not found."""
    for col in VOTE_COLUMN_CANDIDATES:
        if col in df.columns:
            s = df[col]
            filled = int((s.notna() & (s.astype(str).str.strip() != "")).sum())
            return col, filled, len(df)
    return None, 0, len(df)


def _run_mrp(country: str, week_label: str, panel_df: pd.DataFrame, panel_date) -> None:
    """Run the R post-stratification on a complete vote-choice panel and store all outputs."""
    extended_frame_path = storage.get_hotfix_backfill_extended_frame_path(country, week_label)

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
            compute_draws=STAGE2_COMPUTE_DRAWS,
            export_cell_draws=STAGE2_EXPORT_CELL_DRAWS,
            area_shares_path=area_shares_path,
        )

        produced = {p.name: p for p in output_dir.glob("*.csv")}
        missing = [name for name in EXPECTED_R_OUTPUTS if name not in produced]
        if missing:
            raise FileNotFoundError(
                f"R finished but expected outputs are missing for {country} {week_label}: {missing}. "
                f"Found: {sorted(produced)}"
            )

        # Extended frame: same handling as before (pandas round-trip, which
        # also normalises R's "NA" strings to empty cells) at its own path.
        extended_frame = pd.read_csv(produced[EXTENDED_FRAME_FILENAME])
        storage.upload_dataframe(extended_frame, extended_frame_path)
        logger.info("[%s %s] Extended frame uploaded to %s.", country, week_label, extended_frame_path)

        # Everything else the R script wrote, uploaded byte-for-byte.
        for name, local_path in sorted(produced.items()):
            if name == EXTENDED_FRAME_FILENAME:
                continue
            blob_path = storage.get_hotfix_backfill_mrp_output_path(country, week_label, name)
            storage.upload_file(local_path, blob_path)
            logger.info("[%s %s] Uploaded %s -> %s", country, week_label, name, blob_path)

        logger.info(
            "[%s %s] Stored %d R output file(s) (extended frame + %d auxiliary).",
            country, week_label, len(produced), len(produced) - 1,
        )


def run_stage2_week(
    country: str,
    year: int,
    week: int,
    force: bool = False,
    mrp_only: bool = False,
) -> None:
    """
    Run the survey wave + R extended frame for one week that stage 1 has
    already finished (or, with mrp_only=True, just the R step against an
    already-complete vote-choice panel). Safe to call concurrently for
    different weeks — each call is scoped to its own week's blobs.

    Idempotent per (country, week): if a lock already exists for this week
    and `force` is False, this is a no-op. The lock is only written after the
    R outputs have all been uploaded.
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
    vote_panel_path = storage.get_hotfix_backfill_vote_panel_path(country, week_label)

    # ── MRP-only: reuse the saved vote-choice panel, skip the survey wave ────
    if mrp_only:
        panel_df = storage.read_dataframe_or_none(vote_panel_path)
        if panel_df is None:
            raise FileNotFoundError(
                f"MRP-only: no vote-choice panel found for {country} {week_label} "
                f"(expected blob: {vote_panel_path}). Run stage 2 normally for this week."
            )

        col, filled, total = _vote_completeness(panel_df)
        if col is None:
            # The vote column may be renamed by _prepare_survey_for_r — check what R will actually see.
            col, filled, total = _vote_completeness(_prepare_survey_for_r(panel_df, panel_date))
        if col is None:
            raise ValueError(
                f"MRP-only: couldn't find a vote column ({VOTE_COLUMN_CANDIDATES}) in the panel or "
                f"the R-ready survey for {country} {week_label}; can't verify the panel is complete. "
                f"Panel columns: {list(panel_df.columns)}"
            )
        if filled < total:
            raise ValueError(
                f"MRP-only: vote-choice panel for {country} {week_label} is incomplete "
                f"({filled}/{total} rows have '{col}'). The survey wave is still running or was "
                f"interrupted — refusing to run MRP on a partial panel."
            )
        logger.info("[%s %s] MRP-only: vote-choice panel complete (%d/%d rows).", country, week_label, filled, total)

    # ── Full mode: survey wave (news read + vote choice) ─────────────────────
    else:
        biography_panel_path = storage.get_hotfix_backfill_biography_panel_path(country, week_label)
        gdelt_cache_path = storage.get_gdelt_cache_path(country, week_label)

        panel_df = storage.read_dataframe_or_none(biography_panel_path)
        if panel_df is None:
            raise FileNotFoundError(
                f"No stage-1 biography panel found for {country} {week_label} "
                f"(expected blob: {biography_panel_path}). Run hotfix-backfill stage 1 "
                f"for this week before stage 2."
            )

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

    # ── MRP extended frame + all other R outputs ─────────────────────────────
    _run_mrp(country, week_label, panel_df, panel_date)

    # Hotfix-backfill track — like the existing MRP backfill path, this
    # never updates production's longitudinal aggregates.
    storage.mark_job_ran(country, STAGE2_JOB_TYPE, week_label)
    logger.info("[%s %s] Stage 2 complete.", country, week_label)
