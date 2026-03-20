from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.coherence.post.persona_l2l.config import PersonaL2LConfig
from app.coherence.post.persona_l2l.prompts import build_persona_l2l_system_prompt, DEFAULT_JUDGE_CONFIG


@dataclass(frozen=True)
class PersonaL2LGateResult:
    ok_here: bool
    issue: str | None
    verdict: str
    confidence: float
    consistency_score: float
    contradictions: list[dict[str, Any]]
    notes: dict[str, Any]


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


async def run_persona_l2l_gate(
    *,
    context: dict[str, Any],
    cfg: PersonaL2LConfig,
) -> PersonaL2LGateResult:
    provider = context.get("provider")
    user_text = context.get("user_text") or ""
    assistant_output = context.get("llm_output")
    session_messages = context.get("chat_messages", [])

    notes: dict[str, Any] = {
        "has_provider": provider is not None,
        "assistant_output_len": len(assistant_output.strip()) if isinstance(assistant_output, str) else 0,
        "session_turns": len(session_messages) if isinstance(session_messages, list) else None,
    }

    if not cfg.enable:
        return PersonaL2LGateResult(
            ok_here=True,
            issue="disabled",
            verdict="PASS",
            confidence=1.0,
            consistency_score=1.0,
            contradictions=[],
            notes=notes,
        )

    if provider is None:
        return PersonaL2LGateResult(
            ok_here=False,
            issue="missing_provider",
            verdict="WARN",
            confidence=0.0,
            consistency_score=0.0,
            contradictions=[],
            notes=notes,
        )

    if not isinstance(assistant_output, str) or not assistant_output.strip():
        return PersonaL2LGateResult(
            ok_here=False,
            issue="empty_or_invalid_llm_output",
            verdict="WARN",
            confidence=0.0,
            consistency_score=0.0,
            contradictions=[],
            notes=notes,
        )

    # If no prior turns, nothing to compare
    if not isinstance(session_messages, list) or len(session_messages) < 2:
        return PersonaL2LGateResult(
            ok_here=True,
            issue=None,
            verdict="PASS",
            confidence=1.0,
            consistency_score=1.0,
            contradictions=[],
            notes=notes,
        )

    system = build_persona_l2l_system_prompt(DEFAULT_JUDGE_CONFIG)
    payload = {
        "session_messages": session_messages,
        "user_text": user_text,
        "assistant_output": assistant_output,
    }

    judge_raw = await provider.generate(
        system=system,
        user=json.dumps(payload, ensure_ascii=False),
        grounding={},
    )

    judge_text = judge_raw.get("content") if isinstance(judge_raw, dict) else str(judge_raw)

    try:
        obj = json.loads(judge_text)
    except Exception:
        return PersonaL2LGateResult(
            ok_here=False,
            issue="judge_invalid_json",
            verdict="WARN",
            confidence=0.0,
            consistency_score=0.0,
            contradictions=[],
            notes={**notes, "judge_preview": judge_text[:200]},
        )

    verdict = str(obj.get("verdict", "WARN"))
    confidence = _safe_float(obj.get("confidence", 0.0))
    contradictions = obj.get("contradictions") or []
    score_obj = obj.get("score") or {}
    consistency_score = _safe_float(score_obj.get("consistency_score", 0.0))

    issue = None
    if verdict in ("FAIL",) or consistency_score < cfg.min_consistency_warn:
        issue = "l2l_contradiction_detected"

    return PersonaL2LGateResult(
        ok_here=True,
        issue=issue,
        verdict=verdict,
        confidence=confidence,
        consistency_score=consistency_score,
        contradictions=contradictions[: cfg.max_contradictions],
        notes=notes,
    )