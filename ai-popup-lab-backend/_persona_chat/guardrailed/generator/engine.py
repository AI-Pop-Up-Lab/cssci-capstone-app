"""Final response generation for the guardrailed pipeline."""

from _persona_chat.guardrailed.prompts import (
    GUARDRAILED_RESPONSE_SYS_PROMPT,
    REDIRECT_MESSAGE,
    REFUSAL_MESSAGE,
)
from _persona_chat.guardrailed.schemas import GuardrailInput, GuardrailSignals, PolicyDecision
from _persona_chat.guardrailed.session_trace import append_kv_block, append_named_block, append_turn_closing
from _persona_chat.logging import get_logger
from _persona_chat.utils import (
    build_chat_messages,
    create_system_prompt,
    stream_chat_response,
)


log = get_logger(__name__)


VERY_LOW_RELEVANCE_THRESHOLD = 0.35
VERY_LOW_EPISTEMIC_THRESHOLD = 0.35
LOW_RELEVANCE_THRESHOLD = 0.5
LOW_EPISTEMIC_THRESHOLD = 0.5


# =============================================================================
# Internal Helpers
# =============================================================================

def _build_guided_user_message(*, user_message: str, guidance: str, policy: PolicyDecision) -> str:
    """Attach policy guidance for the answering model in a simple, explicit form."""
    return (
        f"Guardrail guidance: {guidance}\n"
        f"Style guidance:\n"
        f"- Hedging style: {policy.hedging_style}\n"
        f"- Confidence style: {policy.confidence_style}\n"
        f"- Register: {policy.register_style}\n"
        f"- Sentence style: {policy.sentence_style}\n"
        f"- Abstraction level: {policy.abstraction_level}\n"
        f"- Vocabulary level: {policy.vocabulary_level}\n"
        f"- Explanation style: {policy.explanation_style}\n"
        f"- Tone style: {policy.tone_style}\n"
        f"- Emotional style: {policy.emotional_style}\n\n"
        f"User message: {user_message}"
    )


def _build_stylometric_execution_note(*, stylometric_profile: dict, policy: PolicyDecision) -> str:
    """Convert baseline stylometry plus judge modulation into practical execution notes."""
    hedging_style = policy.hedging_style or stylometric_profile.get("hedging_style", "medium")
    confidence_style = policy.confidence_style or stylometric_profile.get("confidence_style", "balanced")
    warmth_style = stylometric_profile.get("warmth_style", "warm")
    reasoning_style = stylometric_profile.get("reasoning_style", "blended")

    hedging_note = {
        "low": "Speak fairly directly, without constantly qualifying every point.",
        "medium": "Use a modest amount of softening and uncertainty language when appropriate.",
        "high": "Sound cautious and noticeably hedged, especially outside direct lived experience.",
    }.get(hedging_style, "Use a modest amount of softening when appropriate.")

    confidence_note = {
        "tentative": "Sound careful and tentative rather than highly certain.",
        "balanced": "Sound steady and believable, confident but not pushy or overconfident.",
        "assured": "Sound assured and clear, while still staying inside the persona's real knowledge.",
    }.get(confidence_style, "Sound steady and believable.")

    warmth_note = {
        "reserved": "Keep the tone more restrained than chatty.",
        "warm": "Keep the tone warm, approachable, and human.",
        "expressive": "Let the tone be more openly enthusiastic and expressive when it fits.",
    }.get(warmth_style, "Keep the tone warm and human.")

    reasoning_note = {
        "practical": "Explain things through everyday practical reasoning and concrete lived examples.",
        "reflective": "Let the answer sound reflective and personally considered.",
        "analytical": "Organize the answer clearly and logically, but avoid sounding academic.",
        "blended": "Mix practical examples with a little reflection when it feels natural.",
    }.get(reasoning_style, "Use practical, grounded reasoning.")

    return (
        "Stylometric execution notes:\n"
        f"- Baseline hedging from profile: {stylometric_profile.get('hedging_style', 'medium')}\n"
        f"- Baseline confidence from profile: {stylometric_profile.get('confidence_style', 'balanced')}\n"
        f"- Judge-selected hedging for this topic: {hedging_style}\n"
        f"- Judge-selected confidence for this topic: {confidence_style}\n"
        f"- {hedging_note}\n"
        f"- {confidence_note}\n"
        f"- {warmth_note}\n"
        f"- {reasoning_note}\n"
        "- Keep the style subtle and believable rather than exaggerated."
    )


def _should_force_brief_limited_answer(policy: PolicyDecision) -> bool:
    """Return True when the policy indicates the topic is too far outside the profile for detail."""
    return (
        policy.action == "limited_answer"
        and (
            policy.relevance_score <= VERY_LOW_RELEVANCE_THRESHOLD
            or policy.epistemic_score <= VERY_LOW_EPISTEMIC_THRESHOLD
            or policy.knowledge_level == "very_limited"
        )
    )


