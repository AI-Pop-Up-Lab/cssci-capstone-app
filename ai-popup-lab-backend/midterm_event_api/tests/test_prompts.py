from midterm_event_api.config import DEFAULT_BASE_PROMPT_PATH, get_settings
from midterm_event_api.chat import build_messages
from midterm_event_api.personas import parse_persona_text
from midterm_event_api.prompts import FACTS_PLACEHOLDER, PROFILE_PLACEHOLDER, build_system_prompt, load_base_prompt

PERSONA = parse_persona_text(
    "---\ngender: Female\nage_group: 43-47\neducation: 2-year\nstate: FL\nrace: White\n---\nYou are Dana.",
    "us_0001",
)


def test_shipped_base_prompt_has_both_placeholders_and_no_comments():
    base = load_base_prompt(str(DEFAULT_BASE_PROMPT_PATH))
    assert FACTS_PLACEHOLDER in base
    assert PROFILE_PLACEHOLDER in base
    assert "<!--" not in base


def test_system_prompt_fills_in_the_persona():
    prompt = build_system_prompt(PERSONA, load_base_prompt(str(DEFAULT_BASE_PROMPT_PATH)))

    assert "- State: Florida (FL)" in prompt
    assert "- Education: 2-year college (associate) degree" in prompt
    assert "- Age: 43-47 years old" in prompt
    assert "You are Dana." in prompt
    assert "{{" not in prompt


def test_persona_is_appended_if_placeholders_are_missing():
    prompt = build_system_prompt(PERSONA, "Be nice.")
    assert prompt.startswith("Be nice.")
    assert "- Gender: Female" in prompt
    assert prompt.endswith("You are Dana.")


def test_messages_keep_only_recent_history(monkeypatch):
    monkeypatch.setenv("MIDTERM_MAX_HISTORY_MESSAGES", "2")
    history = [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "user", "content": "three"},
        {"role": "assistant", "content": "four"},
    ]
    messages = build_messages(PERSONA, "five", history, get_settings())

    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert [m["content"] for m in messages[1:]] == ["three", "four", "five"]
