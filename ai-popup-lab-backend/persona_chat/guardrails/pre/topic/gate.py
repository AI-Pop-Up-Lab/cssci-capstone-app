from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.guardrails.manager import orchestrate_combined_validation, CombinedValidatorResult


@dataclass(frozen=True)
class GateMessageResult:
    combined: CombinedValidatorResult


async def llm_gate_message(
    *,
    provider: Any,
    user_text: str,
    persona_id: str,
    snapshot_id: str,
    profile: dict[str, Any],
    answers: list[dict[str, Any]],
    suggested_questions: list[Any],
) -> GateMessageResult:
    combined = await orchestrate_combined_validation(
        provider=provider,
        user_text=user_text,
        persona_id=persona_id,
        snapshot_id=snapshot_id,
        profile=profile,
        answers=answers,
        suggested_questions=suggested_questions,
    )
    return GateMessageResult(combined=combined)