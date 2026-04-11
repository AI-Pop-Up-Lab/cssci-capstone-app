"""Stylometric profile generation and judge-guidance preparation."""

import json

from _persona_chat.guardrailed.schemas import StylometricSignal
from _persona_chat.utils import run_chat_completion


STYLOMETRY_SYS_PROMPT = (
    "You analyze a persona biography and infer a likely linguistic profile for future dialogue.\n"
    "- Focus on how the persona is likely to speak, explain, and frame ideas.\n"
    "- Use the biography as the main evidence source.\n"
    "- Age, education, and work can inform the judgment, but they must never be used as crude shortcuts.\n"
    "- Avoid stereotypes about class, education, occupation, age, or intelligence.\n"
    "- Infer communication style, not human worth.\n"
    "- Prefer subtle, believable variation over exaggerated personas.\n"
    "- Return JSON only.\n"
    "- The JSON must contain these keys:\n"
    '  "register", "sentence_style", "abstraction_level", "vocabulary_level",\n'
    '  "hedging_style", "confidence_style", "warmth_style", "explanation_style",\n'
    '  "reasoning_style", "profile_summary", "evidence"\n'
)


STYLOMETRY_JUDGE_SUBPROMPT = """
Stylometric evaluation:
- Use the stylometric profile as evidence for how this persona is likely to sound.
- Treat this as a communication-style signal, not as a measure of intelligence or worth.
- Keep the style subtle and believable.
- Use it to help decide register, sentence shape, abstraction level, vocabulary level, and explanation style.
- Do not let it override epistemic limits; it should shape form, not falsely expand knowledge.
- Treat the stylometric profile as the baseline speaking stance.
- Then modulate confidence and hedging based on topic fit:
  - if the topic strongly matches the persona's work, study, hobbies, or lived experience, confidence may rise and hedging may drop somewhat
  - if the topic is far from the persona's profile, confidence should drop and hedging should rise
- Keep these shifts believable and proportional rather than dramatic.
""".strip()


def _build_generation_user_prompt(*, persona_biography: str, persona_details: dict, persona_country: str) -> str:
    """Build the profile-generation prompt from biography and structured details."""
    normalized_details = json.dumps(
        {
            "country": persona_country,
            "age_group": persona_details.get("age_group"),
            "gender": persona_details.get("gender"),
            "education": persona_details.get("education"),
            "municipality": persona_details.get("municipality"),
            "vote_2030": persona_details.get("vote_2030"),
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

    return (
        "Infer a reusable linguistic profile for this persona.\n\n"
        "Persona details:\n"
        f"{normalized_details}\n\n"
        "Persona biography:\n"
        f"{persona_biography}\n\n"
        "Output constraints:\n"
        '- "register": plain | everyday | polished | articulate\n'
        '- "sentence_style": short | mixed | long\n'
        '- "abstraction_level": concrete | mixed | abstract\n'
        '- "vocabulary_level": simple | moderate | advanced\n'
        '- "hedging_style": low | medium | high\n'
        '- "confidence_style": tentative | balanced | assured\n'
        '- "warmth_style": reserved | warm | expressive\n'
        '- "explanation_style": example_first | balanced | concept_first\n'
        '- "reasoning_style": practical | reflective | analytical | blended\n'
        '- "profile_summary": 2-4 sentences\n'
        '- "evidence": short array of direct evidence phrases from the biography\n'
    )


def generate_stylometric_profile(*, persona_biography: str, persona_details: dict, persona_country: str) -> dict:
    """Generate a structured stylometric profile from the biography and persona details."""
    raw_response = run_chat_completion(
        messages=[
            {"role": "system", "content": STYLOMETRY_SYS_PROMPT},
            {
                "role": "user",
                "content": _build_generation_user_prompt(
                    persona_biography=persona_biography,
                    persona_details=persona_details,
                    persona_country=persona_country,
                ),
            },
        ],
        temperature=0.2,
        json_mode=True,
    )

    profile = json.loads(raw_response)
    return {
        "register": profile.get("register", "everyday"),
        "sentence_style": profile.get("sentence_style", "mixed"),
        "abstraction_level": profile.get("abstraction_level", "mixed"),
        "vocabulary_level": profile.get("vocabulary_level", "moderate"),
        "hedging_style": profile.get("hedging_style", "medium"),
        "confidence_style": profile.get("confidence_style", "balanced"),
        "warmth_style": profile.get("warmth_style", "warm"),
        "explanation_style": profile.get("explanation_style", "balanced"),
        "reasoning_style": profile.get("reasoning_style", "blended"),
        "profile_summary": profile.get(
            "profile_summary",
            "The persona speaks in an everyday, grounded way with a balance of warmth and practical explanation.",
        ),
        "evidence": profile.get("evidence", []),
    }


def prepare_stylometric_signal(*, stylometric_profile: dict) -> StylometricSignal:
    """Build the stylometric instructions that will be injected into the judge prompt."""
    judge_prompt = (
        f"{STYLOMETRY_JUDGE_SUBPROMPT}\n\n"
        "Stylometric profile context:\n"
        f"{json.dumps(stylometric_profile, ensure_ascii=False, indent=2)}"
    )
    return StylometricSignal(
        summary=stylometric_profile.get(
            "profile_summary",
            "Stylometric guidance is based on the persona's likely communication style.",
        ),
        judge_prompt=judge_prompt,
    )
