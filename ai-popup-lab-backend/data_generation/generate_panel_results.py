"""
Panel generation orchestration: ties together attrition/replacement,
biography population, and the survey wave into one cycle for a single
country + ISO week.

Pipeline order per cycle:
  1. Attrition + replacement (panel.attrition) — retire ~10% of the active
     panel, replace with a fresh weighted draw from the stratification frame.
  2. Biography generation (panel.biography) — only for this cycle's new
     joiners; existing panellists keep their existing biography + media_diet.
  3. Survey wave (panel.runner) — run on the full panel (existing + new
     joiners together).

Two entry points share this core cycle but read/write different Azure
storage tracks:
  - generate_panel_results(...)          — production weekly track
  - generate_panel_results_backfill(...) — backfill track (separate active
    panel state, separate historical snapshots, separate job-lock type), so
    a backfill run never touches live production panel state.

`azure_storage_utils` owns its own BlobServiceClient internally now (see that
module) — nothing in this file passes a client around.
"""
from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import pandas as pd
from isoweek import Week

import azure_storage_utils as storage
from .panel.attrition import apply_attrition_and_replacement, PANEL_SIZE, ATTRITION_RATE
from .panel.biography import populate_panel
from .panel.runner import run_survey

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
COUNTRY_INFO_PATH = BASE_DIR / "country_data" / "country_data_info.json"


def iso_week_label(year: int, week: int) -> str:
    """Canonical filename/blob label for a given ISO year+week, e.g. '2026_18'."""
    return f"{year}_{week:02d}"


def isoweek_to_panel_date(year: int, week: int) -> str:
    """Return the Monday of the given ISO week as YYYYMMDD — used to name
    this cycle's wave columns and to seed attrition's random draw."""
    return Week(year, week).monday().strftime("%Y%m%d")


def _load_country_info(country: str) -> dict:
    with open(COUNTRY_INFO_PATH) as f:
        country_info = json.load(f)
    info = country_info.get(country)
    if info is None:
        raise ValueError(f"No entry for '{country}' in {COUNTRY_INFO_PATH}")
    return info


def _download_strat_frame(country: str, tmp_dir: Path) -> Path:
    """Pull the country's stratification frame from blob down to a local
    temp file — attrition.draw_new_panelists reads from a local path."""
    frame_df = storage.read_dataframe(storage.get_stratification_frame_path(country))
    frame_path = tmp_dir / f"{country}_strat_frame.csv"
    frame_df.to_csv(frame_path, index=False)
    return frame_path


def _run_panel_cycle(
    country: str,
    year: int,
    week: int,
    question_id: str,
    display_name: str,
    active_panel_path: str,
    historical_panel_path: str,
    gdelt_cache_path: str,
    attrition_lock_type: str,
) -> pd.DataFrame:
    """
    Runs one full attrition -> biography -> survey cycle and returns the
    updated panel. Handles all Azure reads/writes except the overall job
    lock, which the caller sets (since its job_type differs between
    production and backfill).

    Resumable at every stage: attrition/replacement only ever runs once per
    country/week (guarded by `attrition_lock_type`, checked/marked the same
    way as the other job locks) — a crash mid-biography or mid-survey and
    subsequent rerun picks up from wherever `active_panel_path` was last
    checkpointed, rather than re-drawing new replacements or re-retiring
    panellists that already went through this week's cycle. Biography and
    survey checkpoints are written straight to `active_panel_path` itself
    (not a separate scratch blob) specifically so a restart's initial read
    sees that partial progress.
    """
    label = f"{country} {iso_week_label(year, week)}"
    week_label = iso_week_label(year, week)
    panel_date = isoweek_to_panel_date(year, week)

    with tempfile.TemporaryDirectory() as tmp:
        # ── 1. Attrition + replacement (only once per country/week) ───────
        panel_df = storage.read_dataframe_or_none(active_panel_path)

        if storage.already_ran(country, attrition_lock_type, week_label):
            logger.info("[%s] Attrition already applied this week — resuming current panel state.", label)
        else:
            strat_frame_path = _download_strat_frame(country, Path(tmp))
            panel_df = apply_attrition_and_replacement(
                panel_df,
                strat_frame_path,
                panel_date=panel_date,
                panel_size=PANEL_SIZE,
                attrition_rate=ATTRITION_RATE,
            )
            # Persist immediately — this is also what makes the attrition
            # lock meaningful: from here on, a resumed run sees this week's
            # post-attrition panel (new joiners included, biography NA)
            # rather than None or last week's panel.
            storage.upload_dataframe(panel_df, active_panel_path)
            storage.mark_job_ran(country, attrition_lock_type, week_label)

        # ── 2. Biographies for this cycle's new joiners ───────────────────
        missing_bio = int(panel_df["biography"].isna().sum())
        if missing_bio:
            logger.info("[%s] Generating %d new-joiner biographies...", label, missing_bio)

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

        # ── 3. Survey wave ─────────────────────────────────────────────────
        news_df = storage.read_dataframe_or_none(gdelt_cache_path)
        if news_df is not None:
            logger.info("[%s] Loaded GDELT cache from blob (%d rows).", label, len(news_df))
        else:
            logger.info("[%s] No GDELT cache found — runner will download from GDELT.", label)

        def survey_checkpoint(current_panel: pd.DataFrame) -> None:
            storage.upload_dataframe(current_panel, active_panel_path)

        panel_df, news_df = run_survey(
            question_id=question_id,
            panel_df=panel_df,
            panel_date=panel_date,
            news_df=news_df,
            on_checkpoint=survey_checkpoint,
        )

        # ── 4. Persist outputs ─────────────────────────────────────────────
        storage.upload_dataframe(panel_df, historical_panel_path)
        logger.info("[%s] Results snapshot uploaded to %s", label, historical_panel_path)

        storage.upload_dataframe(panel_df, active_panel_path)
        logger.info("[%s] Active panel state updated.", label)

        if news_df is not None:
            storage.upload_dataframe(news_df, gdelt_cache_path)
            logger.info("[%s] GDELT cache updated.", label)

    return panel_df


