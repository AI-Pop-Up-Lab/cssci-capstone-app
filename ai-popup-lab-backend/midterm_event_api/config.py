"""
Settings for the midterm event chat.

Everything is read from environment variables: the `.env` file when running locally,
and the App Service "Environment variables" page on Azure. Settings are re-read on every
request, so tests can change them with monkeypatch. (On Azure, changing a setting restarts
the app anyway.)

See the "Configuration" table in README.md for what each variable does.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_PERSONAS_DIR = PACKAGE_DIR / "personas"
DEFAULT_BASE_PROMPT_PATH = PACKAGE_DIR / "prompts" / "base_system.md"

REPLY_MODES = ("buffered", "stream")


@dataclass(frozen=True)
class Settings:
    # kill switch: set MIDTERM_CHAT_ENABLED=false to pause the chat without a code change
    chat_enabled: bool
    # "buffered" waits for the whole reply so it can be moderated before anyone sees it,
    # "stream" sends it word by word (faster to appear, but replies can't be checked first)
    reply_mode: str
    personas_dir: Path
    base_prompt_path: Path
    max_message_chars: int
    max_history_messages: int
    daily_message_limit: int
    # None means the parameter is left out of the model request
    temperature: float | None
    max_reply_tokens: int | None
    llm_timeout_seconds: float
    # same Azure OpenAI variables the old persona chat uses
    azure_api_key: str | None
    azure_base_url: str | None
    model: str | None


def _env_str(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return value.strip()


def _env_bool(name: str, default: bool) -> bool:
    value = _env_str(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    value = _env_str(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("%s=%r is not a whole number, using %s", name, value, default)
        return default


def _env_optional_number(name: str, default, cast):
    # set the variable to "none" to leave the parameter out of the model request,
    # for models that reject it (e.g. reasoning models reject temperature)
    raw = os.getenv(name)
    if raw is None:
        return default
    if raw.strip().lower() in ("", "none", "off"):
        return None
    try:
        return cast(raw)
    except ValueError:
        logger.warning("%s=%r is not a number, using %s", name, raw, default)
        return default


def get_settings() -> Settings:
    reply_mode = (_env_str("MIDTERM_REPLY_MODE") or "buffered").lower()
    if reply_mode not in REPLY_MODES:
        logger.warning("MIDTERM_REPLY_MODE=%r is not one of %s, using 'buffered'", reply_mode, REPLY_MODES)
        reply_mode = "buffered"

    personas_dir = _env_str("MIDTERM_PERSONAS_DIR")
    base_prompt_path = _env_str("MIDTERM_BASE_PROMPT_PATH")

    return Settings(
        chat_enabled=_env_bool("MIDTERM_CHAT_ENABLED", True),
        reply_mode=reply_mode,
        personas_dir=Path(personas_dir) if personas_dir else DEFAULT_PERSONAS_DIR,
        base_prompt_path=Path(base_prompt_path) if base_prompt_path else DEFAULT_BASE_PROMPT_PATH,
        max_message_chars=_env_int("MIDTERM_MAX_MESSAGE_CHARS", 1000),
        max_history_messages=_env_int("MIDTERM_MAX_HISTORY_MESSAGES", 20),
        # FLAG: effectively no limit, on purpose (in-person event, see limits.py)
        daily_message_limit=_env_int("MIDTERM_DAILY_MESSAGE_LIMIT", 10000),
        temperature=_env_optional_number("MIDTERM_TEMPERATURE", 0.7, float),
        max_reply_tokens=_env_optional_number("MIDTERM_MAX_REPLY_TOKENS", 300, int),
        llm_timeout_seconds=float(_env_int("MIDTERM_LLM_TIMEOUT_SECONDS", 30)),
        azure_api_key=_env_str("AZURE_OPENAI_API_KEY"),
        azure_base_url=_env_str("AZURE_OPENAI_BASE_URL"),
        # MIDTERM_MODEL lets the event use a different deployment than the old chat
        model=_env_str("MIDTERM_MODEL") or _env_str("AZURE_OPENAI_MODEL"),
    )
