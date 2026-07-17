"""
runs synthetic panel result generation for a given country and ISO week.
called by run_job.py for weekly runs and backfill-job.yml for backfills.

also gets data from azure storage
"""
from __future__ import annotations

import io
import json
import logging
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
from azure.storage.blob import BlobServiceClient
from isoweek import Week 

from .panel.biography import populate_panel
from .panel.runner import run_survey
from .store_data import get_blob_client, CONTAINER_NAME, results_blob_name, biography_snapshot_blob_name

logger = logging.getLogger(__name__)

BASE_DIR   = Path(__file__).resolve().parent.parent
PANELS_DIR = BASE_DIR / "country_data" / "panels"
COUNTRY_INFO_PATH = BASE_DIR / "country_data" / "country_data_info.json"

_COUNTRY_DISPLAY = {
    "sweden":      "Sweden",
    "netherlands": "Netherlands",
    "denmark":     "Denmark",
    "usa": "The USA",
}

# ── Blob path helpers ─────────────────────────────────────────────────────────

def _active_panel_blob(country: str) -> str:
    return f"panel-state/{country}/active_panel.csv"

def _results_blob(country: str, year: int, week: int) -> str:
    return results_blob_name(country, year, week)

def _gdelt_blob(country: str, year: int, week: int) -> str:
    return f"gdelt-cache/{country}/{year}_{week:02d}_gdelt.csv"

def _panel_guard_blob(country: str, year: int, week: int) -> str:
    return f"job-runs/panel/{country}/{year}_{week:02d}.lock"

def _backfill_panel_blob(country: str, year: int, week: int) -> str:
    """per-week input panel for parallel vote-choice backfill runs unlike from _active_panel_blob, which is the shared rolling panel state."""
    return f"panel-state/{country}/backfill/{year}_{week:02d}_{country}_panel.csv"

def _vote_choice_guard_blob(country: str, year: int, week: int) -> str:
    return f"job-runs/vote-choice-backfill/{country}/{year}_{week:02d}.lock"

def _backfill_checkpoint_blob(country: str, year: int, week: int) -> str:
    """Scratch checkpoint for in-progress vote-choice backfill runs. Never used as an input."""
    return f"panel-state/{country}/backfill/checkpoints/{year}_{week:02d}_{country}_panel_checkpoint.csv"

# ── Low-level blob helpers ────────────────────────────────────────────────────

def _blob_exists(client: BlobServiceClient, blob_name: str) -> bool:
    try:
        client.get_blob_client(container=CONTAINER_NAME, blob=blob_name).get_blob_properties()
        return True
    except Exception:
        return False

def _download_df(client: BlobServiceClient, blob_name: str) -> pd.DataFrame | None:
    try:
        data = client.get_blob_client(container=CONTAINER_NAME, blob=blob_name).download_blob().readall()
        return pd.read_csv(io.BytesIO(data))
    except Exception:
        return None

def _upload_df(client: BlobServiceClient, blob_name: str, df: pd.DataFrame) -> None:
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    client.get_blob_client(container=CONTAINER_NAME, blob=blob_name).upload_blob(buf, overwrite=True)
    logger.info("Uploaded %s (%d rows)", blob_name, len(df))

# ── Public API ────────────────────────────────────────────────────────────────

def already_ran_panel(client: BlobServiceClient, country: str, year: int, week: int) -> bool:
    return _blob_exists(client, _panel_guard_blob(country, year, week))

def mark_ran_panel(client: BlobServiceClient, country: str, year: int, week: int) -> None:
    blob = client.get_blob_client(container=CONTAINER_NAME, blob=_panel_guard_blob(country, year, week))
    blob.upload_blob(b"done", overwrite=True)

def isoweek_to_panel_date(year: int, week: int) -> str:
    """Return the Monday of the given ISO week as YYYYMMDD."""
    return Week(year, week).monday().strftime("%Y%m%d")

