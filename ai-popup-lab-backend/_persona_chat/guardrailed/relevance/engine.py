"""Relevance sub-prompt preparation for the guardrailed pipeline."""

from _persona_chat.guardrailed.schemas import RelevanceSignal


# =============================================================================
# Prompt Builder
# =============================================================================

RELEVANCE_JUDGE_SUBPROMPT = """
Relevance evaluation:
- Compare the user's message to the persona biography and profile context.
- Determine how close or distant the requested topic is from what this persona would realistically want to talk about or be able to talk about.
- Produce a relevance score between 0 and 1.
- A score near 0 means the topic is far from the persona profile and should be steered, redirected, or rejected more strongly.
- A score near 1 means the topic is strongly grounded in the persona profile and can be answered more directly.
- Consider not only literal overlap, but also whether the persona would realistically relate to the topic, care about the topic, or see it as part of their conversational scope.
""".strip()


# =============================================================================
# Public Evaluation Entry Point
# =============================================================================

def evaluate_relevance(*, user_message: str, persona_biography: str) -> RelevanceSignal:
    """Build the relevance instructions that will be injected into the judge prompt."""
    judge_prompt = (
        f"{RELEVANCE_JUDGE_SUBPROMPT}\n\n"
        "Context for relevance evaluation:\n"
        f"- User message: {user_message}\n"
        "- Persona biography: provided separately in the judge prompt."
    )

    return RelevanceSignal(
        summary="Relevance is delegated to the judge model through a dedicated sub-prompt.",
        judge_prompt=judge_prompt,
    )
