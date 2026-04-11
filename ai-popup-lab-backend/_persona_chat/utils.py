"""Shared chat response utilities used by multiple persona chat engines."""

import json

from openai import OpenAI

from _persona_chat.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_BASE_URL,
    AZURE_OPENAI_MODEL,
)


# =============================================================================
# Prompt and Message Builders
# =============================================================================

def create_system_prompt(base_prompt: str, biography: str) -> str:
    """Attach the persona biography to a response mode's system prompt."""
    return f"{base_prompt}\n{biography}"


def build_chat_messages(*, system_prompt: str, user_message: str, chat_history: list) -> list:
    """Build the message list sent to the chat completion API."""
    return [
        {"role": "system", "content": system_prompt},
        *chat_history,
        {"role": "user", "content": user_message},
    ]


# =============================================================================
# Shared LLM Calls
# =============================================================================

def run_chat_completion(*, messages: list, temperature: float, json_mode: bool = False) -> str:
    """Run a non-streaming chat completion using the shared model configuration."""
    client = OpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        base_url=AZURE_OPENAI_BASE_URL,
    )

    format_type = {"type": "json_object"} if json_mode else None

    response = client.chat.completions.create(
        model=AZURE_OPENAI_MODEL,
        messages=messages,
        response_format=format_type,
        temperature=temperature,
        stream=False,
    )

    content = response.choices[0].message.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict)
        )

    return json.dumps(content)

def stream_chat_response(*, messages: list, temperature: float, json_mode: bool = False):
    """Stream a chat completion using the shared model configuration."""
    client = OpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        base_url=AZURE_OPENAI_BASE_URL,
    )

    format_type = {"type": "json_object"} if json_mode else None

    response = client.chat.completions.create(
        model=AZURE_OPENAI_MODEL,
        messages=messages,
        response_format=format_type,
        temperature=temperature,
        stream=True,
    )

    for chunk in response:
        # Some stream events can arrive without any choices payload, for example
        # usage/finalization events. Those should simply be ignored.
        if not getattr(chunk, "choices", None):
            continue

        choice = chunk.choices[0]
        delta = getattr(choice, "delta", None)
        content = getattr(delta, "content", None)

        if content:
            yield content