def generate_panel_biographies_only(
    country: str,
    year: int,
    week: int,
    client: BlobServiceClient | None = None,
    generate_events: bool = False,
    articles_path: str | Path | None = None,
) -> None:
    """
    Populate (or top up) biographies for a country's active panel WITHOUT
    running a survey wave. Intended for standing up a new panel — e.g.
    building the US panel — before turning on weekly surveys for it.
    """
    if client is None:
        client = get_blob_client()

    with open(COUNTRY_INFO_PATH) as f:
        country_info = json.load(f)

    info = country_info.get(country, {})
    panel_filename = info.get("panel_filename")
    if not panel_filename:
        raise ValueError(f"No panel_filename configured for '{country}' in {COUNTRY_INFO_PATH}")

    display_name = _COUNTRY_DISPLAY.get(country, country.title())
    panel_date = isoweek_to_panel_date(year, week)

    panel_df = _download_df(client, _active_panel_blob(country))
    if panel_df is None:
        logger.info("No active panel in blob — initialising from %s", panel_filename)
        source = PANELS_DIR / panel_filename
        if not source.exists():
            raise FileNotFoundError(
                f"Base panel file not found: {source}\n"
                f"Copy {panel_filename} to country_data/panels/ in the backend repo."
            )
        panel_df = pd.read_csv(source)
        if "biography" not in panel_df.columns:
            panel_df["biography"] = pd.NA

    missing_bio = int(panel_df["biography"].isna().sum())
    if not missing_bio:
        logger.info("All %d panelists already have biographies for %s — nothing to do.", len(panel_df), country)
        return

    logger.info(
        "Generating %d/%d missing biographies for %s (generate_events=%s)...",
        missing_bio, len(panel_df), country, generate_events,
    )

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        checkpoint_tmp = tmp.name

    def checkpoint_callback(current_panel: pd.DataFrame) -> None:
        """Push progress to the active panel blob periodically, so an ACI
        crash mid-run doesn't lose everything generated so far — only the
        local temp checkpoint file, which doesn't survive a container restart."""
        _upload_df(client, _active_panel_blob(country), current_panel)

    panel_df = populate_panel(
        panel_df,
        display_name,
        delay_seconds=0.01,
        checkpoint_path=checkpoint_tmp,
        generate_events=generate_events,
        date=panel_date if generate_events else None,
        articles_path=articles_path if generate_events else None,
        on_checkpoint=checkpoint_callback,
    )

    _upload_df(client, _active_panel_blob(country), panel_df)
    _upload_df(client, biography_snapshot_blob_name(country, year, week), panel_df)
    logger.info(
        "Biography-only panel generation complete: %s %d-W%02d "
        "(active panel + weekly snapshot updated in blob, no survey run).",
        country, year, week,
    )

def generate_vote_choice_backfill_onetime(
    country: str,
    target_year: int,
    target_week: int,
    source_year: int,
    source_week: int,
    force: bool = False,
    client: BlobServiceClient | None = None,
) -> None:
    """
    One-off vote-choice generation for a target ISO week, reusing a
    biography-only panel snapshot taken from a DIFFERENT week
    (source_year/source_week) instead of that target week's own
    pre-built backfill panel.

    Deliberately isolated from the normal backfill blobs/guards/checkpoints
    for target_year/target_week, so it can't collide with a "real" backfill
    run for that week later.
    """
    if client is None:
        client = get_blob_client()

    with open(COUNTRY_INFO_PATH) as f:
        country_info = json.load(f)

    info = country_info.get(country, {})
    question_id = info.get("question_id")
    if not question_id:
        raise ValueError(f"No question_id configured for '{country}'")

    onetime_guard = f"job-runs/vote-choice-backfill-onetime/{country}/{target_year}_{target_week:02d}.lock"
    if not force and _blob_exists(client, onetime_guard):
        logger.info(
            "One-time vote choice backfill already exists for %s %d-W%02d — skipping.",
            country, target_year, target_week,
        )
        return

    panel_date = isoweek_to_panel_date(target_year, target_week)

    source_blob = _backfill_panel_blob(country, source_year, source_week)
    panel_df = _download_df(client, source_blob)
    if panel_df is None:
        raise FileNotFoundError(f"No backfill panel found at {source_blob}.")
    if panel_df["biography"].isna().any():
        raise ValueError(
            f"Source panel {country} {source_year}-W{source_week:02d} has missing biographies."
        )
    panel_df = _download_df(client, source_blob)
    if panel_df is None:
        raise FileNotFoundError(f"No biography snapshot found at {source_blob}.")
    if panel_df["biography"].isna().any():
        raise ValueError(
            f"Source panel {country} {source_year}-W{source_week:02d} has missing biographies."
        )

    news_df = _download_df(client, _gdelt_blob(country, target_year, target_week))

    def checkpoint_callback(current_panel: pd.DataFrame) -> None:
        _upload_df(
            client,
            f"panel-state/{country}/backfill-onetime/checkpoints/"
            f"{target_year}_{target_week:02d}_{country}_panel_checkpoint.csv",
            current_panel,
        )

    panel_df, news_df = run_survey(
        question_id=question_id,
        panel_df=panel_df,
        panel_date=panel_date,
        news_df=news_df,
        attrition_rate=0.0,
        panels_dir=None,
        panel_name=None,
        on_checkpoint=checkpoint_callback,
    )

    _upload_df(client, _results_blob(country, target_year, target_week), panel_df)

