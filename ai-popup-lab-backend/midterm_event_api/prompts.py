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
EVENTS_PLACEHOLDER = "{{RECENT_EVENTS}}"


@lru_cache(maxsize=4)
def load_base_prompt(path: str) -> str:
    return strip_comments(Path(path).read_text(encoding="utf-8"))


def persona_facts(persona: Persona) -> str:
    return "\n".join(
        f"- {attributes.LABELS[name]}: {attributes.describe(name, persona.attributes[name])}"
        for name in attributes.ATTRIBUTES
    )


def format_recent_events(state: str | None = None, events_data: dict | None = None) -> str:
    """Format recent national and state events into a brief briefing if available."""
    if not events_data:
        return ""
    lines = []
    national = events_data.get("national", [])
    if national:
        lines.append("**National headlines leading up to today:**")
        for item in national:
            lines.append(f"- {item}")
    if state and "state" in events_data and state in events_data["state"]:
        state_events = events_data["state"][state]
        if state_events:
            lines.append(f"\n**Recent local/state news in {state}:**")
            for item in state_events:
                lines.append(f"- {item}")
    return "\n".join(lines).strip()


def build_system_prompt(persona: Persona, base_prompt: str, events_data: dict | None = None) -> str:
    prompt = base_prompt
    events_text = format_recent_events(persona.attributes.get("state"), events_data)

    for placeholder, content in (
        (FACTS_PLACEHOLDER, persona_facts(persona)),
        (PROFILE_PLACEHOLDER, persona.profile),
        (EVENTS_PLACEHOLDER, events_text),
    ):
        if placeholder in prompt:
            prompt = prompt.replace(placeholder, content)
        elif placeholder != EVENTS_PLACEHOLDER:
            prompt = f"{prompt}\n\n{content}"
    return prompt.strip()
