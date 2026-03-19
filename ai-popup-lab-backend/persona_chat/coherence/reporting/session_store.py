from __future__ import annotations

from typing import Any

from app.guardrails.contract import GuardrailResult


_SESSION_TURNS: dict[str, list[dict[str, Any]]] = {}


def append_turn_result(
    *,
    session_id: str,
    turn_index: int,
    user_text: str,
    assistant_output: str,
    monitor_results: list[GuardrailResult],
) -> None:
    _SESSION_TURNS.setdefault(session_id, []).append(
        {
            "turn_index": turn_index,
            "user_text": user_text,
            "assistant_output": assistant_output,
            "monitor_results": monitor_results,
        }
    )


def get_session_turns(session_id: str) -> list[dict[str, Any]]:
    return list(_SESSION_TURNS.get(session_id, []))


def clear_session_turns(session_id: str) -> None:
    _SESSION_TURNS.pop(session_id, None)