def generate_vote_choice_backfill(
    country: str,
    year: int,
    week: int,
    force: bool = False,
    client: BlobServiceClient | None = None,
) -> None:
    """
    Run one survey wave for a pre-built, week-specific backfill panel.
    Safe to run in parallel across weeks: reads/writes only per-week blobs,
    never touches the shared active_panel.csv.
    Assumes biographies already populated (does NOT call populate_panel).
    """
    if client is None:
        client = get_blob_client()

    with open(COUNTRY_INFO_PATH) as f:
        country_info = json.load(f)

    info = country_info.get(country, {})
    question_id = info.get("question_id")
    if not question_id:
        raise ValueError(f"No question_id configured for '{country}'")

    if not force and _blob_exists(client, _vote_choice_guard_blob(country, year, week)):
        logger.info("Vote choice already exists for %s %d-W%02d — skipping.", country, year, week)
        return

    panel_date = isoweek_to_panel_date(year, week)

    # Load this week's pre-built panel (already has biographies + attrition applied)
    panel_df = _download_df(client, _backfill_panel_blob(country, year, week))
    if panel_df is None:
        raise FileNotFoundError(
            f"No backfill panel found at {_backfill_panel_blob(country, year, week)}. "
            f"Upload the split week file to blob before running."
        )
    if panel_df["biography"].isna().any():
        raise ValueError(
            f"Backfill panel for {country} {year}-W{week:02d} has missing biographies — "
            f"run the biography-only step first."
        )

    news_df = _download_df(client, _gdelt_blob(country, year, week))

    def checkpoint_callback(current_panel: pd.DataFrame) -> None:
        _upload_df(client, _backfill_checkpoint_blob(country, year, week), current_panel)

    panel_df, news_df = run_survey(
        question_id=question_id,
        panel_df=panel_df,
        panel_date=panel_date,
        news_df=news_df,
        attrition_rate=0.0,          # already applied when the week's panel was split for backfilling biography generation done all at once
        panels_dir=None,
        panel_name=None,
        on_checkpoint=checkpoint_callback,
    )

    _upload_df(client, _results_blob(country, year, week), panel_df)
    if news_df is not None:
        _upload_df(client, _gdelt_blob(country, year, week), news_df)

    blob = client.get_blob_client(container=CONTAINER_NAME, blob=_vote_choice_guard_blob(country, year, week))
    blob.upload_blob(b"done", overwrite=True)
    logger.info("Vote choice backfill complete: %s %d-W%02d", country, year, week)

