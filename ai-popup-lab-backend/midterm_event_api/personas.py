"""
Loading, validating and matching persona files.

Each persona is one markdown file in `personas/`:

    ---
    gender: Female
    age_group: 43-47
    education: Post-grad
    state: FL
    race: White
    ---
    You are ... (the persona profile, which becomes part of the system prompt)

The filename (without .md) is the persona's ID. Files starting with "_" (like _TEMPLATE.md)
are skipped. Full format: PERSONA_GUIDE.md.

A broken file is skipped and logged rather than crashing the API, because the same API also
serves the rest of the website. Run `python -m midterm_event_api.validate_personas` to see
every problem before deploying.
"""

import logging
import random
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from midterm_event_api import attributes
from midterm_event_api.config import get_settings

logger = logging.getLogger(__name__)

ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
FRONTMATTER_PATTERN = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)(.*)\Z", re.DOTALL)
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)

# profiles are sent with every message, so very long ones cost more and slow replies down
LONG_PROFILE_CHARS = 6000

# frontmatter keys with a special meaning; anything else is kept in `extra`
RESERVED_KEYS = {"id", "display_name", *attributes.ATTRIBUTES}


class PersonaFileError(ValueError):
    pass


@dataclass(frozen=True)
class Persona:
    id: str
    display_name: str
    attributes: dict
    # any other frontmatter fields, passed through to the frontend untouched
    extra: dict
    # the markdown body: goes into the system prompt, never sent to the frontend
    profile: str
    source_file: str

    def public(self) -> dict:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "attributes": dict(self.attributes),
            "extra": dict(self.extra),
        }


@dataclass
class LoadResult:
    personas: dict = field(default_factory=dict)
    # "filename: what's wrong" for every file that was skipped
    problems: list = field(default_factory=list)
    # "filename: what to look at" for files that loaded but might need a second look
    warnings: list = field(default_factory=list)


def strip_comments(text: str) -> str:
    """Remove <!-- ... --> comments, so templates can carry notes that never reach the model."""
    return HTML_COMMENT_PATTERN.sub("", text).strip()


def _default_display_name(persona_id: str) -> str:
    # "us_0042" -> "Persona 42", matching how the old chat labelled personas
    digits = re.findall(r"\d+", persona_id)
    return f"Persona {int(digits[-1])}" if digits else persona_id


def parse_persona_text(text: str, persona_id: str, source_file: str = "") -> Persona:
    """Parse one persona file's contents. Raises PersonaFileError explaining what's wrong."""
    if not ID_PATTERN.match(persona_id):
        raise PersonaFileError(
            "the filename may only contain letters, numbers, '_' and '-' (e.g. us_0042.md)"
        )

    # tolerate files saved on Windows or with a byte-order mark
    text = text.lstrip("﻿").replace("\r\n", "\n")

    found = FRONTMATTER_PATTERN.match(text)
    if not found:
        raise PersonaFileError(
            "the file must start with a '---' line, then the attributes, then another '---' line"
        )
    frontmatter_text, body = found.groups()

    try:
        frontmatter = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as exc:
        raise PersonaFileError(f"the attributes between the '---' lines aren't valid YAML: {exc}") from exc
    if not isinstance(frontmatter, dict):
        raise PersonaFileError("the attributes between the '---' lines must be 'key: value' lines")

    if "id" in frontmatter and str(frontmatter["id"]) != persona_id:
        raise PersonaFileError(
            f"'id: {frontmatter['id']}' doesn't match the filename '{persona_id}'. "
            "The filename is the ID, so you can just remove the id line"
        )

    missing = [name for name in attributes.ATTRIBUTES if frontmatter.get(name) in (None, "")]
    if missing:
        raise PersonaFileError(f"missing required attribute(s): {', '.join(missing)}")

    values = {}
    for name in attributes.ATTRIBUTES:
        try:
            values[name] = attributes.normalize(name, frontmatter[name])
        except ValueError as exc:
            raise PersonaFileError(str(exc)) from exc

    profile = strip_comments(body)
    if not profile:
        raise PersonaFileError("the profile text below the second '---' line is empty")

    display_name = frontmatter.get("display_name")
    display_name = str(display_name).strip() if display_name else _default_display_name(persona_id)

    extra = {key: value for key, value in frontmatter.items() if key not in RESERVED_KEYS}

    return Persona(
        id=persona_id,
        display_name=display_name,
        attributes=values,
        extra=extra,
        profile=profile,
        source_file=source_file,
    )


