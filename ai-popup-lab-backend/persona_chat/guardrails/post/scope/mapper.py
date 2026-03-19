from __future__ import annotations

from typing import Any

from app.guardrails.contract import GuardrailResult
from app.guardrails.post.scope.lexical import TopicRelevance


def map_relevance_to_guardrail_result(
    *,
    name: str,
    relevance: TopicRelevance,
    min_output_score: float,
) -> GuardrailResult:
    ok = relevance.user_score >= min_output_score
    return GuardrailResult(
        ok=ok,
        name=name,
        details={
            "output_score": relevance.user_score,
            "tier": relevance.tier,
            "reason": relevance.reason,
            "min_output_score": min_output_score,
        },
    )