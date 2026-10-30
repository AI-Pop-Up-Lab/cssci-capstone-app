import random

import pytest

from conftest import write_persona
from midterm_event_api import attributes
from midterm_event_api.config import DEFAULT_PERSONAS_DIR
from midterm_event_api.personas import (
    LoadResult,
    PersonaFileError,
    PersonaStore,
    load_personas,
    parse_persona_text,
)


def test_parses_a_persona_and_normalises_values():
    text = (
        "﻿---\r\n"
        "gender: female\r\n"
        "age_group: 43–47\r\n"  # en dash, as Word/Google Docs would write it
        "education: post-grad\r\n"
        "state: Florida\r\n"
        "race: WHITE\r\n"
        "vote_2026: Democrat\r\n"
        "---\r\n"
        "<!-- writer's note, not for the model -->\r\n"
        "You are Dana.\r\n"
    )
    persona = parse_persona_text(text, "us_0042")

    assert persona.id == "us_0042"
    assert persona.display_name == "Persona 42"
    assert persona.attributes == {
        "gender": "Female",
        "age_group": "43-47",
        "education": "Post-grad",
        "state": "FL",
        "race": "White",
    }
    assert persona.extra == {"vote_2026": "Democrat"}
    assert persona.profile == "You are Dana."


def test_display_name_can_be_set():
    text = "---\ngender: Male\nage_group: 83+\neducation: No HS\nstate: TX\nrace: Black\ndisplay_name: Earl\n---\nYou are Earl."
    assert parse_persona_text(text, "us_0001").display_name == "Earl"


@pytest.mark.parametrize(
    "text, expected_error",
    [
        ("gender: Female\nYou are...", "must start with a '---' line"),
        ("---\ngender: Female\n---\nYou are...", "missing required attribute(s): age_group, education, state, race"),
        ("---\ngender: Female\nage_group: 40-46\neducation: 4-year\nstate: FL\nrace: White\n---\nYou...", "'40-46' is not a valid age_group"),
        ("---\ngender: Female\nage_group: 43-47\neducation: 4-year\nstate: FL\nrace: White\n---\n<!-- only a comment -->", "profile text"),
        ("---\nid: us_9999\ngender: Female\nage_group: 43-47\neducation: 4-year\nstate: FL\nrace: White\n---\nYou...", "doesn't match the filename"),
        ("---\ngender: [unclosed\n---\nYou...", "valid YAML"),
    ],
)
def test_reports_what_is_wrong_with_a_file(text, expected_error):
    with pytest.raises(PersonaFileError, match=expected_error.replace("(", r"\(").replace(")", r"\)")):
        parse_persona_text(text, "us_0001")


def test_error_lists_the_allowed_values():
    text = "---\ngender: Female\nage_group: 43-47\neducation: Masters\nstate: FL\nrace: White\n---\nYou..."
    with pytest.raises(PersonaFileError) as error:
        parse_persona_text(text, "us_0001")
    assert "No HS, HS grad, Some college, 2-year, 4-year, Post-grad" in str(error.value)


def test_load_skips_broken_files_and_templates(tmp_path):
    write_persona(tmp_path, "us_0001")
    write_persona(tmp_path, "us_0002", state="Atlantis")
    write_persona(tmp_path, "_TEMPLATE")
    (tmp_path / "notes.txt").write_text("not a persona")

    result = load_personas(tmp_path)

    assert list(result.personas) == ["us_0001"]
    assert len(result.problems) == 1
    assert result.problems[0].startswith("us_0002.md: 'Atlantis' is not a valid state")


def test_shipped_personas_folder_has_no_problems():
    result = load_personas(DEFAULT_PERSONAS_DIR)
    assert result.problems == []
    assert "us_0001" in result.personas


def _store(tmp_path):
    write_persona(tmp_path, "us_0001", age_group="43-47", education="Post-grad", state="FL")
    write_persona(tmp_path, "us_0002", age_group="48-52", education="Post-grad", state="FL")
    write_persona(tmp_path, "us_0003", age_group="83+", education="Post-grad", state="FL")
    write_persona(tmp_path, "us_0004", gender="Male", age_group="23-27", education="HS grad", state="OH", race="Black")
    return PersonaStore(load_personas(tmp_path))


def test_match_exact(tmp_path):
    result = _store(tmp_path).match({"gender": "Male", "state": "OH"})
    assert result.persona.id == "us_0004"
    assert result.exact
    assert result.unmatched_attributes == []


def test_match_falls_back_to_the_closest_age_group(tmp_path):
    # nobody is 38-42 in Florida with a post-grad degree; 43-47 is the nearest age group
    result = _store(tmp_path).match({"age_group": "38-42", "education": "Post-grad", "state": "FL"})
    assert result.persona.id == "us_0001"
    assert not result.exact
    assert result.matched_attributes == ["education", "state"]
    assert result.unmatched_attributes == ["age_group"]


def test_match_with_no_filters_picks_randomly_among_everyone(tmp_path):
    store = _store(tmp_path)
    picked = {store.match({}, rng=random.Random(seed)).persona.id for seed in range(40)}
    assert picked == {"us_0001", "us_0002", "us_0003", "us_0004"}
    assert store.match({}).candidates == 4


def test_match_returns_none_without_personas():
    assert PersonaStore(LoadResult()).match({}) is None


def test_states_accept_codes_and_names():
    assert attributes.normalize("state", "fl") == "FL"
    assert attributes.normalize("state", "new  york") == "NY"
    with pytest.raises(ValueError):
        attributes.normalize("state", "Ontario")
