"""
Shared test setup. Run from the ai-popup-lab-backend folder:

    python -m pytest midterm_event_api/tests -q

No real model calls are made: tests replace llm.complete / llm.stream with fakes.
"""

import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

# importing api_endpoints imports every router, and one of them connects to Azure storage
# at import time; a dummy connection string is enough because nothing is downloaded
os.environ.setdefault(
    "AZURE_STORAGE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=https;AccountName=dummy;AccountKey=ZHVtbXk=;EndpointSuffix=core.windows.net",
)

from midterm_event_api.limits import limiter  # noqa: E402

PERSONA_TEMPLATE = """---
gender: {gender}
age_group: {age_group}
education: {education}
state: {state}
race: {race}
---
You are a test persona from {state}.
"""


def write_persona(directory: Path, persona_id: str, **overrides) -> Path:
    values = {
        "gender": "Female",
        "age_group": "43-47",
        "education": "Post-grad",
        "state": "FL",
        "race": "White",
        **overrides,
    }
    path = directory / f"{persona_id}.md"
    path.write_text(PERSONA_TEMPLATE.format(**values), encoding="utf-8")
    return path


@pytest.fixture
def personas_dir(tmp_path, monkeypatch):
    """A personas folder with three personas, used by the API through MIDTERM_PERSONAS_DIR."""
    directory = tmp_path / "personas"
    directory.mkdir()
    write_persona(directory, "us_0001")
    write_persona(directory, "us_0002", gender="Male", age_group="68-72", education="HS grad", state="OH")
    write_persona(directory, "us_0003", gender="Male", age_group="23-27", education="4-year", state="TX", race="Hispanic")
    monkeypatch.setenv("MIDTERM_PERSONAS_DIR", str(directory))
    return directory


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch):
    # tests start from the defaults, whatever is in a local .env
    for name in list(os.environ):
        if name.startswith("MIDTERM_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_BASE_URL", "https://example.invalid/openai/v1/")
    monkeypatch.setenv("AZURE_OPENAI_MODEL", "test-model")
    limiter.reset()
    yield
    limiter.reset()
