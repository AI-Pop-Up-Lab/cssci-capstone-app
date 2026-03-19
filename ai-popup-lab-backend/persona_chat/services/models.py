from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SessionInfo:
    session_id: str
    persona_id: str
    snapshot_id: str
    model_version: str


@dataclass(frozen=True)
class GroundingBundle:
    persona_id: str
    snapshot_id: str
    profile: dict[str, Any]
    answers: list[dict[str, Any]]
    suggested_questions: list[Any]


@dataclass(frozen=True)
class LlmAnswerBundle:
    content: str
    citations: list[Any]
    safety: dict[str, Any] | None