def generate_panel_results(
    country: str,
    year: int,
    week: int,
    force: bool = False,
    client: BlobServiceClient | None = None,
) -> None:
    """
    Run one survey wave for `country` for ISO week `year`/`week`.

    Args:
        country: Full country name, e.g. 'sweden'.
        year:    ISO year, e.g. 2026.
        week:    ISO week number, e.g. 22.
        force:   If True, run even if a lock file already exists.
        client:  Optional pre-created BlobServiceClient.
    """
    if client is None:
        client = get_blob_client()

    with open(COUNTRY_INFO_PATH) as f:
        country_info = json.load(f)

    info = country_info.get(country, {})
    panel_filename = info.get("panel_filename")
    question_id    = info.get("question_id")

    if not panel_filename or not question_id:
        logger.info("Panel not configured for %s — skipping.", country)
        return

    if not force and already_ran_panel(client, country, year, week):
        logger.info("Panel results already exist for %s %d-W%02d — skipping.", country, year, week)
        return

    panel_date = isoweek_to_panel_date(year, week)
    panel_name = Path(panel_filename).stem   # e.g. 'sweden_panel_40'
    display_name = _COUNTRY_DISPLAY.get(country, country.title())

    logger.info("Generating panel results: country=%s, week=%d-%02d, panel_date=%s",
                country, year, week, panel_date)

    # ── 1. Load or initialise active panel ───────────────────────────────────
    panel_df = _download_df(client, _active_panel_blob(country))
    if panel_df is None:
        logger.info("No active panel in blob — initialising from %s", panel_filename)
        source = PANELS_DIR / panel_filename
        if not source.exists():
            raise FileNotFoundError(
                f"Base panel file not found: {source}\n"
                f"Copy {panel_filename} to country_data/panels/ in the backend repo."
            )
        panel_df = pd.read_csv(source)
        if "biography" not in panel_df.columns:
            panel_df["biography"] = pd.NA

    # ── 2. Generate missing biographies ──────────────────────────────────────
    missing_bio = panel_df["biography"].isna().sum()
    if missing_bio:
        logger.info("Generating %d missing biographies for %s...", missing_bio, country)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            checkpoint_tmp = tmp.name
        panel_df = populate_panel(
            panel_df,
            display_name,
            delay_seconds=0.01,
            checkpoint_path=checkpoint_tmp,
        )
        # Persist biographies immediately in case the survey crashes later
        _upload_df(client, _active_panel_blob(country), panel_df)

    # ── 3. Load GDELT cache (or let runner download) ──────────────────────────
    gdelt_blob_name = _gdelt_blob(country, year, week)
    news_df = _download_df(client, gdelt_blob_name)
    if news_df is not None:
        logger.info("Loaded GDELT cache from blob (%d rows).", len(news_df))
    else:
        logger.info("No GDELT cache found — runner will download from GDELT.")

    # ── 4. Run the survey ─────────────────────────────────────────────────────
    def checkpoint_callback(current_panel: pd.DataFrame) -> None:
        """Save panel to blob every CHECKPOINT_INTERVAL respondents."""
        _upload_df(client, _active_panel_blob(country), current_panel)

    panel_df, news_df = run_survey(
        question_id=question_id,
        panel_df=panel_df,
        panel_date=panel_date,
        news_df=news_df,
        panels_dir=PANELS_DIR,
        panel_name=panel_name,
        on_checkpoint=checkpoint_callback,
    )

    # ── 5. Upload results snapshot (this week's responses only) ──────────────
    results_blob_name = _results_blob(country, year, week)
    _upload_df(client, results_blob_name, panel_df)
    logger.info("Results snapshot uploaded to %s", results_blob_name)

    # ── 6. Update active panel state ─────────────────────────────────────────
    _upload_df(client, _active_panel_blob(country), panel_df)
    logger.info("Active panel state updated in blob.")

    # ── 7. Update GDELT cache ─────────────────────────────────────────────────
    if news_df is not None:
        _upload_df(client, gdelt_blob_name, news_df)
        logger.info("GDELT cache updated in blob.")

    # ── 8. Write lock ─────────────────────────────────────────────────────────
    mark_ran_panel(client, country, year, week)
    logger.info("Panel generation complete: %s %d-W%02d", country, year, week)