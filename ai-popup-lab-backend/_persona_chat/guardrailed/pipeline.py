"""Single-purpose step functions for the guardrailed response mode."""

from _persona_chat.guardrailed.epistemic import evaluate_epistemic_boundaries
from _persona_chat.guardrailed.generator import generate_policy_response
from _persona_chat.guardrailed.judge import decide_policy
from _persona_chat.guardrailed.lexical import detect_prompt_injection
from _persona_chat.guardrailed.relevance import evaluate_relevance
from _persona_chat.guardrailed.stylometry import prepare_stylometric_signal
from _persona_chat.guardrailed.schemas import (
    EpistemicSignal,
    GuardrailInput,
    GuardrailSignals,
    LexicalSignal,
    PolicyDecision,
    RelevanceSignal,
    StylometricSignal,
)
from _persona_chat.guardrailed.session_trace import append_kv_block, append_named_block
from _persona_chat.logging import get_logger


log = get_logger(__name__)


def _log_section(title: str) -> None:
    """Write a readable section header to the guardrail log."""
    log.info("")
    log.info("============================================================")
    log.info("%s", title)
    log.info("============================================================")


# =============================================================================
# Step 0: Request Logging
# =============================================================================

def log_guardrailed_request(guardrail_input: GuardrailInput) -> None:
    """Log the incoming request and its basic context."""
    _log_section("Guardrailed Request")
    log.info("User message")
    log.info("  %s", guardrail_input.user_message)
    log.info("")
    log.info("Context")
    log.info("  History turns: %s", len(guardrail_input.chat_history))
    log.info("  Biography length: %s characters", len(guardrail_input.persona_biography))
    log.info(
        "  Stylometric summary: %s",
        guardrail_input.stylometric_profile.get("profile_summary", "None"),
    )
    append_kv_block(
        trace=guardrail_input.session_trace,
        title="Request Context",
        step_label="STEP 0",
        items=[
            ("User message", guardrail_input.user_message),
            ("History turns", len(guardrail_input.chat_history)),
            ("Biography length", f"{len(guardrail_input.persona_biography)} characters"),
            (
                "Stylometric summary",
                guardrail_input.stylometric_profile.get("profile_summary", "None"),
            ),
        ],
    )


# =============================================================================
# Step 1A: Lexical Check
# =============================================================================

def run_lexical_step(guardrail_input: GuardrailInput) -> LexicalSignal:
    """Run lexical prompt-injection detection."""
    signal = detect_prompt_injection(guardrail_input.user_message)
    log.info("Step 1A: Lexical Prompt Injection")
    log.info("  Triggered: %s", signal.triggered)
    log.info("  Matched terms: %s", signal.matched_terms or "None")
    log.info("")
    append_kv_block(
        trace=guardrail_input.session_trace,
        title="Lexical Check",
        step_label="STEP 1A",
        items=[
            ("Triggered", signal.triggered),
            ("Risk level", signal.risk_level),
            ("Matched terms", signal.matched_terms or "None"),
        ],
    )
    return signal


# =============================================================================
# Step 1B: Relevance Check
# =============================================================================

def run_relevance_step(guardrail_input: GuardrailInput) -> RelevanceSignal:
    """Prepare topic relevance sub-prompt context for the judge model."""
    signal = evaluate_relevance(
        user_message=guardrail_input.user_message,
        persona_biography=guardrail_input.persona_biography,
    )
    log.info("Step 1B: Topic Relevance")
    log.info("  Mode: judge sub-prompt preparation")
    log.info("  Summary: %s", signal.summary)
    log.info("")
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Relevance Summary",
        content=signal.summary,
        step_label="STEP 1B",
    )
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Relevance Judge Prompt",
        content=signal.judge_prompt,
        step_label="STEP 1B",
    )
    return signal


# =============================================================================
# Step 1C: Epistemic Check
# =============================================================================

