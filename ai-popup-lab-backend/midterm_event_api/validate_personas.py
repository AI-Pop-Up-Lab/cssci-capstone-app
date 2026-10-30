"""
Check persona files before committing or deploying them.

Run from the ai-popup-lab-backend folder:

    python -m midterm_event_api.validate_personas            # checks midterm_event_api/personas/
    python -m midterm_event_api.validate_personas some/dir   # checks another folder
    python -m midterm_event_api.validate_personas --values   # lists the allowed attribute values

Prints every problem, then how the valid personas are spread over each attribute, so gaps
(e.g. no personas from a state) are easy to spot. Exits with code 1 if any file has a problem.
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

from midterm_event_api import attributes
from midterm_event_api.config import DEFAULT_PERSONAS_DIR
from midterm_event_api.generation.sample_personas import media_hours_range
from midterm_event_api.personas import load_personas


def print_allowed_values():
    for name in attributes.ATTRIBUTES:
        print(f"{name}:")
        for value in attributes.ALLOWED_VALUES[name]:
            extra = f"  ({attributes.STATE_NAMES[value]})" if name == "state" else ""
            print(f"  {value}{extra}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check midterm event persona files.")
    parser.add_argument("directory", nargs="?", default=str(DEFAULT_PERSONAS_DIR))
    parser.add_argument("--values", action="store_true", help="list the allowed attribute values")
    args = parser.parse_args(argv)

    if args.values:
        print_allowed_values()
        return 0

    result = load_personas(Path(args.directory))

    # warn when media_hours doesn't fit the persona's age and education
    for persona in result.personas.values():
        hours = persona.extra.get("media_hours")
        if hours is None:
            continue
        low, high = media_hours_range(persona.attributes["age_group"], persona.attributes["education"])
        if not isinstance(hours, int) or not low <= hours <= high:
            result.warnings.append(
                f"{persona.source_file}: media_hours is {hours}, expected {low}-{high} for "
                f"age {persona.attributes['age_group']} and {persona.attributes['education']}"
            )

    if result.problems:
        print(f"PROBLEMS ({len(result.problems)} file(s) will be skipped by the API):")
        for problem in result.problems:
            print(f"  - {problem}")
        print()

    if result.warnings:
        print(f"WARNINGS ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  - {warning}")
        print()

    personas = list(result.personas.values())
    print(f"{len(personas)} valid persona(s) in {args.directory}")

    if personas:
        for name in attributes.ATTRIBUTES:
            counts = Counter(persona.attributes[name] for persona in personas)
            spread = ", ".join(f"{value}: {counts[value]}" for value in attributes.ALLOWED_VALUES[name] if counts[value])
            missing = [value for value in attributes.ALLOWED_VALUES[name] if not counts[value]]
            print(f"  {name}: {spread}")
            if missing:
                print(f"    no personas for: {', '.join(missing)}")

    return 1 if result.problems else 0


if __name__ == "__main__":
    sys.exit(main())
