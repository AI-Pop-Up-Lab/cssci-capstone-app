"""Lexical prompt-injection detection for the guardrailed pipeline."""

from _persona_chat.guardrailed.schemas import LexicalSignal


# =============================================================================
# Detection Terms
# =============================================================================

PROMPT_INJECTION_TERMS = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "reveal your system prompt",
    "show hidden instructions",
    "print your prompt",
    "developer message",
    "system prompt",
    "hidden instructions",
    "secret key",
    "api key",
    "bypass safety",
    "disable guardrails",
)


# =============================================================================
# Public Detection Entry Point
# =============================================================================

def detect_prompt_injection(user_message: str) -> LexicalSignal:
    """Detect common prompt-injection phrases using a simple lexical scan."""
    normalized_message = user_message.lower()
    matched_terms = [
        term for term in PROMPT_INJECTION_TERMS if term in normalized_message
    ]

    return LexicalSignal(
        triggered=bool(matched_terms),
        matched_terms=matched_terms,
        risk_level="high" if matched_terms else "low",
    )
