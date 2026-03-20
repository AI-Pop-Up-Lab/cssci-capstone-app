from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.guardrails.pre.prompt_injection.config import DEFAULT_CONFIG, InjectionGateConfig
from app.guardrails.pre.prompt_injection.lexical import compute_injection_lexical


@dataclass(frozen=True)
class InjectionLexicalPrecheck:
    score: int
    is_suspicious: bool
    dangerous_terms: list[str]
    categories: list[str]
    matches_payload: list[dict[str, Any]]
    reason: str


def run_injection_lexical_precheck(
    *,
    user_text: str,
    cfg: InjectionGateConfig = DEFAULT_CONFIG,
    max_matches: int = 12,
) -> InjectionLexicalPrecheck:
    lex = compute_injection_lexical(user_text=user_text, threshold=cfg.lexical_threshold)

    matches_payload = [
        {
            "term_id": m.term_id,
            "category": m.category,
            "weight": m.weight,
            "pattern": m.pattern,
            "span": m.span,
            "snippet": m.snippet,
        }
        for m in lex.matches
    ][:max_matches]

    return InjectionLexicalPrecheck(
        score=lex.score,
        is_suspicious=lex.is_suspicious,
        dangerous_terms=lex.dangerous_terms,
        categories=lex.categories,
        matches_payload=matches_payload,
        reason=lex.reason,
    )