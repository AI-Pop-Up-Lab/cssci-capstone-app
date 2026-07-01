from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Optional

from openai import OpenAI
import cohere
import json


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

def send_message_cohere_rag(question, conversation, articles):
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

    try:
        response = co.chat(
            model="command-r-plus-08-2024",
            messages=messages,
            documents=documents,
        )
    except Exception as e:
        print("FAILED - FULL MESSAGES:")
        for i, m in enumerate(messages):
            print(f"  [{i}] role={m['role']!r}, content_length={len(m.get('content') or '')}, content_preview={str(m.get('content', ''))[:100]!r}")
        print(f"Number of documents: {len(documents)}")
        raise

    return response.message.content[0].text, response.message.citations



def send_message(message: str,
				 conversation: Optional[List[Dict[str, str]]] = None,
				 max_tokens: int = 2048,
				 temperature: float = 0.7,) -> str:
	"""Send `message` to Azure OpenAI and return the respondent message.

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

	response = client.chat.completions.create(
		model=model,
		messages=messages,
		max_tokens=max_tokens,
		temperature=temperature,
	)

	try:
		respondent_msg = response.choices[0].message.content
	except Exception as exc:
		raise RuntimeError(f"Unexpected Azure OpenAI response shape: {response}") from exc

	if respondent_msg is None:
		raise RuntimeError("Model returned an empty respondent message")

	return respondent_msg




__all__ = ["send_message"]