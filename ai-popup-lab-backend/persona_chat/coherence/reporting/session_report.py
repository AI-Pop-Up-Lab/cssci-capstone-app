from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from app.guardrails.contract import GuardrailResult


REPORT_DIR = Path(__file__).resolve().parents[2] / "coherence_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SessionTurnReport:
    turn_index: int
    user_text: str
    assistant_output: str

    p2l_judge_binary: int | None = None
    p2l_score: float | None = None
    p2l_verdict: str | None = None
    p2l_violation_count: int = 0
    p2l_violations: list[dict[str, Any]] = field(default_factory=list)

    l2l_judge_binary: int | None = None
    l2l_score: float | None = None
    l2l_verdict: str | None = None
    l2l_contradiction_count: int = 0
    l2l_contradictions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SessionCoherenceReport:
    session_id: str
    persona_id: str | None
    snapshot_id: str | None
    created_at: str

    turn_count: int

    # Paper-aligned session metrics
    prompt_to_line_consistency: float | None
    line_to_line_consistency: float | None

    p2l_mean_score: float | None
    l2l_mean_score: float | None

    p2l_total_violations: int
    l2l_total_contradictions: int
    l2l_turns_with_contradictions: int

    p2l_violation_type_counts: dict[str, int]
    turns: list[SessionTurnReport]


def _safe_float(x: Any) -> float | None:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _extract_monitor_map(results: list[GuardrailResult]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in results:
        out[r.name] = r.details if isinstance(r.details, dict) else {}
    return out


def _mean(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _count_violation_types(turns: list[SessionTurnReport]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in turns:
        for v in t.p2l_violations:
            vt = str(v.get("type", "unknown"))
            counts[vt] = counts.get(vt, 0) + 1
    return counts


def _p2l_binary_from_turn(p2l: dict[str, Any]) -> int | None:
    """
    Paper formula needs J_LLM(P, r_t) in {0,1}.
    We derive it from verdict/violations:
      - PASS => 1
      - FAIL => 0
      - WARN => 0 if violations exist else None
    """
    verdict = str(p2l.get("verdict", "")).upper()
    violations = p2l.get("violations") or []

    if verdict == "PASS":
        return 1
    if verdict == "FAIL":
        return 0
    if verdict == "WARN":
        return 0 if violations else None
    return None


def _l2l_binary_from_turn(l2l: dict[str, Any]) -> int | None:
    """
    Paper formula uses min_{i<t} J_LLM(r_i, r_t).
    In your implementation, if contradictions were detected for the turn,
    that min consistency is effectively 0; otherwise 1.
    """
    contradictions = l2l.get("contradictions") or []
    verdict = str(l2l.get("verdict", "")).upper()

    if contradictions:
        return 0
    if verdict == "PASS":
        return 1
    if verdict == "FAIL":
        return 0
    return None


def _compute_prompt_to_line_consistency(turns: list[SessionTurnReport]) -> float | None:
    """
    Paper Eq. (1):
      C_prompt-to-line(R,P) = (1/T) * sum_t J_LLM(P, r_t)
    """
    vals = [t.p2l_judge_binary for t in turns if t.p2l_judge_binary is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _compute_line_to_line_consistency(turns: list[SessionTurnReport]) -> float | None:
    """
    Paper Eq. (2):
      C_line-to-line(R) = (1/(T-1)) * sum_{t=2..T} min_{i<t} J_LLM(r_i, r_t)

    Here we store per-turn l2l_judge_binary as that min value for the turn.
    We exclude the first turn because there is no prior assistant line.
    """
    vals = [
        t.l2l_judge_binary
        for t in turns
        if t.turn_index >= 2 and t.l2l_judge_binary is not None
    ]
    if not vals:
        return None
    return sum(vals) / len(vals)


def build_session_coherence_report(
    *,
    session_id: str,
    persona_id: str | None,
    snapshot_id: str | None,
    turn_records: list[dict[str, Any]],
) -> SessionCoherenceReport:
    turns: list[SessionTurnReport] = []

    for rec in turn_records:
        turn_index = int(rec["turn_index"])
        user_text = str(rec.get("user_text", ""))
        assistant_output = str(rec.get("assistant_output", ""))
        monitor_results = rec.get("monitor_results", [])

        by_name = _extract_monitor_map(monitor_results)

        p2l = by_name.get("persona_prompt_to_line", {})
        l2l = by_name.get("persona_line_to_line", {})

        p2l_violations = p2l.get("violations") or []
        l2l_contradictions = l2l.get("contradictions") or []

        turns.append(
            SessionTurnReport(
                turn_index=turn_index,
                user_text=user_text,
                assistant_output=assistant_output,
                p2l_judge_binary=_p2l_binary_from_turn(p2l),
                p2l_score=_safe_float(p2l.get("coherence_score")),
                p2l_verdict=p2l.get("verdict"),
                p2l_violation_count=len(p2l_violations),
                p2l_violations=p2l_violations,
                l2l_judge_binary=_l2l_binary_from_turn(l2l),
                l2l_score=_safe_float(l2l.get("consistency_score")),
                l2l_verdict=l2l.get("verdict"),
                l2l_contradiction_count=len(l2l_contradictions),
                l2l_contradictions=l2l_contradictions,
            )
        )

    return SessionCoherenceReport(
        session_id=session_id,
        persona_id=persona_id,
        snapshot_id=snapshot_id,
        created_at=datetime.now(UTC).isoformat(),
        turn_count=len(turns),
        prompt_to_line_consistency=_compute_prompt_to_line_consistency(turns),
        line_to_line_consistency=_compute_line_to_line_consistency(turns),
        p2l_mean_score=_mean([t.p2l_score for t in turns]),
        l2l_mean_score=_mean([t.l2l_score for t in turns]),
        p2l_total_violations=sum(t.p2l_violation_count for t in turns),
        l2l_total_contradictions=sum(t.l2l_contradiction_count for t in turns),
        l2l_turns_with_contradictions=sum(1 for t in turns if t.l2l_contradiction_count > 0),
        p2l_violation_type_counts=_count_violation_types(turns),
        turns=turns,
    )


def save_session_report_json(report: SessionCoherenceReport) -> Path:
    path = REPORT_DIR / f"{report.session_id}_coherence_report.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(asdict(report), f, ensure_ascii=False, indent=2)
    return path


def save_session_report_csv(report: SessionCoherenceReport) -> Path:
    path = REPORT_DIR / f"{report.session_id}_coherence_turns.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "session_id",
                "persona_id",
                "snapshot_id",
                "turn_index",
                "p2l_judge_binary",
                "p2l_score",
                "p2l_verdict",
                "p2l_violation_count",
                "l2l_judge_binary",
                "l2l_score",
                "l2l_verdict",
                "l2l_contradiction_count",
            ],
        )
        writer.writeheader()
        for t in report.turns:
            writer.writerow(
                {
                    "session_id": report.session_id,
                    "persona_id": report.persona_id,
                    "snapshot_id": report.snapshot_id,
                    "turn_index": t.turn_index,
                    "p2l_judge_binary": t.p2l_judge_binary,
                    "p2l_score": t.p2l_score,
                    "p2l_verdict": t.p2l_verdict,
                    "p2l_violation_count": t.p2l_violation_count,
                    "l2l_judge_binary": t.l2l_judge_binary,
                    "l2l_score": t.l2l_score,
                    "l2l_verdict": t.l2l_verdict,
                    "l2l_contradiction_count": t.l2l_contradiction_count,
                }
            )
    return path
