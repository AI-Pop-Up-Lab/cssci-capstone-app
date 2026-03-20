from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.guardrails.gates.decision import PreGateDecision


@dataclass(frozen=True)
class TopicOrchestrationResult:
    segments: list[str]
    decisions: list[Any]              # kept for compatibility with your types/logging
    kept_segments: list[str]
    dropped_segments: list[str]
    user_for_llm: str
    has_mixed: bool
    overall_tier: str                 # allow | partial | steer | deny
    action: str                       # ANSWER | PARTIAL_ANSWER | STEER | REFUSE
    debug: dict[str, Any]


def topic_from_combined_validator(
    *,
    user_text: str,
    combined: PreGateDecision,
) -> TopicOrchestrationResult:
    text = (user_text or "").strip()
    items = combined.topic_items or []

    kept = [it["text"] for it in items if it.get("decision") in ("ANSWER", "SOFT_DENY")]
    dropped = [it["text"] for it in items if it.get("decision") in ("REDIRECT", "REFUSE")]
    has_mixed = bool(kept) and bool(dropped)

    debug = {
        "mode": "combined_validator",
        "original": text,
        "tier": combined.topic_overall_tier,
        "action": combined.topic_overall_action,
        "has_mixed": has_mixed,
        "user_for_llm": combined.user_for_llm,
        "items": items,
        "validator": {
            "final_action": combined.final_action,
            "final_reason": combined.final_reason,
        },
    }

    return TopicOrchestrationResult(
        segments=[text] if text else [],
        decisions=items,  # keep as list of dicts; your logger can adapt
        kept_segments=kept,
        dropped_segments=dropped,
        user_for_llm=combined.user_for_llm or text,
        has_mixed=has_mixed,
        overall_tier=combined.topic_overall_tier,
        action=combined.topic_overall_action,
        debug=debug,
    )