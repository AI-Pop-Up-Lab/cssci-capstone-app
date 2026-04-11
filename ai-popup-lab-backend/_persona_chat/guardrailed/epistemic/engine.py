"""Epistemic sub-prompt preparation for the guardrailed pipeline."""

from _persona_chat.guardrailed.schemas import EpistemicSignal


# =============================================================================
# Prompt Builder
# =============================================================================

EPISTEMIC_JUDGE_SUBPROMPT = """
Epistemic evaluation:
- Use the persona biography to infer the persona's likely education level, work background, lived experience, confidence, tone, emotional register, and reasoning depth.
- Determine how much this persona should realistically know about the user's topic.
- Produce an epistemic score between 0 and 1.
- A score near 0 means the persona should know very little about this topic and should answer cautiously, modestly, or avoid the topic.
- A score near 1 means the persona is well-positioned to talk about this topic from within their own background.
- Also decide:
  - the appropriate knowledge level
  - the appropriate language level
  - the appropriate tone of voice
  - the appropriate emotional style
- These style decisions should stay grounded in the persona biography rather than generic assistant behavior.
""".strip()


# =============================================================================
# Public Evaluation Entry Point
# =============================================================================

def evaluate_epistemic_boundaries(*, user_message: str, persona_biography: str) -> EpistemicSignal:
    """Build the epistemic instructions that will be injected into the judge prompt."""
    judge_prompt = (
        f"{EPISTEMIC_JUDGE_SUBPROMPT}\n\n"
        "Context for epistemic evaluation:\n"
        f"- User message: {user_message}\n"
        "- Persona biography: provided separately in the judge prompt."
    )

    return EpistemicSignal(
        summary="Epistemic evaluation is delegated to the judge model through a dedicated sub-prompt.",
        judge_prompt=judge_prompt,
    )
