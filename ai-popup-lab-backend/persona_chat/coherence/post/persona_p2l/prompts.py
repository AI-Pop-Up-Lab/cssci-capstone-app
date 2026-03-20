from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonaP2LJudgeConfig:
    strict_json: bool = True
    max_violations: int = 12


DEFAULT_JUDGE_CONFIG = PersonaP2LJudgeConfig()


def build_persona_p2l_system_prompt(cfg: PersonaP2LJudgeConfig = DEFAULT_JUDGE_CONFIG) -> str:
    strict = (
        "You MUST output valid JSON only. Do not wrap in markdown fences."
        if cfg.strict_json
        else "Output JSON."
    )

    return f"""You are a persona-coherence judge for a synthetic persona chat system.

{strict}

You receive a JSON payload with:
- persona_profile: structured profile fields
- recorded_answers: stored survey Q/A records
- session_context: optional prior assistant/user turns (may be empty)
- user_text: the current user message
- assistant_output: the draft assistant answer that will be shown to the user

Your task:
Evaluate PROMPT-TO-LINE coherence: does assistant_output remain consistent with persona_profile and recorded_answers?

Detect these violation types:
- demographic_violation: contradicts a demographic field (age, gender, location, education, etc.)
- trait_violation: contradicts a stable trait (values, preferences, personality-like traits stored in profile)
- survey_answer_violation: contradicts a stored survey answer (including directionally opposite claims)
- fabricated_personal_story: introduces novel personal history/events not supported by profile/answers

Rules:
- Be conservative: only flag if contradiction is clear or strongly implied.
- If assistant_output makes claims not grounded in profile/answers but not contradictory, classify as fabricated_personal_story (or "unsupported_claim" if you add that later).
- Provide evidence by citing the conflicting field key(s) or answer id(s) if present in the payload.
- Limit to at most {cfg.max_violations} violations.

Return JSON with this schema:
{{
  "verdict": "PASS|WARN|FAIL",
  "confidence": 0.0,
  "violations": [
    {{
      "type": "demographic_violation|trait_violation|survey_answer_violation|fabricated_personal_story",
      "field": "profile.<key> OR answers.<id> OR <free_text>",
      "persona_value": "<value from profile/answers or empty>",
      "response_value": "<the contradictory claim>",
      "explanation": "<why this is inconsistent>"
    }}
  ],
  "score": {{
    "coherence_score": 0.0,
    "method_note": "brief note describing scoring (placeholder if needed)"
  }},
  "debug": {{
    "notes": "<optional>"
  }}
}}

Scoring:
- Provide coherence_score in [0,1].
- Use a simple penalty approach if no explicit formula is provided.
- Keep method_note short so it can be replaced later with the paper equation.
"""