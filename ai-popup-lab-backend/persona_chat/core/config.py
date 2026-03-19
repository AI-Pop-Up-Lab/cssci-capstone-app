from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# ============================================================
# Project paths
# ============================================================
# /persona_chat/core/config.py
BASE_DIR = Path(__file__).resolve().parents[2]
PERSONA_CHAT_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """
    Central settings object.

    Sources (in order):
    - Defaults in this file
    - Values from .env (if present)
    - Environment variables

    Notes:
    - `extra="ignore"` allows .env to contain more keys than we define here.
    """

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        extra="ignore",
    )

    # ============================================================
    # App
    # ============================================================
    APP_ENV: str = "dev"

    # ============================================================
    # Database configuration
    # ============================================================
    # Legacy single-DB setting. Keep this during transition.
    # Historically your code used DATABASE_URL everywhere.
    # After refactor:
    #   - persona/static data -> PERSONA_DB_URL
    #   - chat/runtime data   -> CHAT_DB_URL
    DATABASE_URL: str = f"sqlite:///{(PERSONA_CHAT_DIR / 'data' / 'app.db').as_posix()}"

    # Persona DB: static profile + question bank + survey answers
    PERSONA_DB_URL: str = f"sqlite:///{(PERSONA_CHAT_DIR / 'data' / 'persona.db').as_posix()}"

    # Chat DB: sessions + messages + traces
    CHAT_DB_URL: str = f"sqlite:///{(PERSONA_CHAT_DIR / 'data' / 'chat.db').as_posix()}"

    # ============================================================
    # LLM (OpenAI-compatible providers: Groq, OpenRouter, etc.)
    # ============================================================
    LLM_PROVIDER: str = "openai"

    # Keep secrets OUT of code; set in .env instead
    OPENAI_API_KEY: str = ""

    # Groq defaults (can be overridden by .env)
    OPENAI_MODEL: str = "llama3-70b-8192"
    OPENAI_BASE_URL: str = "https://api.groq.com/openai/v1"

    # ============================================================
    # Topic model runtime (BERTopic)
    # ============================================================
    # Folder that contains per-snapshot scope models:
    #   data/topic_models/<snapshot_id>/...
    TOPIC_MODEL_DIR: str = str(PERSONA_CHAT_DIR / "data" / "topic_models")


settings = Settings()
