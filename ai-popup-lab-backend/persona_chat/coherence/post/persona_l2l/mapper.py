from __future__ import annotations

from typing import Any

from app.guardrails.contract import GuardrailResult
from app.coherence.post.persona_l2l.gate import PersonaL2LGateResult


def map_persona_l2l_to_result(*, name: str, gate: PersonaL2LGateResult) -> GuardrailResult:
    details: dict[str, Any] = {
        "mode": "monitor_only",
        "issue": gate.issue,
        "ok_here": gate.ok_here,
        "verdict": gate.verdict,
        "confidence": gate.confidence,
        "consistency_score": gate.consistency_score,
        "contradictions": gate.contradictions,
        **(gate.notes or {}),
    }
    return GuardrailResult(ok=True, name=name, details=details)