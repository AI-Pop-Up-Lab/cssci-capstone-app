from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class PersonaP2LConfig:
    """
    Prompt-to-line coherence config.

    This is a POST monitor config (monitor-only).
    It checks whether the assistant output is consistent with:
      - persona profile
      - stored survey answers
    """
    enable: bool = True

    # Judge behavior knobs
    strict_json: bool = True
    max_violations: int = 12

    # Scoring knobs (placeholder — wire your paper equation here)
    # You can replace this with the exact paper formula later.
    min_score_warn: float = 0.75  # warn if score < this
    fabricated_story_penalty: float = 0.25
    hard_violation_penalty: float = 0.15


DEFAULT_CONFIG = PersonaP2LConfig()