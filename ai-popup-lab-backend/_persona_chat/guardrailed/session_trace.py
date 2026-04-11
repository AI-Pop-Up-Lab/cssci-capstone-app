"""Session-level transcript writer for the guardrailed persona flow."""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime
from hashlib import sha1
from pathlib import Path
from uuid import uuid4

from _persona_chat.guardrailed.schemas import GuardrailSessionTrace


LOG_DIR = Path(__file__).resolve().parent / "log"
_TRACE_LOCK = threading.Lock()
_ACTIVE_SESSIONS: dict[str, "GuardrailSessionTrace"] = {}


def _utc_timestamp() -> str:
    """Return a compact UTC timestamp for filenames and headings."""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def _safe_slug(value: str) -> str:
    """Convert free text into a stable ASCII-friendly filename fragment."""
    lowered = value.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", lowered)
    return slug.strip("_") or "unknown"


def _persona_key(*, persona_country: str, persona_details: dict) -> str:
    """Create a stable persona key for the legacy persona bridge."""
    return "|".join(
        [
            _safe_slug(persona_country or "unknown"),
            str(persona_details.get("index", "0")),
            _safe_slug(str(persona_details.get("municipality", "unknown"))),
            _safe_slug(str(persona_details.get("gender", "unknown"))),
            _safe_slug(str(persona_details.get("age_group", "unknown"))),
        ]
    )


def _persona_label(*, persona_country: str, persona_details: dict) -> str:
    """Build a readable persona label for the transcript header."""
    country = persona_country or "Unknown country"
    municipality = persona_details.get("municipality") or "Unknown municipality"
    index = persona_details.get("index")
    return f"{country} | {municipality} | persona_{index}"


def _assistant_turn_count(chat_history: list[dict]) -> int:
    """Count prior assistant turns to derive the next turn number."""
    return sum(1 for message in chat_history if message.get("role") == "assistant")


def _new_session_trace(*, persona_key: str, persona_label: str, turn_index: int) -> GuardrailSessionTrace:
    """Create a fresh transcript target on disk."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    short_id = uuid4().hex[:8]
    filename = f"{timestamp}_{_safe_slug(persona_label)}_{short_id}.txt"
    log_path = LOG_DIR / filename
    session_id = f"{timestamp}_{short_id}"
    trace = GuardrailSessionTrace(
        session_id=session_id,
        persona_key=persona_key,
        persona_label=persona_label,
        log_path=str(log_path),
        turn_index=turn_index,
        is_new_session=True,
    )
    _initialize_session_file(trace)
    return trace


def get_or_create_session_trace(
    *,
    client_id: str,
    persona_country: str,
    persona_details: dict,
    chat_history: list[dict],
) -> GuardrailSessionTrace:
    """Return the active session trace for this client and persona chat."""
    persona_key = _persona_key(
        persona_country=persona_country,
        persona_details=persona_details,
    )
    persona_label = _persona_label(
        persona_country=persona_country,
        persona_details=persona_details,
    )
    turn_index = _assistant_turn_count(chat_history) + 1

    with _TRACE_LOCK:
        active_trace = _ACTIVE_SESSIONS.get(client_id)
        is_new_session = (
            active_trace is None
            or not chat_history
            or active_trace.persona_key != persona_key
        )

        if is_new_session:
            trace = _new_session_trace(
                persona_key=persona_key,
                persona_label=persona_label,
                turn_index=turn_index,
            )
        else:
            trace = GuardrailSessionTrace(
                session_id=active_trace.session_id,
                persona_key=active_trace.persona_key,
                persona_label=active_trace.persona_label,
                log_path=active_trace.log_path,
                turn_index=turn_index,
                is_new_session=False,
            )

        _ACTIVE_SESSIONS[client_id] = trace
        return trace


def _initialize_session_file(trace: GuardrailSessionTrace) -> None:
    """Write the top-level session header for a new trace file."""
    header = (
        _box("GUARDRAILED PERSONA CHAT SESSION", "=")
        + f"Session ID : {trace.session_id}\n"
        + f"Persona    : {trace.persona_label}\n"
        + f"Created    : {_utc_timestamp()}\n"
        + f"Log file   : {trace.log_path}\n\n"
    )
    Path(trace.log_path).write_text(header, encoding="utf-8")


def _box(title: str, border_char: str = "=") -> str:
    """Render a readable section header block."""
    line = border_char * 78
    return f"{line}\n{title}\n{line}\n"


def _format_json(value) -> str:
    """Pretty-print a Python value in a stable readable form."""
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)


def _stringify_content(content) -> str:
    """Convert arbitrary content into a readable transcript string."""
    if isinstance(content, str):
        return content.strip() + "\n"
    return _format_json(content) + "\n"


def _append_text(trace: GuardrailSessionTrace, text: str) -> None:
    """Append raw text to the session transcript."""
    with _TRACE_LOCK:
        with open(trace.log_path, "a", encoding="utf-8") as handle:
            handle.write(text)


def append_named_block(
    *,
    trace: GuardrailSessionTrace,
    title: str,
    content,
    step_label: str | None = None,
) -> None:
    """Append a labeled content block to the session transcript."""
    heading = title if step_label is None else f"{step_label} | {title}"
    text = (
        _box(heading, "-")
        + _stringify_content(content)
        + "\n"
    )
    _append_text(trace, text)


def append_turn_opening(
    *,
    trace: GuardrailSessionTrace,
    user_message: str,
    chat_history: list[dict],
    biography: str,
    stylometric_profile: dict,
) -> None:
    """Append the top of a turn, including the persona grounding blocks."""
    history_digest = sha1(
        json.dumps(chat_history, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:10]

    text = (
        _box(f"TURN {trace.turn_index:02d}", "#")
        + f"Started      : {_utc_timestamp()}\n"
        + f"Session ID   : {trace.session_id}\n"
        + f"Persona      : {trace.persona_label}\n"
        + f"History size : {len(chat_history)} messages\n"
        + f"History hash : {history_digest}\n\n"
    )
    _append_text(trace, text)
    append_named_block(
        trace=trace,
        title="Persona Biography",
        content=biography,
    )
    append_named_block(
        trace=trace,
        title="Stylometric Profile",
        content=stylometric_profile,
    )
    append_named_block(
        trace=trace,
        title="Current User Message",
        content=user_message,
    )
    append_named_block(
        trace=trace,
        title="Prior Chat History",
        content=chat_history if chat_history else "None",
    )


def append_kv_block(
    *,
    trace: GuardrailSessionTrace,
    title: str,
    items: list[tuple[str, object]],
    step_label: str | None = None,
) -> None:
    """Append a simple key/value summary block."""
    width = max((len(key) for key, _ in items), default=0)
    lines = [f"{key.ljust(width)} : {value}" for key, value in items]
    append_named_block(
        trace=trace,
        title=title,
        content="\n".join(lines),
        step_label=step_label,
    )


def append_turn_closing(*, trace: GuardrailSessionTrace, final_response: str) -> None:
    """Append a closing block for the current turn."""
    append_named_block(
        trace=trace,
        title="Final Response",
        content=final_response,
        step_label="STEP 3",
    )
    _append_text(
        trace,
        _box(f"END TURN {trace.turn_index:02d}", "#") + "\n",
    )
