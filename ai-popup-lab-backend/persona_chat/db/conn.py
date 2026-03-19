from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager

from app.core.config import settings

# ============================================================
# Helpers
# ============================================================


def _sqlite_path_from_url(db_url: str) -> str:
    """
    Convert a sqlite URL to a filesystem path.

    Supported:
      - sqlite:///./data/app.db  -> ./data/app.db
      - sqlite:////abs/path.db   -> /abs/path.db
      - sqlite:///Users/me/x.db  -> /Users/me/x.db

    We only support sqlite because this project is currently SQLite-first.
    """
    if not db_url.startswith("sqlite:///"):
        raise ValueError(f"Only sqlite:/// URLs are supported (got: {db_url})")

    # Strip the sqlite:/// prefix
    return db_url.replace("sqlite:///", "", 1)


def _ensure_parent_dir(sqlite_path: str) -> None:
    """Ensure parent directory exists for the sqlite file."""
    db_dir = os.path.dirname(sqlite_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)


def _connect(sqlite_path: str) -> sqlite3.Connection:
    """
    Open a sqlite connection with Row factory enabled.

    Row factory gives dict-like access:
      row["persona_id"]
    """
    _ensure_parent_dir(sqlite_path)
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# DB paths (resolved from settings)
# ============================================================

PERSONA_SQLITE_PATH = _sqlite_path_from_url(settings.PERSONA_DB_URL)
CHAT_SQLITE_PATH = _sqlite_path_from_url(settings.CHAT_DB_URL)

# Legacy path (kept for transition/debug)
LEGACY_SQLITE_PATH = _sqlite_path_from_url(settings.DATABASE_URL)

# ============================================================
# Public context managers
# ============================================================


@contextmanager
def get_persona_conn():
    """
    Persona DB connection.

    Use for tables:
      - personas
      - question_bank
      - survey_answers
    """
    conn = _connect(PERSONA_SQLITE_PATH)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_chat_conn():
    """
    Chat DB connection.

    Use for tables:
      - chat_sessions
      - chat_messages
      - (anything runtime / trace / logs)
    """
    conn = _connect(CHAT_SQLITE_PATH)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_conn():
    """
    Backward-compatible default connection.

    IMPORTANT:
    During the refactor, defaulting to CHAT DB is safer, because:
      - chat tables are ephemeral / runtime
      - persona DB should remain clean and curated

    Migration plan:
      - Persona reads -> get_persona_conn()
      - Chat reads/writes -> get_chat_conn()
      - Eventually remove this function once everything is explicit.
    """
    with get_chat_conn() as conn:
        yield conn