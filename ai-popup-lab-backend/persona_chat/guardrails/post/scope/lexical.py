from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TopicRelevance:
    user_score: float
    tier: str  # "deny" | "caution" | "allow"
    reason: str


_STOP = {
    "a", "an", "the", "and", "or", "but", "if", "then", "so",
    "to", "of", "in", "on", "at", "for", "from", "with", "by",
    "is", "are", "was", "were", "be", "been", "being",
    "i", "you", "he", "she", "it", "we", "they",
    "me", "my", "your", "his", "her", "our", "their",
}


def _normalize_tokens(text: str) -> set[str]:
    t = (text or "").lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    toks = [x for x in t.split() if x and x not in _STOP and len(x) >= 3]
    return set(toks)


def build_persona_corpus(profile: dict[str, Any], answers: list[dict[str, Any]]) -> str:
    """
    Build a cheap lexical corpus from persona profile + retrieved Q/A.
    Used by OutputScopeCheck to sanity-check drift.
    """
    parts: list[str] = []

    for v in (profile or {}).values():
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())

    for a in answers or []:
        qt = (a.get("question_text") or "").strip()
        at = (a.get("answer_text") or "").strip()
        if qt:
            parts.append(qt)
        if at:
            parts.append(at)

    return " ".join(parts).strip()


def compute_topic_relevance(
    *,
    user_text: str,
    persona_corpus: str,
    deny_threshold: float = 0.02,
    caution_threshold: float = 0.05,
) -> TopicRelevance:
    """
    Lightweight lexical overlap: thresholded Jaccard similarity.

    Intentionally NOT semantic. Cheap drift detector / enforcement fallback.
    """
    u = _normalize_tokens(user_text)
    p = _normalize_tokens(persona_corpus)

    if not u or not p:
        return TopicRelevance(user_score=0.0, tier="deny", reason="empty_tokens")

    inter = len(u & p)
    union = len(u | p)
    score = float(inter / union) if union else 0.0

    if score < deny_threshold:
        tier = "deny"
    elif score < caution_threshold:
        tier = "caution"
    else:
        tier = "allow"

    return TopicRelevance(user_score=score, tier=tier, reason="thresholded_jaccard")