"""
app/guardrails/manager.py

============================================================
GUARDRAILS ORCHESTRATOR (PIPELINE ENTRYPOINT)
============================================================

This module is the single entrypoint for all *guardrails* used by the pipeline.

Guardrails here are divided into two stages:

1) PRE-LLM GATE (input validation / sanitization)
   - Can refuse/steer before generation
   - Produces: InjectionGateBundle, TopicGateBundle, combined debug

2) POST-LLM ENFORCING CHECKS (output enforcement)
   - Runs after model generates output
   - Can force refusal (generic) if an enforcing check fails

Monitoring lives in app/coherence/manager.py and is never enforcing.
"""

from __future__ import annotations

from typing import Any

from app.guardrails.pre.engine import orchestrate_combined_validation

from app.guardrails.pre.topic.mapper import topic_from_combined_validator
from app.guardrails.pre.prompt_injection.mapper import injection_from_combined_validator

from app.guardrails.gates.gates import (
    TopicGateBundle,
    InjectionGateBundle,
)


# ============================================================
# PRE-LLM: entrypoint (validator + mapping)
# ============================================================

async def run_pre_guardrails(
    *,
    provider: Any,
    persona_id: str,
    snapshot_id: str,
    user_text: str,
    grounding: Any,
) -> tuple[InjectionGateBundle, TopicGateBundle, dict[str, Any]]:
    """
    Runs the combined validator and maps output into gate bundles.

    Returns:
      - InjectionGateBundle
      - TopicGateBundle
      - combined.debug
    """
    combined = await orchestrate_combined_validation(
        provider=provider,
        user_text=user_text,
        persona_id=persona_id,
        snapshot_id=snapshot_id,
        profile=grounding.profile,
        answers=grounding.answers,
        suggested_questions=grounding.suggested_questions,
    )

    inj_res = injection_from_combined_validator(user_text=user_text, combined=combined)
    topic_res = topic_from_combined_validator(user_text=user_text, combined=combined)

    overall_tier = topic_res.overall_tier
    if overall_tier == "deny":
        topic_action = "REFUSE"
    elif overall_tier == "steer":
        topic_action = "CAUTIOUS"
    else:
        topic_action = "ANSWER"

    inj_bundle = InjectionGateBundle(
        user_for_llm=inj_res.user_for_llm,
        injection_action=inj_res.action,
        lexical_score=inj_res.lexical_score,
        judge_used=inj_res.judge_used,
        debug=inj_res.debug,
    )

    topic_bundle = TopicGateBundle(
        user_for_llm=topic_res.user_for_llm,
        overall_tier=topic_res.overall_tier,
        topic_action=topic_action,
        has_mixed=topic_res.has_mixed,
        debug=topic_res.debug,
        kept_segments=topic_res.kept_segments,
        dropped_segments=topic_res.dropped_segments,
    )

    return inj_bundle, topic_bundle, combined.debug