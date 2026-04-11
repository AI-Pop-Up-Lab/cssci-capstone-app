"""Guardrailed response mode for persona chat."""

from _persona_chat.guardrailed.pipeline import (
    build_guardrail_signals,
    log_guardrailed_request,
    run_epistemic_step,
    run_generator_step,
    run_judge_step,
    run_lexical_step,
    run_relevance_step,
    run_stylometric_step,
)
from _persona_chat.guardrailed.schemas import GuardrailInput
from _persona_chat.guardrailed.session_trace import append_turn_opening


# =============================================================================
# Public Engine Entry Point
# =============================================================================

def generate_response(persona_biography, user_message, chat_history, stylometric_profile, session_trace):
    """Generate a streamed response using the guardrailed persona pipeline."""
    guardrail_input = GuardrailInput(
        persona_biography=persona_biography,
        stylometric_profile=stylometric_profile,
        user_message=user_message,
        chat_history=chat_history,
        session_trace=session_trace,
    )

    append_turn_opening(
        trace=session_trace,
        user_message=user_message,
        chat_history=chat_history,
        biography=persona_biography,
        stylometric_profile=stylometric_profile,
    )

    # =============================================================================
    # Step 0: Log The Incoming Request
    # =============================================================================
    log_guardrailed_request(guardrail_input)

    # =============================================================================
    # Step 1A: Run Lexical Detection
    # =============================================================================
    lexical_signal = run_lexical_step(guardrail_input)

    # =============================================================================
    # Step 1B: Run Relevance Detection
    # =============================================================================
    relevance_signal = run_relevance_step(guardrail_input)

    # =============================================================================
    # Step 1C: Run Epistemic Detection
    # =============================================================================
    epistemic_signal = run_epistemic_step(guardrail_input)

    # =============================================================================
    # Step 1D: Run Stylometric Preparation
    # =============================================================================
    stylometric_signal = run_stylometric_step(guardrail_input)

    # =============================================================================
    # Step 1E: Bundle The Guardrail Signals
    # =============================================================================
    signals = build_guardrail_signals(
        session_trace=session_trace,
        lexical_signal=lexical_signal,
        relevance_signal=relevance_signal,
        epistemic_signal=epistemic_signal,
        stylometric_signal=stylometric_signal,
    )

    # =============================================================================
    # Step 2: Run The Judge Decision
    # =============================================================================
    policy = run_judge_step(
        guardrail_input=guardrail_input,
        signals=signals,
    )

    # =============================================================================
    # Step 3: Run Final Response Generation
    # =============================================================================
    
    return run_generator_step(
        guardrail_input=guardrail_input,
        signals=signals,
        policy=policy,
    )