def run_epistemic_step(guardrail_input: GuardrailInput) -> EpistemicSignal:
    """Prepare epistemic sub-prompt context for the judge model."""
    signal = evaluate_epistemic_boundaries(
        user_message=guardrail_input.user_message,
        persona_biography=guardrail_input.persona_biography,
    )
    log.info("Step 1C: Epistemic Boundary")
    log.info("  Mode: judge sub-prompt preparation")
    log.info("  Summary: %s", signal.summary)
    log.info("")
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Epistemic Summary",
        content=signal.summary,
        step_label="STEP 1C",
    )
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Epistemic Judge Prompt",
        content=signal.judge_prompt,
        step_label="STEP 1C",
    )
    return signal


# =============================================================================
# Step 1D: Stylometric Check
# =============================================================================

def run_stylometric_step(guardrail_input: GuardrailInput) -> StylometricSignal:
    """Prepare stylometric sub-prompt context for the judge model."""
    signal = prepare_stylometric_signal(
        stylometric_profile=guardrail_input.stylometric_profile,
    )
    log.info("Step 1D: Stylometric Profile")
    log.info("  Mode: judge sub-prompt preparation")
    log.info("  Summary: %s", signal.summary)
    log.info("")
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Stylometric Summary",
        content=signal.summary,
        step_label="STEP 1D",
    )
    append_named_block(
        trace=guardrail_input.session_trace,
        title="Stylometric Judge Prompt",
        content=signal.judge_prompt,
        step_label="STEP 1D",
    )
    return signal


# =============================================================================
# Step 1E: Signal Bundle
# =============================================================================

def build_guardrail_signals(
    *,
    session_trace,
    lexical_signal: LexicalSignal,
    relevance_signal: RelevanceSignal,
    epistemic_signal: EpistemicSignal,
    stylometric_signal: StylometricSignal,
) -> GuardrailSignals:
    """Bundle the individual stage outputs into one signal object."""
    _log_section("Guardrail Signals")
    signals = GuardrailSignals(
        lexical=lexical_signal,
        relevance=relevance_signal,
        epistemic=epistemic_signal,
        stylometric=stylometric_signal,
    )
    append_named_block(
        trace=session_trace,
        title="Bundled Guardrail Signals",
        content={
            "lexical": {
                "triggered": lexical_signal.triggered,
                "matched_terms": lexical_signal.matched_terms,
                "risk_level": lexical_signal.risk_level,
            },
            "relevance": {"summary": relevance_signal.summary},
            "epistemic": {"summary": epistemic_signal.summary},
            "stylometric": {"summary": stylometric_signal.summary},
        },
        step_label="STEP 1E",
    )
    return signals


# =============================================================================
# Step 2: Judge
# =============================================================================

def run_judge_step(
    *,
    guardrail_input: GuardrailInput,
    signals: GuardrailSignals,
) -> PolicyDecision:
    """Run the judge step and log the selected policy."""
    policy = decide_policy(guardrail_input=guardrail_input, signals=signals)

    _log_section("Guardrail Policy")
    log.info("Step 2: Judge Decision")
    log.info("  Action: %s", policy.action)
    log.info("  Lexical score: %s", policy.lexical_score)
    log.info("  Relevance score: %s", policy.relevance_score)
    log.info("  Epistemic score: %s", policy.epistemic_score)
    log.info("  Knowledge level: %s", policy.knowledge_level)
    log.info("  Language level: %s", policy.language_level)
    log.info("  Register style: %s", policy.register_style)
    log.info("  Sentence style: %s", policy.sentence_style)
    log.info("  Abstraction level: %s", policy.abstraction_level)
    log.info("  Vocabulary level: %s", policy.vocabulary_level)
    log.info("  Explanation style: %s", policy.explanation_style)
    log.info("  Tone style: %s", policy.tone_style)
    log.info("  Emotional style: %s", policy.emotional_style)
    log.info("  Why: %s", policy.rationale)
    log.info("  Guidance: %s", policy.response_guidance)
    return policy


# =============================================================================
# Step 3: Generator
# =============================================================================

def run_generator_step(
    *,
    guardrail_input: GuardrailInput,
    signals: GuardrailSignals,
    policy: PolicyDecision,
):
    """Run the final guarded response generation step."""
    return generate_policy_response(
        guardrail_input=guardrail_input,
        signals=signals,
        policy=policy,
    )
