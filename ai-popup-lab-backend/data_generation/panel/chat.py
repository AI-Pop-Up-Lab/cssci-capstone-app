from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Optional

from openai import OpenAI
import cohere

from .retry_utils import retry_call

# Load .env from modules directory or project root
env_path = Path(__file__).resolve().parent / '.env'  # modules/.env
if not env_path.exists():
    env_path = Path(__file__).resolve().parents[1] / '.env'  # project/.env

if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass


def _get_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return val


co = cohere.ClientV2(_get_env('COHERE_API_KEY'))


def _cohere_rag_call(messages, documents):
    return co.chat(
        model="command-r-plus-08-2024",
        messages=messages,
        documents=documents,
    )


def send_message_cohere_rag(question, conversation, articles):
    """Send `question` to Cohere's RAG-grounded chat endpoint, retrying up to
    5 times with backoff on failure. Returns (text, citations)."""
    documents = [
        {
            "data": {
                "title": a.get("title") or "Untitled",
                "snippet": (a.get("text") or "")[:1500],
            }
        }
        for a in articles
    ]

    messages = []

    system_content = next(
        (msg["content"] for msg in conversation if msg["role"] == "system"), None
    )
    if system_content:
        messages.append({"role": "system", "content": system_content})

    for msg in conversation:
        if msg["role"] == "system":
            continue
        role = msg["role"]
        if role == "respondent":
            role = "assistant"
        messages.append({"role": role, "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    response = retry_call(_cohere_rag_call, messages, documents)

    return response.message.content[0].text, response.message.citations


def _azure_chat_call(client, model, messages, max_tokens, temperature):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    respondent_msg = response.choices[0].message.content
    if respondent_msg is None:
        # Treat an empty completion as a retryable failure rather than a hard
        # error — it's usually transient (content filter hiccup, truncation).
        raise RuntimeError("Model returned an empty respondent message")
    return respondent_msg


def send_message(message: str,
                  conversation: Optional[List[Dict[str, str]]] = None,
                  max_tokens: int = 2048,
                  temperature: float = 0.7) -> str:
    """Send `message` to Azure OpenAI and return the respondent message,
    retrying up to 5 times with backoff on failure.

    Args:
      message: the user message text.
      conversation: optional list of prior messages in the form
        [{"role": "system|user|assistant", "content": "..."}, ...].
      max_tokens: token limit for the response.
      temperature: sampling temperature.

    Returns:
      The respondent reply as a plain string.
    """
    api_key = _get_env('AZURE_OPENAI_API_KEY')
    model = _get_env('AZURE_OPENAI_MODEL')
    base_url = _get_env('AZURE_OPENAI_BASE_URL').rstrip('/')
    client = OpenAI(api_key=api_key, base_url=base_url)

    if conversation is None:
        conversation = []

    # Copy to avoid mutating caller list. Internally map respondent role to assistant role.
    messages = []
    for turn in conversation:
        msg = dict(turn)
        if msg.get('role') == 'respondent':
            msg['role'] = 'assistant'
        messages.append(msg)
    messages.append({"role": "user", "content": message})

    return retry_call(_azure_chat_call, client, model, messages, max_tokens, temperature)


__all__ = ["send_message", "send_message_cohere_rag"]