def _user_requested_detail(user_message: str) -> bool:
    """Return True when the user explicitly asks for depth or detail."""
    normalized = user_message.lower()
    detail_markers = (
        "in detail",
        "detailed",
        "explain",
        "deep dive",
        "more detail",
        "tell me more",
        "how does",
        "what is",
        "who is",
    )
    return any(marker in normalized for marker in detail_markers)


def _should_force_basic_limited_answer(*, policy: PolicyDecision, user_message: str) -> bool:
    """Return True when the persona should stay basic even if a hard two-sentence cap is unnecessary."""
    return (
        policy.action == "limited_answer"
        and _user_requested_detail(user_message)
        and (
            policy.relevance_score <= LOW_RELEVANCE_THRESHOLD
            or policy.epistemic_score <= LOW_EPISTEMIC_THRESHOLD
            or policy.knowledge_level in {"limited", "very_limited"}
        )
    )


def _should_force_very_basic_nonexpert_answer(*, policy: PolicyDecision, user_message: str) -> bool:
    """Return True when the persona should not provide detailed explanation on this topic at all."""
    return (
        not policy.detail_allowed
        and (
            _user_requested_detail(user_message)
            or policy.relevance_score <= LOW_RELEVANCE_THRESHOLD
            or policy.epistemic_score <= LOW_EPISTEMIC_THRESHOLD
            or policy.knowledge_level in {"limited", "very_limited"}
            or policy.expertise_basis == "none"
        )
    )


def _tighten_guidance_for_low_fit(policy: PolicyDecision) -> str:
    """Add deterministic brevity constraints for low-fit topics."""
    return (
        f"{policy.response_guidance}\n"
        "Hard limit: keep the reply to at most 2 short sentences.\n"
        "If the topic is outside the persona's real experience, give only a basic plain-language description if needed.\n"
        "State clearly when you do not know the topic personally or in detail.\n"
        "Do not provide extended explanations, examples, lore, or background detail.\n"
        "Prefer brevity over completeness."
    )


def _tighten_guidance_for_basic_fit(policy: PolicyDecision) -> str:
    """Add deterministic limits for requests that should stay basic and modest."""
    return (
        f"{policy.response_guidance}\n"
        "Keep the reply short and basic.\n"
        "Use at most 3 short paragraphs or 3 short sentences.\n"
        "Do not go into technical detail, backstory, advanced explanation, or extended examples.\n"
        "It is good to admit you only know the broad outline and not the details.\n"
        "If needed, answer at a plain layperson level only."
    )


def _tighten_guidance_for_nonexpert_detail(policy: PolicyDecision) -> str:
    """Add a hard ceiling when the persona lacks real grounds for detail."""
    return (
        f"{policy.response_guidance}\n"
        "Hard epistemic ceiling: do not provide a detailed explanation on this topic.\n"
        "Answer only at a very basic layperson level.\n"
        "Use at most 2 short sentences.\n"
        "Avoid technical terms, named theories, mechanisms, jargon, sub-concepts, or advanced examples unless absolutely unavoidable.\n"
        "State clearly that you do not know the topic in depth.\n"
        "Do not let the user's request for detail override this limit."
    )


def _log_and_yield_text(*, trace, action: str, text: str):
    """Log and yield a static response."""
    log.info("")
    log.info("Guardrail Response")
    log.info("  Mode: %s", action)
    log.info("  Response: %s", text)
    append_kv_block(
        trace=trace,
        title="Static Policy Response",
        step_label="STEP 3",
        items=[
            ("Mode", action),
            ("Response", text),
        ],
    )
    append_turn_closing(trace=trace, final_response=text)
    yield text


def _stream_with_logging(*, trace, response_iterator, action: str, user_message: str, guidance: str):
    """Log the final streamed response after yielding it to the client."""
    chunks: list[str] = []

    for chunk in response_iterator:
        chunks.append(chunk)
        yield chunk

    final_response = "".join(chunks)
    log.info("")
    log.info("Guardrail Response")
    log.info("  Mode: %s", action)
    log.info("  Guidance used: %s", guidance)
    log.info("  User message: %s", user_message)
    log.info("  Final response: %s", final_response)
    append_kv_block(
        trace=trace,
        title="Generated Response Summary",
        step_label="STEP 3",
        items=[
            ("Mode", action),
            ("Guidance used", guidance),
            ("User message", user_message),
        ],
    )
    append_turn_closing(trace=trace, final_response=final_response)


# =============================================================================
# Public Generation Entry Point
# =============================================================================

