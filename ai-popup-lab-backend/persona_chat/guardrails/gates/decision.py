"""
app/guardrails/gates/decision.py

============================================================
PRE-GATE DECISION CONTRACT
============================================================

This module defines the shared dataclass contract for the PRE-LLM
combined validator decision.

Why this exists
---------------
Both:
- app/guardrails/manager.py (pipeline entrypoint)
and
- module mappers (scope/mapper.py, prompt_injection/mapper.py)

need this type.

Putting it here prevents cross-directional imports where modules
import the manager.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PreGateDecision:
    injection_verdict: str
    injection_action: str
    injection_confidence: float
    injection_reason: str | None
    injection_signals: dict[str, bool]
    injection_lexical_score: int
    injection_matches: list[dict[str, Any]]

    topic_items: list[dict[str, Any]]
    topic_overall_tier: str
    topic_overall_action: str

    final_action: str
    final_reason: str | None

    user_for_llm: str
    debug: dict[str, Any]