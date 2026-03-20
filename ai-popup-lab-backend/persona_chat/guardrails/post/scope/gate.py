from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.core.utils import get_logger
from app.guardrails.post.scope.lexical import build_persona_corpus, compute_topic_relevance, TopicRelevance
from app.guardrails.post.scope.config import TopicGateConfig, DEFAULT_CONFIG

log = get_logger(__name__)


# Conservative smalltalk detector (same idea as your existing OutputScopeCheck)
_SMALLTALK_RE = re.compile(
    r"^\s*(hi|hey|hello|yo|sup|good\s+(morning|afternoon|evening)|"
    r"how\s+are\s+you|how’s\s+it\s+going|hows\s+it\s+going|"
    r"thanks|thank\s+you|thx|ty|ok|okay|k|cool|nice)\b",
    re.IGNORECASE,
)


def _looks_like_provider_error(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    patterns = [
        "temporarily experiencing connection issues",
        "please try again shortly",
        "too many requests",
        "rate limit",
        "status=429",
        "http 429",
        "exhausted retries",
        "service unavailable",
        "gateway timeout",
    ]
    return any(p in t for p in patterns)


def _gate_says_all_smalltalk(context: dict[str, Any]) -> bool:
    tp = context.get("topic_precheck") or {}
    items = tp.get("items") or []
    if not isinstance(items, list) or not items:
        return False

    scopes: list[str] = []
    for it in items:
        if isinstance(it, dict):
            scopes.append(str(it.get("scope") or "").upper().strip())

    return bool(scopes) and all(s == "SMALLTALK" for s in scopes)


def _is_smalltalk(text: str, *, max_chars: int) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if len(t) <= max_chars and _SMALLTALK_RE.search(t):
        return True
    if len(t) <= 3:
        return True
    return False


@dataclass(frozen=True)
class OutputScopeGateResult:
    bypassed: bool
    bypass_reason: str | None
    relevance: TopicRelevance | None


async def llm_topic_gate(  # name matches PRE structure; POST implementation is lexical
    *,
    context: dict[str, Any],
    cfg: TopicGateConfig = DEFAULT_CONFIG,
) -> OutputScopeGateResult:
    profile = context.get("profile", {}) or {}
    answers = context.get("answers", []) or []
    llm_output = (context.get("llm_output") or "").strip()

    if not llm_output:
        return OutputScopeGateResult(bypassed=False, bypass_reason=None, relevance=TopicRelevance(0.0, "deny", "empty_output"))

    # Provider error bypass
    if cfg.bypass_provider_errors and _looks_like_provider_error(llm_output):
        return OutputScopeGateResult(bypassed=True, bypass_reason="provider_error_message", relevance=None)

    # Smalltalk bypass (from upstream scope gate)
    if cfg.smalltalk_allowed and _gate_says_all_smalltalk(context):
        return OutputScopeGateResult(bypassed=True, bypass_reason="gate_all_smalltalk", relevance=None)

    # Smalltalk bypass (local)
    if cfg.smalltalk_allowed and _is_smalltalk(llm_output, max_chars=cfg.smalltalk_max_chars):
        return OutputScopeGateResult(bypassed=True, bypass_reason="output_smalltalk", relevance=None)

    persona_corpus = build_persona_corpus(profile, answers)

    rel = compute_topic_relevance(
        user_text=llm_output,
        persona_corpus=persona_corpus,
        deny_threshold=cfg.min_output_score,
        caution_threshold=cfg.min_output_score * 2,
    )

    if cfg.bypass_on_empty_tokens and rel.reason == "empty_tokens":
        return OutputScopeGateResult(bypassed=True, bypass_reason="empty_tokens", relevance=None)

    return OutputScopeGateResult(bypassed=False, bypass_reason=None, relevance=rel)