def generate_policy_response(
    *,
    guardrail_input: GuardrailInput,
    signals: GuardrailSignals,
    policy: PolicyDecision,
):
    """Generate the final response stream according to the chosen policy."""
    if policy.action == "refuse":
        return _log_and_yield_text(
            trace=guardrail_input.session_trace,
            action="refuse",
            text=REFUSAL_MESSAGE,
        )

    if policy.action == "redirect":
        return _log_and_yield_text(
            trace=guardrail_input.session_trace,
            action="redirect",
            text=REDIRECT_MESSAGE,
        )

    effective_guidance = policy.response_guidance
    if _should_force_very_basic_nonexpert_answer(
        policy=policy,
        user_message=guardrail_input.user_message,
    ):
        effective_guidance = _tighten_guidance_for_nonexpert_detail(policy)
    elif _should_force_brief_limited_answer(policy):
        effective_guidance = _tighten_guidance_for_low_fit(policy)
    elif _should_force_basic_limited_answer(
        policy=policy,
        user_message=guardrail_input.user_message,
    ):
        effective_guidance = _tighten_guidance_for_basic_fit(policy)

    system_prompt = create_system_prompt(
        GUARDRAILED_RESPONSE_SYS_PROMPT,
        guardrail_input.persona_biography,
    )
    style_execution_note = _build_stylometric_execution_note(
        stylometric_profile=guardrail_input.stylometric_profile,
        policy=policy,
    )
    guided_user_message = _build_guided_user_message(
        user_message=guardrail_input.user_message,
        guidance=f"{effective_guidance}\n{style_execution_note}",
        policy=policy,
    )
    messages = build_chat_messages(
        system_prompt=system_prompt,
        user_message=guided_user_message,
        chat_history=guardrail_input.chat_history,
    )

    log.info("")
    log.info("Guardrail Response Preparation")
    log.info("  Mode: %s", policy.action)
    log.info("  Guidance: %s", effective_guidance)
    log.info("  Lexical triggered: %s", signals.lexical.triggered)
    log.info("  Lexical score: %s", policy.lexical_score)
    log.info("  Relevance score: %s", policy.relevance_score)
    log.info("  Epistemic score: %s", policy.epistemic_score)
    log.info("  Knowledge level: %s", policy.knowledge_level)
    log.info("  Detail allowed: %s", policy.detail_allowed)
    log.info("  Expertise basis: %s", policy.expertise_basis)
    log.info("  Hedging style: %s", policy.hedging_style)
    log.info("  Confidence style: %s", policy.confidence_style)
    log.info("  Language level: %s", policy.language_level)
    log.info("  Register style: %s", policy.register_style)
    log.info("  Sentence style: %s", policy.sentence_style)
    log.info("  Abstraction level: %s", policy.abstraction_level)
    log.info("  Vocabulary level: %s", policy.vocabulary_level)
    log.info("  Explanation style: %s", policy.explanation_style)
    log.info("  Tone style: %s", policy.tone_style)
    log.info("  Emotional style: %s", policy.emotional_style)
    append_kv_block(
        trace=guardrail_input.session_trace,
        title="Response Preparation Summary",
        step_label="STEP 3",
        items=[
            ("Mode", policy.action),
            ("Guidance", effective_guidance),
            ("Lexical triggered", signals.lexical.triggered),
            ("Lexical score", policy.lexical_score),
            ("Relevance score", policy.relevance_score),
            ("Epistemic score", policy.epistemic_score),
            ("Knowledge level", policy.knowledge_level),
            ("Detail allowed", policy.detail_allowed),
            ("Expertise basis", policy.expertise_basis),
            ("Hedging style", policy.hedging_style),
            ("Confidence style", policy.confidence_style),
            ("Language level", policy.language_level),
            ("Register style", policy.register_style),
            ("Sentence style", policy.sentence_style),
            ("Abstraction level", policy.abstraction_level),
            ("Vocabulary level", policy.vocabulary_level),
            ("Explanation style", policy.explanation_style),
            ("Tone style", policy.tone_style),
            ("Emotional style", policy.emotional_style),
            (
                "Hedging style",
                policy.hedging_style or guardrail_input.stylometric_profile.get("hedging_style", "medium"),
            ),
            (
                "Confidence style",
                policy.confidence_style or guardrail_input.stylometric_profile.get("confidence_style", "balanced"),
            ),
            (
                "Warmth style",
                guardrail_input.stylometric_profile.get("warmth_style", "warm"),
            ),
            (
                "Reasoning style",
                guardrail_input.stylometric_profile.get("reasoning_style", "blended"),
            ),
        ],
    )
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Generator System Prompt",
        content=system_prompt,
        step_label="STEP 3",
    )
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Generator Style Execution Note",
        content=style_execution_note,
        step_label="STEP 3",
    )
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Generator Guided User Prompt",
        content=guided_user_message,
        step_label="STEP 3",
    )
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Generator Messages Payload",
        content=messages,
        step_label="STEP 3",
    )
    response_iterator = stream_chat_response(messages=messages, temperature=0.45)
    return _stream_with_logging(
        trace=guardrail_input.session_trace,
        response_iterator=response_iterator,
        action=policy.action,
        user_message=guardrail_input.user_message,
        guidance=effective_guidance,
    )
