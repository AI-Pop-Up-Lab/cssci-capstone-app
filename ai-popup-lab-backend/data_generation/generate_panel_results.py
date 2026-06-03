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
from .store_data import get_blob_client, CONTAINER_NAME

logger = logging.getLogger(__name__)

BASE_DIR   = Path(__file__).resolve().parent.parent
PANELS_DIR = BASE_DIR / "country_data" / "panels"
COUNTRY_INFO_PATH = BASE_DIR / "country_data" / "country_data_info.json"

_COUNTRY_DISPLAY = {
    "sweden":      "Sweden",
    "netherlands": "Netherlands",
    "denmark":     "Denmark",
}

# ── Blob path helpers ─────────────────────────────────────────────────────────

def _active_panel_blob(country: str) -> str:
    return f"panel-state/{country}/active_panel.csv"

def _results_blob(country: str, year: int, week: int) -> str:
    return f"panel-results/{country}/{year}_{week:02d}_{country}_panel_results.csv"

def _gdelt_blob(country: str, year: int, week: int) -> str:
    return f"gdelt-cache/{country}/{year}_{week:02d}_gdelt.csv"

def _panel_guard_blob(country: str, year: int, week: int) -> str:
    return f"job-runs/panel/{country}/{year}_{week:02d}.lock"

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