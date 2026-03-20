from __future__ import annotations

import json
import re
from typing import Any

from app.core.utils import get_logger
from app.guardrails.prompts import DEFAULT_CONFIG, ValidatorConfig, build_combined_validator_system_prompt

from app.guardrails.pre.prompt_injection.gate import run_injection_lexical_precheck
from app.guardrails.pre.prompt_injection.config import (
    DEFAULT_CONFIG as INJ_DEFAULT_CONFIG,
    InjectionGateConfig,
)
from app.guardrails.pre.topic.config import (
    DEFAULT_CONFIG as TOPIC_DEFAULT_CONFIG,
    TopicGateConfig,
)

from app.guardrails.gates.decision import PreGateDecision


log = get_logger(__name__)

_JSON_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE | re.MULTILINE)


def _strip_fences(s: str) -> str:
    return _JSON_FENCE_RE.sub("", (s or "")).strip()


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _norm_injection_verdict(v: Any) -> str:
    vv = str(v or "").strip().upper()
    return vv if vv in {"NONE", "LOW", "MED", "HIGH"} else "LOW"


def _norm_injection_action(a: Any) -> str:
    aa = str(a or "").strip().upper()
    return aa if aa in {"ALLOW", "CAUTIOUS", "STEER", "REFUSE"} else "CAUTIOUS"


def _norm_scope(x: Any) -> str:
    v = str(x or "").strip().upper()
    return v if v in {"IN_SCOPE", "OUT_OF_SCOPE", "SMALLTALK"} else "OUT_OF_SCOPE"


def _norm_decision(x: Any) -> str:
    v = str(x or "").strip().upper()
    return v if v in {"ANSWER", "SOFT_DENY", "REDIRECT", "REFUSE"} else "REFUSE"


def _norm_topic_tier(x: Any) -> str:
    v = str(x or "").strip().lower()
    return v if v in {"allow", "partial", "steer", "deny"} else "steer"


def _norm_topic_action(x: Any) -> str:
    v = str(x or "").strip().upper()
    return v if v in {"ANSWER", "PARTIAL_ANSWER", "STEER", "REFUSE"} else "STEER"


# ============================================================
# PRE-LLM: combined validator call
# ============================================================

