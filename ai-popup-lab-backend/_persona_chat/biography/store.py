"""Helpers for loading, caching, and persisting persona biographies."""

import json
import os
from pathlib import Path

from _persona_chat.biography.engine import generate_biography


# =============================================================================
# Path Configuration
# =============================================================================

local_biographies_path = Path(__file__).resolve().parents[2] / "country_data" / "biographies.json"
mounted_biographies_path = Path("/mnt/data/biographies.json")

if os.getenv("ENV") == "development" or not mounted_biographies_path.exists():
    BIOGRAPHIES_PATH = local_biographies_path
else:
    BIOGRAPHIES_PATH = mounted_biographies_path


# =============================================================================
# Cache I/O
# =============================================================================

def load_biographies() -> dict:
    """Load the biography cache from disk."""
    with BIOGRAPHIES_PATH.open("r") as f:
        return json.load(f)


def save_biographies(data: dict) -> None:
    """Persist the biography cache to disk."""
    with BIOGRAPHIES_PATH.open("w") as f:
        json.dump(data, f, indent=4, sort_keys=True)


# =============================================================================
# Biography Resolution
# =============================================================================

def get_or_create_biography(*, persona_details: dict, persona_country: str) -> str:
    """Return a cached biography or generate and store one when missing."""

    
    persona_index = str(persona_details["index"])
    data = load_biographies()


    # The cache is grouped by country and then persona index.
    if str(persona_country) not in data:
        data[persona_country] = {}


    if persona_index in data[persona_country]:
        return data[persona_country][persona_index]
    

    biography = generate_biography(
        persona_details=persona_details,
        country=persona_country,
    )


    data[persona_country][persona_index] = biography
    save_biographies(data)
    return biography