def generate_panel_results(
    country: str,
    year: int,
    week: int,
    force: bool = False,
) -> None:
    """
    Run one production weekly cycle (attrition -> biographies -> survey) for
    `country` / ISO week `year`-W`week`. Skips if a lock already exists for
    this country/week, unless `force=True`.
    """
    info = _load_country_info(country)
    question_id = info.get("question_id")
    if not question_id:
        logger.info("Panel not configured for %s — skipping.", country)
        return

    week_label = iso_week_label(year, week)

    if not force and storage.already_ran(country, "panel", week_label):
        logger.info("Panel results already exist for %s %s — skipping.", country, week_label)
        return

    display_name = info.get("alias", country.title())

    logger.info("Generating panel results: country=%s, week=%s", country, week_label)

    _run_panel_cycle(
        country=country,
        year=year,
        week=week,
        question_id=question_id,
        display_name=display_name,
        active_panel_path=storage.get_active_panel_path(country),
        historical_panel_path=storage.get_historical_panel_path(country, week_label),
        gdelt_cache_path=storage.get_gdelt_cache_path(country, week_label),
        attrition_lock_type="attrition",
    )

    storage.mark_job_ran(country, "panel", week_label)
    logger.info("Panel generation complete: %s %s", country, week_label)


def generate_panel_results_backfill(
    country: str,
    year: int,
    week: int,
    force: bool = False,
) -> None:
    """
    Run one backfill cycle (attrition -> biographies -> survey) for
    `country` / ISO week `year`-W`week`, entirely on the backfill storage
    track — reads/writes `get_backfill_active_panel_path` instead of the
    production active panel, so this never touches live panel state.

    Before the first backfilled week, seed
    `get_backfill_active_panel_path(country)` with the week-(t-1) panel.
    Subsequent weeks in a sequential backfill run pick up from where the
    previous backfilled week left that same blob.
    """
    info = _load_country_info(country)
    question_id = info.get("question_id")
    if not question_id:
        logger.info("Panel not configured for %s — skipping.", country)
        return

    week_label = iso_week_label(year, week)

    if not force and storage.already_ran(country, "panel_backfill", week_label):
        logger.info("Backfill panel results already exist for %s %s — skipping.", country, week_label)
        return

    display_name = info.get("alias", country.title())

    logger.info("Backfilling panel results: country=%s, week=%s", country, week_label)

    _run_panel_cycle(
        country=country,
        year=year,
        week=week,
        question_id=question_id,
        display_name=display_name,
        active_panel_path=storage.get_backfill_active_panel_path(country),
        historical_panel_path=storage.get_backfill_historical_panel_path(country, week_label),
        gdelt_cache_path=storage.get_gdelt_cache_path(country, week_label),
        attrition_lock_type="attrition_backfill",
    )

    storage.mark_job_ran(country, "panel_backfill", week_label)
    logger.info("Backfill panel generation complete: %s %s", country, week_label)
