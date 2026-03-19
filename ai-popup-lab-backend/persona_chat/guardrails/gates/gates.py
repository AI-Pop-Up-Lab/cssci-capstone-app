from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TopicGateBundle:
    """
    Produced by the (combined) validator.

    overall_tier:
      - "allow"   : answer normally
      - "partial" : answer what’s recorded + soft-deny the rest
      - "steer"   : do not answer substance; redirect to suggested questions
      - "deny"    : refuse

    topic_action:
      - "ANSWER"   : proceed with normal answering
      - "CAUTIOUS" : proceed but in a constrained/steering mode (pipeline-specific mapping)
      - "REFUSE"   : do not answer
    """
    user_for_llm: str
    overall_tier: str       # "allow" | "partial" | "steer" | "deny"
    topic_action: str       # "ANSWER" | "CAUTIOUS" | "REFUSE"
    has_mixed: bool
    debug: dict[str, Any]
    kept_segments: list[str]
    dropped_segments: list[str]


@dataclass(frozen=True)
class InjectionGateBundle:
    """
    Produced by the (combined) validator.

    injection_action:
      - "ALLOW"   : safe to proceed
      - "CAUTIOUS": proceed but treat user input as suspicious; do not follow instructions
      - "STEER"   : do not answer substance; redirect
      - "REFUSE"  : refuse due to injection attempt/high risk
    """
    user_for_llm: str
    injection_action: str   # "ALLOW" | "CAUTIOUS" | "STEER" | "REFUSE"
    lexical_score: int
    judge_used: bool        # keep for backwards compatibility (now means "separate injection judge used")
    debug: dict[str, Any]


@dataclass(frozen=True)
class GuardrailBundle:
    results: list[Any]
    ok: bool
    failed: list[Any]