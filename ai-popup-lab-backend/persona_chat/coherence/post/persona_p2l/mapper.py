from __future__ import annotations

from typing import Any

from app.guardrails.contract import GuardrailResult
from app.coherence.post.persona_p2l.gate import PersonaP2LGateResult


def map_persona_p2l_to_result(*, name: str, gate: PersonaP2LGateResult) -> GuardrailResult:
    """
    Monitor-only mapping:
    - ALWAYS ok=True
    - Put everything in details for trace storage
    """
    details: dict[str, Any] = {
        "mode": "monitor_only",
        "issue": gate.issue,
        "ok_here": gate.ok_here,
        "verdict": gate.verdict,
        "confidence": gate.confidence,
        "coherence_score": gate.coherence_score,
        "violations": gate.violations,
        **(gate.notes or {}),
    }
    return GuardrailResult(ok=True, name=name, details=details)