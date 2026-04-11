"""LLM-based policy selection for the guardrailed response pipeline."""

import json

from _persona_chat.guardrailed.prompts import GUARDRAILED_JUDGE_SYS_PROMPT
from _persona_chat.guardrailed.schemas import GuardrailInput, GuardrailSignals, PolicyDecision
from _persona_chat.guardrailed.session_trace import append_kv_block, append_named_block
from _persona_chat.logging import get_logger
from _persona_chat.utils import build_chat_messages, run_chat_completion


log = get_logger(__name__)


# =============================================================================
# Internal Helpers
# =============================================================================

def _build_judge_user_message(*, guardrail_input: GuardrailInput, signals: GuardrailSignals) -> str:
    """Build the structured judge prompt input."""
    lexical_terms = ", ".join(signals.lexical.matched_terms) if signals.lexical.matched_terms else "None"
    if guardrail_input.chat_history:
        chat_history = "\n".join(
            f"- {message.get('role', 'unknown')}: {message.get('content', '')}"
            for message in guardrail_input.chat_history
        )
    else:
        chat_history = "None"

    return (
        "Persona biography:\n"
        f"{guardrail_input.persona_biography}\n\n"
        "Prior conversation:\n"
        f"{chat_history}\n\n"
        "User message:\n"
        f"{guardrail_input.user_message}\n\n"
        "Lexical signal:\n"
        f"- Triggered: {signals.lexical.triggered}\n"
        f"- Risk level: {signals.lexical.risk_level}\n"
        f"- Matched terms: {lexical_terms}\n\n"
        f"{signals.relevance.judge_prompt}\n\n"
        f"{signals.epistemic.judge_prompt}\n\n"
        f"{signals.stylometric.judge_prompt}\n\n"
        "Expertise-depth rule:\n"
        "- User requests for detail do not by themselves justify a detailed answer.\n"
        "- Set detail_allowed to true only when the biography shows strong grounds for depth on this topic.\n"
        "- Strong grounds means at least one of: relevant education, relevant job exposure, substantial lived experience, or a clearly stated domain hobby/interest.\n"
        "- If the topic is far from the persona's interests, work, or educational direction, set detail_allowed to false and expertise_basis to none.\n"
        "- When detail_allowed is false, the persona should stay at a very basic layperson level even if the user asks for a super detailed explanation.\n\n"
        "Dynamic style modulation rule:\n"
        "- Start from the stylometric profile as the persona's baseline speaking style.\n"
        "- If the topic strongly resonates with the persona's work, hobbies, study, or lived experience, you may raise confidence_style and lower hedging_style somewhat.\n"
        "- If the topic is far from the persona's profile, lower confidence_style and raise hedging_style.\n"
        "- Keep the modulation proportional and believable.\n\n"
        "Return JSON with this shape:\n"
        "{\n"
        '  "action": "allow | limited_answer | redirect | refuse",\n'
        '  "lexical_score": 0.0,\n'
        '  "relevance_score": 0.0,\n'
        '  "epistemic_score": 0.0,\n'
        '  "knowledge_level": "very_limited | limited | moderate | high",\n'
        '  "detail_allowed": false,\n'
        '  "expertise_basis": "none | biography_interest | lived_experience | work_exposure | education_background | domain_expert",\n'
        '  "hedging_style": "low | medium | high",\n'
        '  "confidence_style": "tentative | balanced | assured",\n'
        '  "language_level": "plain | everyday | nuanced | technical",\n'
        '  "register_style": "plain | everyday | polished | articulate",\n'
        '  "sentence_style": "short | mixed | long",\n'
        '  "abstraction_level": "concrete | mixed | abstract",\n'
        '  "vocabulary_level": "simple | moderate | advanced",\n'
        '  "explanation_style": "example_first | balanced | concept_first",\n'
        '  "tone_style": "calm | warm | direct | cautious | engaged",\n'
        '  "emotional_style": "neutral | reserved | empathetic | concerned | passionate",\n'
        '  "rationale": "short explanation",\n'
        '  "response_guidance": "clear advice for the answering model"\n'
        "}"
    )


def _safe_float(value, fallback: float) -> float:
    """Convert JSON numeric fields safely into floats."""
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return fallback


