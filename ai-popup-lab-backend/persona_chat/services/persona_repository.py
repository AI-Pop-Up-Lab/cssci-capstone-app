from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from app.db.conn import get_persona_conn

# ============================================================
# Similarity helper (lightweight retrieval)
# ============================================================


def _sim(a: str, b: str) -> float:
    """Simple string similarity (0..1) using SequenceMatcher."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ============================================================
# Types
# ============================================================


@dataclass
class RetrievedAnswer:
    """A scored survey answer retrieved as context for answering."""
    question_id: str
    question_text: str
    answer_value: str | None
    answer_text: str
    wave: str
    confidence: float | None
    score: float


# ============================================================
# Persona/profile reads
# ============================================================


def get_persona_profile(persona_id: str, snapshot_id: str) -> dict[str, Any] | None:
    """
    Load persona profile JSON from persona.db.

    Source table:
      personas(profile_json)
    """
    with get_persona_conn() as conn:
        row = conn.execute(
            "SELECT profile_json FROM personas WHERE persona_id=? AND snapshot_id=?",
            (persona_id, snapshot_id),
        ).fetchone()

    if not row:
        return None

    return json.loads(row["profile_json"])


def list_personas(snapshot_id: str) -> list[dict[str, Any]]:
    """
    List personas for a snapshot.

    Returns:
      [{ persona_id, snapshot_id, display_name, profile }, ...]
    """
    with get_persona_conn() as conn:
        rows = conn.execute(
            "SELECT persona_id, snapshot_id, profile_json FROM personas WHERE snapshot_id=? ORDER BY persona_id",
            (snapshot_id,),
        ).fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        prof = json.loads(r["profile_json"])
        out.append(
            {
                "persona_id": r["persona_id"],
                "snapshot_id": r["snapshot_id"],
                "display_name": prof.get("display_name", r["persona_id"]),
                "profile": prof,
            }
        )
    return out


# ============================================================
# Survey question/answer reads
# ============================================================


def list_questions_for_persona(persona_id: str, snapshot_id: str) -> list[dict[str, Any]]:
    """
    List all question IDs/texts that this persona has answers for.

    Note:
    If you enforce "all personas answer all questions", then this becomes
    effectively "all questions in question_bank".
    """
    with get_persona_conn() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT qb.question_id, qb.question_text
            FROM survey_answers sa
            JOIN question_bank qb ON qb.question_id = sa.question_id
            WHERE sa.persona_id=? AND sa.snapshot_id=?
            ORDER BY qb.question_id
            """,
            (persona_id, snapshot_id),
        ).fetchall()

    return [{"question_id": r["question_id"], "question_text": r["question_text"]} for r in rows]


def get_answer_exact(persona_id: str, snapshot_id: str, question_id: str) -> list[dict[str, Any]]:
    """
    Get exact answer rows for a persona + question.

    Returns multiple rows if multiple waves exist.
    """
    with get_persona_conn() as conn:
        rows = conn.execute(
            """
            SELECT sa.question_id, qb.question_text, sa.answer_value, sa.answer_text, sa.wave, sa.confidence
            FROM survey_answers sa
            JOIN question_bank qb ON qb.question_id = sa.question_id
            WHERE sa.persona_id=? AND sa.snapshot_id=? AND sa.question_id=?
            ORDER BY sa.wave DESC
            """,
            (persona_id, snapshot_id, question_id),
        ).fetchall()

    return [
        {
            "question_id": r["question_id"],
            "question_text": r["question_text"],
            "answer_value": r["answer_value"],
            "answer_text": r["answer_text"],
            "wave": r["wave"],
            "confidence": r["confidence"],
        }
        for r in rows
    ]


def retrieve_relevant_answers(
    persona_id: str,
    snapshot_id: str,
    user_query: str,
    k: int = 4,
) -> list[RetrievedAnswer]:
    """
    Lightweight retrieval: rank persona answers by similarity to:
      - question_text
      - answer_text

    This is intentionally simple (no embeddings).
    """
    with get_persona_conn() as conn:
        rows = conn.execute(
            """
            SELECT sa.question_id, qb.question_text, sa.answer_value, sa.answer_text, sa.wave, sa.confidence
            FROM survey_answers sa
            JOIN question_bank qb ON qb.question_id = sa.question_id
            WHERE sa.persona_id=? AND sa.snapshot_id=?
            """,
            (persona_id, snapshot_id),
        ).fetchall()

    scored: list[RetrievedAnswer] = []
    for r in rows:
        qtext = r["question_text"]
        atext = r["answer_text"]
        score = max(_sim(user_query, qtext), _sim(user_query, atext))
        scored.append(
            RetrievedAnswer(
                question_id=r["question_id"],
                question_text=qtext,
                answer_value=r["answer_value"],
                answer_text=atext,
                wave=r["wave"],
                confidence=r["confidence"],
                score=score,
            )
        )

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:k]