async def orchestrate_combined_validation(
    *,
    provider: Any,
    user_text: str,
    persona_id: str,
    snapshot_id: str,
    profile: dict[str, Any],
    answers: list[dict[str, Any]],
    suggested_questions: list[Any],
    cfg: ValidatorConfig = DEFAULT_CONFIG,
    inj_cfg: InjectionGateConfig = INJ_DEFAULT_CONFIG,
    topic_cfg: TopicGateConfig = TOPIC_DEFAULT_CONFIG,
) -> PreGateDecision:
    text = (user_text or "").strip()
    if not text:
        return PreGateDecision(
            injection_verdict="LOW",
            injection_action="REFUSE",
            injection_confidence=0.0,
            injection_reason="empty_user_text",
            injection_signals={},
            injection_lexical_score=0,
            injection_matches=[],
            topic_items=[],
            topic_overall_tier="deny",
            topic_overall_action="REFUSE",
            final_action="REFUSE",
            final_reason="empty_user_text",
            user_for_llm="",
            debug={"reason": "empty_user_text"},
        )

    # ------------------------------------------------------------
    # Local deterministic lexical injection (via gate entrypoint)
    # ------------------------------------------------------------
    inj_lex = run_injection_lexical_precheck(
        user_text=text,
        cfg=inj_cfg,
        max_matches=cfg.max_injection_matches,
    )
    matches_payload = inj_lex.matches_payload

    # ------------------------------------------------------------
    # Compact profile
    # ------------------------------------------------------------
    profile_compact = dict(profile or {})
    for k in ["raw_text", "full_bio", "long_summary"]:
        if k in profile_compact and isinstance(profile_compact[k], str) and len(profile_compact[k]) > 2000:
            profile_compact[k] = profile_compact[k][:2000] + "…"

    # ------------------------------------------------------------
    # Compact answers
    # ------------------------------------------------------------
    answers_compact: list[dict[str, Any]] = []
    for a in (answers or [])[:15]:
        answers_compact.append(
            {
                "question_id": a.get("question_id"),
                "question_text": a.get("question_text"),
                "answer_value": a.get("answer_value"),
                "answer_text": a.get("answer_text"),
                "wave": a.get("wave"),
                "confidence": a.get("confidence"),
            }
        )

    suggested_compact = (
        suggested_questions[: cfg.max_suggested_questions]
        if isinstance(suggested_questions, list)
        else suggested_questions
    )

    system = build_combined_validator_system_prompt(cfg)

    user_payload = {
        "persona_id": persona_id,
        "snapshot_id": snapshot_id,
        "user_text": text,
        "persona_profile": profile_compact,
        "recorded_answers": answers_compact,
        "suggested_questions": suggested_compact,
        "limits": {"max_items": cfg.max_items},
        "injection_lexical_signals": {
            "lexical_threshold": inj_cfg.lexical_threshold,
            "lexical_score": inj_lex.score,
            "is_suspicious": inj_lex.is_suspicious,
            "dangerous_terms": inj_lex.dangerous_terms,
            "categories": inj_lex.categories,
            "matches": matches_payload,
            "reason": inj_lex.reason,
        },
        "topic_config_hints": {
            "prefer_in_scope_for_politics": topic_cfg.prefer_in_scope_for_politics,
            "treat_smalltalk_as_steer": topic_cfg.treat_smalltalk_as_steer,
        },
    }

    log.warning(
        "[GUARDRAILS][PRE] FULL_PROMPT_BEGIN\nSYSTEM:\n%s\n\nUSER:\n%s\nFULL_PROMPT_END",
        system,
        json.dumps(user_payload, ensure_ascii=False),
    )

    resp = await provider.generate(
        system=system,
        user=json.dumps(user_payload, ensure_ascii=False),
        grounding={},
    )

    raw = _strip_fences(getattr(resp, "content", "") or "")
    log.warning("[GUARDRAILS][PRE] raw_response_preview=%r", raw[:260])

    try:
        parsed = json.loads(raw)
    except Exception as e:
        log.error("[GUARDRAILS][PRE] json_parse_failed err=%s", str(e))
        return PreGateDecision(
            injection_verdict="LOW",
            injection_action="CAUTIOUS",
            injection_confidence=0.15,
            injection_reason="validator_json_parse_failed",
            injection_signals={},
            injection_lexical_score=inj_lex.score,
            injection_matches=matches_payload,
            topic_items=[],
            topic_overall_tier="steer",
            topic_overall_action="STEER",
            final_action="STEER",
            final_reason="validator_json_parse_failed",
            user_for_llm=text,
            debug={
                "raw": raw,
                "parse_error": True,
                "exception": str(e),
                "lexical": user_payload["injection_lexical_signals"],
            },
        )

    inj = parsed.get("injection") or {}
    topic = parsed.get("scope") or {}
    final = parsed.get("final") or {}

    injection_verdict = _norm_injection_verdict(inj.get("verdict"))
    injection_action = _norm_injection_action(inj.get("action"))
    injection_conf = max(0.0, min(1.0, _safe_float(inj.get("confidence"), 0.0)))
    injection_reason = (str(inj.get("reason") or "").strip() or None)

    sig_in = inj.get("signals") or {}
    injection_signals: dict[str, bool] = {}
    if isinstance(sig_in, dict):
        for k, v in sig_in.items():
            injection_signals[str(k)] = bool(v)

    items_in = (topic.get("items") or [])[: cfg.max_items]
    topic_items: list[dict[str, Any]] = []
    for it in items_in:
        if not isinstance(it, dict):
            continue
        t = str(it.get("text") or "").strip()
        if not t:
            continue
        topic_items.append(
            {
                "text": t,
                "topic_label": (str(it.get("topic_label")) if it.get("topic_label") is not None else None),
                "scope": _norm_scope(it.get("scope")),
                "confidence": max(0.0, min(1.0, _safe_float(it.get("confidence"), 0.0))),
                "decision": _norm_decision(it.get("decision")),
                "reason": (str(it.get("reason")) if it.get("reason") is not None else None),
            }
        )

    overall = topic.get("overall") or {}
    topic_overall_tier = _norm_topic_tier(overall.get("tier"))
    topic_overall_action = _norm_topic_action(overall.get("action"))

    final_action = _norm_injection_action(final.get("action"))
    final_reason = (str(final.get("reason") or "").strip() or None)

    user_for_llm = str(parsed.get("user_for_llm") or "").strip() or text

    debug = {
        "raw": raw,
        "parse_error": False,
        "parsed": parsed,
        "lexical": user_payload["injection_lexical_signals"],
    }

    log.warning(
        "[GUARDRAILS][PRE] decision final=%s topic_tier=%s topic_action=%s inj_verdict=%s inj_action=%s lex_score=%s",
        final_action,
        topic_overall_tier,
        topic_overall_action,
        injection_verdict,
        injection_action,
        inj_lex.score,
    )

    return PreGateDecision(
        injection_verdict=injection_verdict,
        injection_action=injection_action,
        injection_confidence=injection_conf,
        injection_reason=injection_reason,
        injection_signals=injection_signals,
        injection_lexical_score=inj_lex.score,
        injection_matches=matches_payload,
        topic_items=topic_items,
        topic_overall_tier=topic_overall_tier,
        topic_overall_action=topic_overall_action,
        final_action=final_action,
        final_reason=final_reason,
        user_for_llm=user_for_llm,
        debug=debug,
    )