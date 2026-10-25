"""
Building the system prompt: the shared rules in prompts/base_system.md plus one persona.

base_system.md contains two placeholders that are filled in here:
  {{PERSONA_FACTS}}    the five attributes from the persona file, as a short list
  {{PERSONA_PROFILE}}  the persona file's profile text
If a placeholder is missing from base_system.md, that part is added at the end instead,
so the persona can never silently disappear from the prompt.
"""

from functools import lru_cache
from pathlib import Path

from midterm_event_api import attributes
from midterm_event_api.personas import Persona, strip_comments

FACTS_PLACEHOLDER = "{{PERSONA_FACTS}}"
PROFILE_PLACEHOLDER = "{{PERSONA_PROFILE}}"


@lru_cache(maxsize=4)
def load_base_prompt(path: str) -> str:
    return strip_comments(Path(path).read_text(encoding="utf-8"))


def persona_facts(persona: Persona) -> str:
    return "\n".join(
        f"- {attributes.LABELS[name]}: {attributes.describe(name, persona.attributes[name])}"
        for name in attributes.ATTRIBUTES
    )


def build_system_prompt(persona: Persona, base_prompt: str) -> str:
    prompt = base_prompt
    for placeholder, content in (
        (FACTS_PLACEHOLDER, persona_facts(persona)),
        (PROFILE_PLACEHOLDER, persona.profile),
    ):
        if placeholder in prompt:
            prompt = prompt.replace(placeholder, content)
        else:
            prompt = f"{prompt}\n\n{content}"
    return prompt
