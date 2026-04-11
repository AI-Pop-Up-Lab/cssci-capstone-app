"""Helpers for loading, caching, and persisting stylometric persona profiles."""

import json
import os
from pathlib import Path

from _persona_chat.guardrailed.stylometry.engine import generate_stylometric_profile


local_profiles_path = Path(__file__).resolve().parents[3] / "country_data" / "stylometric_profiles.json"
mounted_profiles_path = Path("/mnt/data/stylometric_profiles.json")

if os.getenv("ENV") == "development" or not mounted_profiles_path.exists():
    STYLOMETRIC_PROFILES_PATH = local_profiles_path
else:
    STYLOMETRIC_PROFILES_PATH = mounted_profiles_path


def load_stylometric_profiles() -> dict:
    """Load cached stylometric profiles from disk."""
    if not STYLOMETRIC_PROFILES_PATH.exists():
        return {}

    with STYLOMETRIC_PROFILES_PATH.open("r") as f:
        return json.load(f)


def save_stylometric_profiles(data: dict) -> None:
    """Persist stylometric profiles to disk."""
    with STYLOMETRIC_PROFILES_PATH.open("w") as f:
        json.dump(data, f, indent=4, sort_keys=True)


def get_or_create_stylometric_profile(
    *,
    persona_details: dict,
    persona_country: str,
    persona_biography: str,
) -> dict:
    """Return a cached stylometric profile or generate one when missing."""
    persona_index = str(persona_details["index"])
    data = load_stylometric_profiles()

    if persona_country not in data:
        data[persona_country] = {}

    if persona_index in data[persona_country]:
        return data[persona_country][persona_index]

    profile = generate_stylometric_profile(
        persona_biography=persona_biography,
        persona_details=persona_details,
        persona_country=persona_country,
    )
    data[persona_country][persona_index] = profile
    save_stylometric_profiles(data)
    return profile
