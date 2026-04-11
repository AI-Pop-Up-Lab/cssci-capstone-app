"""Top-level orchestration helpers for the legacy persona chat flow."""

from _persona_chat.config import USE_LIGHTWEIGHT_RESPONSE
from _persona_chat.biography.store import get_or_create_biography
from _persona_chat.guardrailed.engine import generate_response as generate_guardrailed_response
from _persona_chat.guardrailed.session_trace import get_or_create_session_trace
from _persona_chat.guardrailed.stylometry.store import get_or_create_stylometric_profile
from _persona_chat.lightweight.engine import generate_response as generate_lightweight_response


# =============================================================================
# Command Configuration
# =============================================================================

CHAT_COMMANDS = {"//biography"}


# =============================================================================
# Biography and Command Handling
# =============================================================================

def resolve_biography(*, persona_details: dict, persona_country: str) -> str:
    """Resolve the biography needed for a chat request."""
    return get_or_create_biography(
        persona_details=persona_details,
        persona_country=persona_country,
    )


def handle_chat_command(*, message: str, biography: str) -> str | None:
    """Handle any direct chat commands that bypass normal model generation."""
    if message not in CHAT_COMMANDS:
        return None

    if message == "//biography":
        return biography

    return None


# =============================================================================
# Response Mode Dispatch
# =============================================================================

def generate_chat_response(
    *,
    persona_biography: str,
    user_message: str,
    chat_history: list,
    persona_details: dict,
    persona_country: str,
    client_id: str,
):
    """Dispatch chat generation to the configured response mode."""
    if USE_LIGHTWEIGHT_RESPONSE:
        return generate_lightweight_response(
            persona_biography=persona_biography,
            user_message=user_message,
            chat_history=chat_history,
        )

    stylometric_profile = get_or_create_stylometric_profile(
        persona_details=persona_details,
        persona_country=persona_country,
        persona_biography=persona_biography,
    )
    session_trace = get_or_create_session_trace(
        client_id=client_id,
        persona_country=persona_country,
        persona_details=persona_details,
        chat_history=chat_history,
    )

    return generate_guardrailed_response(
        persona_biography=persona_biography,
        user_message=user_message,
        chat_history=chat_history,
        stylometric_profile=stylometric_profile,
        session_trace=session_trace,
    )
