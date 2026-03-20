from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonaL2LConfig:
    enable: bool = True
    strict_json: bool = True
    max_contradictions: int = 10

    # Placeholder threshold
    min_consistency_warn: float = 0.80


DEFAULT_CONFIG = PersonaL2LConfig()