def _normalize_action(action: str | None) -> str:
    """Normalize the judge action into a supported policy action."""
    if action in {"allow", "limited_answer", "redirect", "refuse"}:
        return action
    return "limited_answer"


def _normalize_expertise_basis(value: str | None) -> str:
    """Normalize the expertise basis into a supported category."""
    if value in {
        "none",
        "biography_interest",
        "lived_experience",
        "work_exposure",
        "education_background",
        "domain_expert",
    }:
        return value
    return "none"


def _normalize_hedging_style(value: str | None) -> str:
    """Normalize hedging style into a supported category."""
    if value in {"low", "medium", "high"}:
        return value
    return "medium"


def _normalize_confidence_style(value: str | None) -> str:
    """Normalize confidence style into a supported category."""
    if value in {"tentative", "balanced", "assured"}:
        return value
    return "balanced"


def _safe_bool(value, fallback: bool) -> bool:
    """Convert JSON boolean-like fields safely into bools."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    return fallback


def _looks_like_policy_payload(payload: object) -> bool:
    """Return True when the payload already looks like the expected judge JSON."""
    return isinstance(payload, dict) and (
        "action" in payload
        or "response_guidance" in payload
        or "rationale" in payload
    )


def _unwrap_policy_payload(payload: object) -> dict | None:
    """Recover the real policy payload from common wrapper shapes returned by the judge."""
    current = payload

    for _ in range(4):
        if _looks_like_policy_payload(current):
            return current

        if isinstance(current, dict):
            for key in ("final", "response", "output", "result", "content"):
                nested = current.get(key)
                if _looks_like_policy_payload(nested):
                    return nested
                if isinstance(nested, str):
                    try:
                        current = json.loads(nested)
                        break
                    except json.JSONDecodeError:
                        continue
                if isinstance(nested, dict):
                    current = nested
                    break
            else:
                return None
            continue

        if isinstance(current, str):
            try:
                current = json.loads(current)
            except json.JSONDecodeError:
                return None
            continue

        return None

    if _looks_like_policy_payload(current):
        return current
    return None


def _parse_judge_response(raw_response: str, signals: GuardrailSignals) -> PolicyDecision:
    """Parse the judge JSON response with a safe fallback."""
    try:
        decoded = json.loads(raw_response)
    except json.JSONDecodeError:
        log.info("Judge parsing fallback")
        log.info("  Reason: invalid JSON returned by judge model")
        return PolicyDecision(
            action="limited_answer",
            rationale="The judge response could not be parsed cleanly, so the system falls back to a cautious answer.",
            response_guidance="Answer gently and cautiously from the persona's perspective. Stay grounded in the biography, keep the language plain, and avoid overclaiming.",
            detail_allowed=False,
            expertise_basis="none",
            hedging_style="medium",
            confidence_style="balanced",
            register_style="everyday",
            sentence_style="mixed",
            abstraction_level="mixed",
            vocabulary_level="moderate",
            explanation_style="balanced",
            lexical_score=1.0 if signals.lexical.triggered else 0.0,
            relevance_score=0.5,
            epistemic_score=0.5,
            knowledge_level="limited",
            language_level="plain",
            tone_style="cautious",
            emotional_style="neutral",
        )

    payload = _unwrap_policy_payload(decoded)
    if payload is None:
        log.info("Judge parsing fallback")
        log.info("  Reason: valid JSON returned, but no policy payload could be unwrapped")
        return PolicyDecision(
            action="limited_answer",
            rationale="The judge response used an unexpected structure, so the system falls back to a cautious answer.",
            response_guidance="Answer gently and cautiously from the persona's perspective. Stay grounded in the biography, keep the language plain, and avoid overclaiming.",
            detail_allowed=False,
            expertise_basis="none",
            hedging_style="medium",
            confidence_style="balanced",
            register_style="everyday",
            sentence_style="mixed",
            abstraction_level="mixed",
            vocabulary_level="moderate",
            explanation_style="balanced",
            lexical_score=1.0 if signals.lexical.triggered else 0.0,
            relevance_score=0.5,
            epistemic_score=0.5,
            knowledge_level="limited",
            language_level="plain",
            tone_style="cautious",
            emotional_style="neutral",
        )

    return PolicyDecision(
        action=_normalize_action(payload.get("action")),
        rationale=payload.get("rationale", "No rationale returned by judge."),
        response_guidance=payload.get(
            "response_guidance",
            "Answer cautiously from the persona's perspective and stay grounded in the biography.",
        ),
        detail_allowed=_safe_bool(payload.get("detail_allowed"), False),
        expertise_basis=_normalize_expertise_basis(payload.get("expertise_basis")),
        hedging_style=_normalize_hedging_style(payload.get("hedging_style")),
        confidence_style=_normalize_confidence_style(payload.get("confidence_style")),
        register_style=payload.get("register_style", "everyday"),
        sentence_style=payload.get("sentence_style", "mixed"),
        abstraction_level=payload.get("abstraction_level", "mixed"),
        vocabulary_level=payload.get("vocabulary_level", "moderate"),
        explanation_style=payload.get("explanation_style", "balanced"),
        lexical_score=_safe_float(payload.get("lexical_score"), 1.0 if signals.lexical.triggered else 0.0),
        relevance_score=_safe_float(payload.get("relevance_score"), 0.5),
        epistemic_score=_safe_float(payload.get("epistemic_score"), 0.5),
        knowledge_level=payload.get("knowledge_level", "limited"),
        language_level=payload.get("language_level", "plain"),
        tone_style=payload.get("tone_style", "cautious"),
        emotional_style=payload.get("emotional_style", "neutral"),
    )


# =============================================================================
# Public Decision Entry Point
# =============================================================================

def decide_policy(*, guardrail_input: GuardrailInput, signals: GuardrailSignals) -> PolicyDecision:
    """Convert guardrail signals into LLM-judged response advice."""
    judge_user_message = _build_judge_user_message(
        guardrail_input=guardrail_input,
        signals=signals,
    )
    messages = build_chat_messages(
        system_prompt=GUARDRAILED_JUDGE_SYS_PROMPT,
        user_message=judge_user_message,
        chat_history=guardrail_input.chat_history,
    )
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Judge System Prompt",
        content=GUARDRAILED_JUDGE_SYS_PROMPT,
        step_label="STEP 2",
    )
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Judge User Prompt",
        content=judge_user_message,
        step_label="STEP 2",
    )
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Judge Messages Payload",
        content=messages,
        step_label="STEP 2",
    )

    raw_response = run_chat_completion(
        messages=messages,
        temperature=0.1,
        json_mode=True,
    )
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Judge Raw Response",
        content=raw_response,
        step_label="STEP 2",
    )
    decision = _parse_judge_response(raw_response, signals)

    log.info("Judge determination")
    log.info("  Action: %s", decision.action)
    log.info("  Lexical score: %s", decision.lexical_score)
    log.info("  Relevance score: %s", decision.relevance_score)
    log.info("  Epistemic score: %s", decision.epistemic_score)
    log.info("  Knowledge level: %s", decision.knowledge_level)
    log.info("  Language level: %s", decision.language_level)
    log.info("  Register style: %s", decision.register_style)
    log.info("  Sentence style: %s", decision.sentence_style)
    log.info("  Abstraction level: %s", decision.abstraction_level)
    log.info("  Vocabulary level: %s", decision.vocabulary_level)
    log.info("  Explanation style: %s", decision.explanation_style)
    log.info("  Tone style: %s", decision.tone_style)
    log.info("  Emotional style: %s", decision.emotional_style)
    append_kv_block(
        trace=guardrail_input.session_trace,
        title="Judge Policy Decision",
        step_label="STEP 2",
        items=[
            ("Action", decision.action),
            ("Lexical score", decision.lexical_score),
            ("Relevance score", decision.relevance_score),
            ("Epistemic score", decision.epistemic_score),
            ("Knowledge level", decision.knowledge_level),
            ("Detail allowed", decision.detail_allowed),
            ("Expertise basis", decision.expertise_basis),
            ("Hedging style", decision.hedging_style),
            ("Confidence style", decision.confidence_style),
            ("Language level", decision.language_level),
            ("Register style", decision.register_style),
            ("Sentence style", decision.sentence_style),
            ("Abstraction level", decision.abstraction_level),
            ("Vocabulary level", decision.vocabulary_level),
            ("Explanation style", decision.explanation_style),
            ("Tone style", decision.tone_style),
            ("Emotional style", decision.emotional_style),
            ("Rationale", decision.rationale),
            ("Response guidance", decision.response_guidance),
        ],
    )

    return decision
