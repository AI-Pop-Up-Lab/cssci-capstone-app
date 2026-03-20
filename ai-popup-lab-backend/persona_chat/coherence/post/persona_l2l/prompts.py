from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonaL2LJudgeConfig:
    strict_json: bool = True
    max_contradictions: int = 10


DEFAULT_JUDGE_CONFIG = PersonaL2LJudgeConfig()


def build_persona_l2l_system_prompt(cfg: PersonaL2LJudgeConfig = DEFAULT_JUDGE_CONFIG) -> str:
    strict = (
        "You MUST output valid JSON only. Do not wrap in markdown fences."
        if cfg.strict_json
        else "Output JSON."
    )

    return f"""You are a contradiction judge for a persona chat session.

{strict}

You receive JSON with:
- session_messages: ordered list of turns (user/assistant), earlier -> later
- assistant_output: the new draft assistant answer
- user_text: the current user message (for context)

Task:
Evaluate LINE-TO-LINE coherence: does assistant_output contradict earlier statements made by the assistant in this session?

Define "contradiction":
- The assistant asserts X earlier and now asserts NOT X (or mutually exclusive facts),
  especially about persona identity, demographics, preferences, or claimed personal history.
- If the earlier statement was uncertain/conditional, only flag if the new statement is clearly incompatible.

Return JSON schema:
{{
  "verdict": "PASS|WARN|FAIL",
  "confidence": 0.0,
  "contradictions": [
    {{
      "prior_turn_index": 0,
      "prior_claim": "...",
      "new_claim": "...",
      "explanation": "why these conflict",
      "severity": "low|medium|high"
    }}
  ],
  "score": {{
    "consistency_score": 0.0,
    "method_note": "brief note"
  }},
  "debug": {{
    "notes": "<optional>"
  }}
}}

Constraints:
- Limit to at most {cfg.max_contradictions} contradictions.
"""