def load_personas(directory: Path) -> LoadResult:
    result = LoadResult()
    directory = Path(directory)

    if not directory.is_dir():
        result.problems.append(f"{directory}: personas folder not found")
        return result

    for path in sorted(directory.glob("*.md")):
        if path.name.startswith(("_", ".")):
            continue
        try:
            persona = parse_persona_text(path.read_text(encoding="utf-8"), path.stem, path.name)
        except (PersonaFileError, UnicodeDecodeError) as exc:
            result.problems.append(f"{path.name}: {exc}")
            continue

        result.personas[persona.id] = persona
        if len(persona.profile) > LONG_PROFILE_CHARS:
            result.warnings.append(
                f"{path.name}: profile is {len(persona.profile)} characters; "
                f"consider keeping it under {LONG_PROFILE_CHARS}"
            )

    return result


@dataclass(frozen=True)
class MatchResult:
    persona: Persona
    exact: bool
    matched_attributes: list
    unmatched_attributes: list
    # how many personas were equally good matches (one of them was picked at random)
    candidates: int


class PersonaStore:
    def __init__(self, load_result: LoadResult):
        self.personas = load_result.personas
        self.problems = load_result.problems
        self.warnings = load_result.warnings

    def get(self, persona_id: str) -> Persona | None:
        return self.personas.get(persona_id)

    def all(self) -> list:
        return [self.personas[key] for key in sorted(self.personas)]

    def match(self, filters: dict, rng: random.Random | None = None) -> MatchResult | None:
        """
        Pick the persona that best fits the visitor's choices.

        `filters` maps attribute -> canonical value, leaving out attributes set to "all".
        With ~500 personas most full combinations of the five attributes have no exact
        match, so this ranks personas by:
          1. how many chosen attributes match exactly, then
          2. how close age group and education are (e.g. 48-52 is closer to 43-47 than 83+)
        and picks randomly among the best, so visitors choosing the same options can get
        different personas.
        """
        if not self.personas:
            return None
        rng = rng or random

        def score(persona: Persona):
            exact = sum(persona.attributes[name] == value for name, value in filters.items())
            distance = 0
            for name in attributes.ORDERED_ATTRIBUTES:
                if name in filters:
                    order = attributes.ALLOWED_VALUES[name]
                    distance += abs(order.index(persona.attributes[name]) - order.index(filters[name]))
            return (exact, -distance)

        scored = [(score(persona), persona) for persona in self.all()]
        best_score = max(item[0] for item in scored)
        best = [persona for item_score, persona in scored if item_score == best_score]
        chosen = rng.choice(best)

        matched = [name for name, value in filters.items() if chosen.attributes[name] == value]
        unmatched = [name for name in filters if name not in matched]
        return MatchResult(
            persona=chosen,
            exact=not unmatched,
            matched_attributes=matched,
            unmatched_attributes=unmatched,
            candidates=len(best),
        )


@lru_cache(maxsize=4)
def _load_store(directory: str) -> PersonaStore:
    result = load_personas(Path(directory))
    for problem in result.problems:
        logger.error("Skipped persona file %s", problem)
    for warning in result.warnings:
        logger.warning("Persona file %s", warning)
    logger.info("Loaded %d midterm event personas from %s", len(result.personas), directory)
    return PersonaStore(result)


def get_store() -> PersonaStore:
    """Personas are read from disk once (on first use) and kept in memory."""
    return _load_store(str(get_settings().personas_dir))
