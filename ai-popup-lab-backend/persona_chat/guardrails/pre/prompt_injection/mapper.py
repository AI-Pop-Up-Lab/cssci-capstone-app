from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.guardrails.gates.decision import PreGateDecision


@dataclass(frozen=True)
class InjectionGateResult:
    user_for_llm: str
    action: str          # ALLOW | CAUTIOUS | STEER | REFUSE
    lexical_score: int
    judge_used: bool     # always True-ish conceptually because the combined validator judged it, but keep False to mean "no separate judge"
    debug: dict[str, Any]


def injection_from_combined_validator(
    *,
    user_text: str,
    combined: PreGateDecision,
) -> InjectionGateResult:
    text = (user_text or "").strip()

    debug = {
        "mode": "combined_validator",
        "lexical_score": combined.injection_lexical_score,
        "matches": combined.injection_matches,
        "injection": {
            "verdict": combined.injection_verdict,
            "action": combined.injection_action,
            "confidence": combined.injection_confidence,
            "reason": combined.injection_reason,
            "signals": combined.injection_signals,
        },
        "final": {"action": combined.final_action, "reason": combined.final_reason},
    }

    return InjectionGateResult(
        user_for_llm=combined.user_for_llm or text,
        action=combined.injection_action,
        lexical_score=combined.injection_lexical_score,
        judge_used=False,  # no separate injection judge exists anymore
        debug=debug,
    )