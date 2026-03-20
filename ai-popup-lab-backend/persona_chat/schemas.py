from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Literal


class PersonaSummary(BaseModel):
    persona_id: str
    snapshot_id: str
    display_name: str
    profile: dict[str, Any]


class StoredAnswer(BaseModel):
    question_id: str
    question_text: str
    answer_value: str | None = None
    answer_text: str
    wave: str
    confidence: float | None = None


class ChatSessionCreate(BaseModel):
    persona_id: str
    snapshot_id: str


class ChatSessionOut(BaseModel):
    session_id: str
    persona_id: str
    snapshot_id: str
    model_version: str


class ChatMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class Citation(BaseModel):
    kind: Literal["profile", "survey_answer"]
    key: str  # profile field name OR question_id
    wave: str | None = None


class Trace(BaseModel):
    persona_id: str
    snapshot_id: str
    model_version: str
    retrieved_profile_fields: list[str]
    retrieved_answers: list[dict[str, Any]]
    checks: dict[str, Any]
    safety: dict[str, Any]


class ChatMessageOut(BaseModel):
    role: Literal["assistant"]
    content: str
    citations: list[Citation]
    trace_id: str
