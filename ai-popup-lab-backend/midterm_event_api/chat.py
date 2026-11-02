"""
The chat flow for one visitor message:

  1. moderation.check_user_message   (placeholder, allows everything for now)
  2. build the prompt: shared rules + persona (prompts.py), recent chat history, the new message
  3. call the model (llm.py)
       buffered mode: wait for the whole reply, run moderation.check_reply, then send it
       stream mode:   send the reply piece by piece as it is generated (no reply check possible)
  4. if Azure's content filter blocks something, the persona answers with BLOCKED_REPLY

The result is a sequence of ReplyEvents that the endpoint turns into server-sent events:
  "message": text to append to the persona's chat bubble
  "error":   text that replaces the bubble's contents (the old frontend already treats it this way)

Chats are not stored. Logs contain the persona ID, reply mode, timing and errors, never message text.
"""

import json
import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from midterm_event_api import llm, moderation
from midterm_event_api.config import Settings
from midterm_event_api.personas import Persona
from midterm_event_api.prompts import build_system_prompt, load_base_prompt

logger = logging.getLogger(__name__)

ERROR_REPLY = "Sorry, something went wrong on our side. Please try sending that again."
EMPTY_REPLY = "Sorry, I lost my train of thought. Could you ask that again?"


@dataclass(frozen=True)
class ReplyEvent:
    event: str
    text: str


@lru_cache(maxsize=4)
def load_news_digests(path: str) -> dict:
    # {persona_id: [news points]} from generation/digest_news.py
    return json.loads(Path(path).read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def load_salient_events(path: str) -> dict:
    # {national_context: {...}} from generation/fetch_salient_events.py
    return json.loads(Path(path).read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def load_state_events(path: str) -> dict:
    # {"AK": [...], "AL": [...]} for all 50 states from generation/fetch_state_events.py
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_messages(persona: Persona, user_message: str, history: list, settings: Settings) -> list:
    events_data = {}

    # 1. Macro salient events & 2025-2026 context (shared national reality)
    if settings.salient_events_path and Path(settings.salient_events_path).exists():
        try:
            events_data.update(load_salient_events(str(settings.salient_events_path)))
        except Exception as e:
            logger.warning("Failed to load salient events: %s", e)

    # 2. State-specific events: inject ONLY this persona's state from the 50-state database
    if settings.state_events_path and Path(settings.state_events_path).exists():
        try:
            states_dict = load_state_events(str(settings.state_events_path))
            p_state = persona.attributes.get("state")
            if p_state and p_state in states_dict:
                events_data["state_highlights"] = {p_state: states_dict[p_state]}
        except Exception as e:
            logger.warning("Failed to load state events: %s", e)

    # 3. Individual persona GDELT media digest points (from digest_news.py)
    if settings.events_path and Path(settings.events_path).exists():
        try:
            points = load_news_digests(str(settings.events_path)).get(persona.id, [])
            if points:
                events_data["media_diet_points"] = points
        except Exception as e:
            logger.warning("Failed to load news digests: %s", e)

    system_prompt = build_system_prompt(
        persona,
        load_base_prompt(str(settings.base_prompt_path)),
        events_data if events_data else None,
    )

    # only the most recent turns are sent, which keeps long chats fast and cheap
    recent = history[-settings.max_history_messages:] if settings.max_history_messages > 0 else []

    return [
        {"role": "system", "content": system_prompt},
        *({"role": turn["role"], "content": turn["content"]} for turn in recent),
        {"role": "user", "content": user_message},
    ]


async def reply_events(persona: Persona, user_message: str, history: list, settings: Settings):
    started = time.monotonic()
    outcome = "ok"
    try:
        check = await moderation.check_user_message(user_message)
        if not check.allowed:
            outcome = "blocked_message"
            yield ReplyEvent("message", moderation.BLOCKED_REPLY)
            return

        messages = build_messages(persona, check.text, history, settings)

        if settings.reply_mode == "stream":
            sent_anything = False
            try:
                async for piece in llm.stream(messages, settings):
                    sent_anything = True
                    yield ReplyEvent("message", piece)
            except llm.ContentFilteredError:
                # "error" replaces whatever part of the reply was already shown
                outcome = "azure_filter"
                yield ReplyEvent("error", moderation.BLOCKED_REPLY)
                return
            if not sent_anything:
                outcome = "empty"
                yield ReplyEvent("error", EMPTY_REPLY)
            return

        try:
            reply = await llm.complete(messages, settings)
        except llm.ContentFilteredError:
            outcome = "azure_filter"
            yield ReplyEvent("message", moderation.BLOCKED_REPLY)
            return

        reply = reply.strip()
        if not reply:
            outcome = "empty"
            yield ReplyEvent("error", EMPTY_REPLY)
            return

        check = await moderation.check_reply(reply)
        if not check.allowed:
            outcome = "blocked_reply"
            yield ReplyEvent("message", moderation.BLOCKED_REPLY)
            return
        yield ReplyEvent("message", check.text)

    except Exception as error:
        outcome = "error"
        # log the error type only: the exception text can contain the visitor's message
        logger.error("Midterm chat failed for persona %s: %s", persona.id, type(error).__name__)
        yield ReplyEvent("error", ERROR_REPLY)

    finally:
        logger.info(
            "Midterm chat persona=%s mode=%s outcome=%s seconds=%.2f",
            persona.id, settings.reply_mode, outcome, time.monotonic() - started,
        )
