from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.utils import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class InjectionMatch:
    term_id: str
    category: str
    weight: int
    pattern: str
    span: tuple[int, int]
    snippet: str


@dataclass(frozen=True)
class InjectionLexicalResult:
    is_suspicious: bool
    score: int  # 0..100
    dangerous_terms: list[str]
    categories: list[str]
    matches: list[InjectionMatch]
    reason: str


def _project_root() -> Path:
    # app/guardrails/pre/prompt_injection/lexical.py -> project root
    return Path(__file__).resolve().parents[4]


def _default_terms_path() -> Path:
    app_path = _project_root() / "app" / "guardrails" / "pre" / "prompt_injection" / "injection_terms.json"
    if app_path.exists():
        return app_path

    return _project_root() / "persona_chat" / "guardrails" / "pre" / "prompt_injection" / "injection_terms.json"


def _load_terms(path: Path) -> dict[str, Any]:
    """
    Fail-safe loader:
    - Never crash the app on missing/invalid JSON
    - Log a clear error and return empty terms
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        log.error("[INJECTION_LEXICAL] terms_file_missing path=%s", str(path))
        return {"version": 0, "max_matches_per_term": 0, "terms": []}
    except Exception as e:
        log.error("[INJECTION_LEXICAL] terms_file_read_error path=%s err=%s", str(path), str(e))
        return {"version": 0, "max_matches_per_term": 0, "terms": []}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("[INJECTION_LEXICAL] terms_file_invalid_json path=%s err=%s", str(path), str(e))
        return {"version": 0, "max_matches_per_term": 0, "terms": []}

    if not isinstance(data, dict) or "terms" not in data:
        log.error("[INJECTION_LEXICAL] terms_file_invalid_schema path=%s", str(path))
        return {"version": 0, "max_matches_per_term": 0, "terms": []}

    return data


def _safe_snippet(text: str, start: int, end: int, pad: int = 28) -> str:
    s = max(0, start - pad)
    e = min(len(text), end + pad)
    return text[s:e].replace("\n", " ").strip()


def _cap(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def compute_injection_lexical(
    *,
    user_text: str,
    terms_path: Path | None = None,
    threshold: int = 35,
) -> InjectionLexicalResult:
    text = (user_text or "").strip()
    if not text:
        log.info("[INJECTION_LEXICAL] empty_user_text -> allow")
        return InjectionLexicalResult(
            is_suspicious=False,
            score=0,
            dangerous_terms=[],
            categories=[],
            matches=[],
            reason="empty_text",
        )

    path = terms_path or _default_terms_path()
    lib = _load_terms(path)

    max_matches_per_term = int(lib.get("max_matches_per_term", 3))
    terms = lib.get("terms") or []

    if not isinstance(terms, list) or not terms:
        log.warning("[INJECTION_LEXICAL] no_terms_loaded path=%s -> allow", str(path))
        return InjectionLexicalResult(
            is_suspicious=False,
            score=0,
            dangerous_terms=[],
            categories=[],
            matches=[],
            reason="empty_terms_library",
        )

    all_matches: list[InjectionMatch] = []
    raw_score = 0

    for t in terms:
        if not isinstance(t, dict):
            continue

        term_id = str(t.get("id") or "").strip()
        if not term_id:
            continue

        category = str(t.get("category") or "unknown").strip()
        weight = int(t.get("weight") or 0)
        patterns = t.get("patterns") or []
        if not isinstance(patterns, list) or not patterns:
            continue

        per_term = 0
        for pat in patterns:
            if per_term >= max_matches_per_term:
                break

            try:
                rx = re.compile(str(pat), re.IGNORECASE | re.DOTALL)
            except re.error:
                log.warning("[INJECTION_LEXICAL] invalid_regex term_id=%s pattern=%r", term_id, pat)
                continue

            for m in rx.finditer(text):
                if per_term >= max_matches_per_term:
                    break

                span = (m.start(), m.end())
                snippet = _safe_snippet(text, span[0], span[1])

                all_matches.append(
                    InjectionMatch(
                        term_id=term_id,
                        category=category,
                        weight=weight,
                        pattern=str(pat),
                        span=span,
                        snippet=snippet,
                    )
                )
                per_term += 1
                raw_score += weight

    length_factor = 1.0
    if len(text) > 800:
        length_factor = 0.85
    if len(text) > 2000:
        length_factor = 0.70

    score = _cap(int(raw_score * length_factor), 0, 100)
    dangerous_terms = sorted({m.term_id for m in all_matches})
    categories = sorted({m.category for m in all_matches})
    is_suspicious = score >= threshold

    if not all_matches:
        log.info("[INJECTION_LEXICAL] no_matches score=%s threshold=%s suspicious=%s", score, threshold, is_suspicious)
    else:
        log.warning(
            "[INJECTION_LEXICAL] matched score=%s threshold=%s suspicious=%s terms=%s categories=%s matches=%s",
            score,
            threshold,
            is_suspicious,
            dangerous_terms,
            categories,
            len(all_matches),
        )
        for i, mm in enumerate(all_matches[:6], 1):
            log.warning(
                "[INJECTION_LEXICAL] match_%02d term=%s cat=%s weight=%s snippet=%r",
                i,
                mm.term_id,
                mm.category,
                mm.weight,
                mm.snippet,
            )

    return InjectionLexicalResult(
        is_suspicious=is_suspicious,
        score=score,
        dangerous_terms=dangerous_terms,
        categories=categories,
        matches=all_matches,
        reason="matched_terms" if all_matches else "no_matches",
    )
