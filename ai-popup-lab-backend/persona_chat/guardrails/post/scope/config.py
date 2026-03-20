from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TopicGateConfig:
    """
    POST scope/scope enforcement config (mirrors PRE scope gate config style).

    Even though post enforcement is lexical (not LLM), we keep the same config pattern:
    - one config object
    - deterministic thresholds
    - simple knobs for bypass behavior
    """
    # Core threshold: output must overlap persona corpus at least this much
    min_output_score: float = 0.01

    # If scorer returns "empty_tokens", do we bypass (treat as ok)?
    bypass_on_empty_tokens: bool = True

    # Smalltalk bypass: lexical overlap is meaningless for greetings
    smalltalk_allowed: bool = True
    smalltalk_max_chars: int = 40

    # Operational/provider error bypass
    bypass_provider_errors: bool = True


DEFAULT_CONFIG = TopicGateConfig()