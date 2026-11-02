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
    lines = []
    if persona.display_name and not persona.display_name.startswith("Persona "):
        lines.append(f"- Name: {persona.display_name}")
    lines.extend(
        f"- {attributes.LABELS[name]}: {attributes.describe(name, persona.attributes[name])}"
        for name in attributes.ATTRIBUTES
    )
    return "\n".join(lines)


def format_recent_events(state: str | None = None, events_data: dict | None = None) -> str:
    """Format recent national context, salient events, and persona media diet points."""
    if not events_data:
        return ""
    sections = []

    # 1. 2025-2026 Macro National Context & Headlines
    context = events_data.get("national_context")
    if isinstance(context, dict):
        lines = ["National context & developments (2025-2026):"]
        titles = {
            "administration_and_governance": "Administration & Governance",
            "foreign_affairs_and_security": "Foreign Affairs & Security",
            "economy_and_cost_of_living": "Economy & Cost of Living",
            "technology_and_society": "Technology & Society",
            "technology_energy_and_society": "Technology, Energy & Society",
            "election_week_headlines": "Major Headlines This Week",
        }
        for cat, items in context.items():
            if items:
                label = titles.get(cat, cat.replace("_", " ").title())
                lines.append(f"• {label}:")
                for item in items:
                    lines.append(f"  - {item}")
        sections.append("\n".join(lines))
    elif isinstance(context, list) and context:
        sections.append("National context:\n" + "\n".join(f"- {item}" for item in context))

    # 2. State-Specific Highlights
    state_highlights = events_data.get("state_highlights") or events_data.get("state", {})
    if state and isinstance(state_highlights, dict) and state in state_highlights:
        state_events = state_highlights[state]
        if state_events:
            sections.append(f"Recent state news & local ballot measures in {state}:\n" + "\n".join(f"- {item}" for item in state_events))

    # 3. Individual Persona Media Diet Memory (from GDELT digest)
    media_points = events_data.get("media_diet_points") or events_data.get("national")
    # if events_data["national"] was directly passed from old chat.py
    if media_points and not context:
        sections.append("Recent news you personally noticed:\n" + "\n".join(f"- {item}" for item in media_points))
    elif media_points and context:
        sections.append("Stories you personally noticed in the outlets you follow:\n" + "\n".join(f"- {item}" for item in media_points))

    return "\n\n".join(sections).strip()


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
