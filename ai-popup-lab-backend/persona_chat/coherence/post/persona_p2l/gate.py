from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.coherence.post.persona_p2l.config import PersonaP2LConfig
from app.coherence.post.persona_p2l.prompts import build_persona_p2l_system_prompt, DEFAULT_JUDGE_CONFIG


@dataclass(frozen=True)
class PersonaP2LGateResult:
    """
    Gate output for prompt-to-line coherence.

    ok_here is NOT enforcement; it's for reporting only.
    Monitor must still return GuardrailResult(ok=True).
    """
    ok_here: bool
    issue: str | None
    verdict: str
    confidence: float
    coherence_score: float
    violations: list[dict[str, Any]]
    notes: dict[str, Any]


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


async def run_persona_p2l_gate(
    *,
    context: dict[str, Any],
    cfg: PersonaP2LConfig,
) -> PersonaP2LGateResult:
    """
    POST coherence gate.

    Expects in context (suggested):
      - context["provider"] : LLM provider (must support .generate(system=..., user=..., grounding={}))
      - context["profile"] : dict
      - context["answers"] : list[dict] (stored answers)
      - context["user_text"] : str
      - context["llm_output"] : str (assistant draft)
      - context["chat_messages"] : optional list of prior turns (for judge context)
    """
    provider = context.get("provider")
    profile = context.get("profile")
    answers = context.get("answers")
    user_text = context.get("user_text")
    assistant_output = context.get("llm_output")
    session_context = context.get("chat_messages", [])

    notes: dict[str, Any] = {
        "has_provider": provider is not None,
        "profile_type": type(profile).__name__,
        "answers_type": type(answers).__name__,
        "assistant_output_len": len(assistant_output.strip()) if isinstance(assistant_output, str) else 0,
        "session_turns": len(session_context) if isinstance(session_context, list) else None,
    }

    # Minimal health checks (monitor-only)
    if not cfg.enable:
        return PersonaP2LGateResult(
            ok_here=True,
            issue="disabled",
            verdict="PASS",
            confidence=1.0,
            coherence_score=1.0,
            violations=[],
            notes=notes,
        )

    if provider is None:
        return PersonaP2LGateResult(
            ok_here=False,
            issue="missing_provider",
            verdict="WARN",
            confidence=0.0,
            coherence_score=0.0,
            violations=[],
            notes=notes,
        )

    if not isinstance(profile, dict) or not isinstance(assistant_output, str) or not assistant_output.strip():
        return PersonaP2LGateResult(
            ok_here=False,
            issue="missing_profile_or_output",
            verdict="WARN",
            confidence=0.0,
            coherence_score=0.0,
            violations=[],
            notes=notes,
        )

    system = build_persona_p2l_system_prompt(DEFAULT_JUDGE_CONFIG)
    payload = {
        "persona_profile": profile,
        "recorded_answers": answers or [],
        "session_context": session_context if isinstance(session_context, list) else [],
        "user_text": user_text or "",
        "assistant_output": assistant_output,
    }

    # Judge call (LLM)
    judge_raw = await provider.generate(
        system=system,
        user=json.dumps(payload, ensure_ascii=False),
        grounding={},
    )

    # Provider output shape varies; assume string content in judge_raw["content"] or judge_raw directly
    judge_text = judge_raw.get("content") if isinstance(judge_raw, dict) else str(judge_raw)

    try:
        obj = json.loads(judge_text)
    except Exception:
        # Judge returned invalid JSON
        return PersonaP2LGateResult(
            ok_here=False,
            issue="judge_invalid_json",
            verdict="WARN",
            confidence=0.0,
            coherence_score=0.0,
            violations=[],
            notes={**notes, "judge_preview": judge_text[:200]},
        )

    verdict = str(obj.get("verdict", "WARN"))
    confidence = _safe_float(obj.get("confidence", 0.0))
    violations = obj.get("violations") or []
    score_obj = obj.get("score") or {}
    coherence_score = _safe_float(score_obj.get("coherence_score", 0.0))

    # ok_here is just health; do NOT enforce
    ok_here = True
    issue = None
    if verdict in ("FAIL",) or (isinstance(coherence_score, float) and coherence_score < cfg.min_score_warn):
        issue = "p2l_incoherence_detected"

    return PersonaP2LGateResult(
        ok_here=ok_here,
        issue=issue,
        verdict=verdict,
        confidence=confidence,
        coherence_score=coherence_score,
        violations=violations[: cfg.max_violations],
        notes=notes,
    )