'''
endpoints for the US midterms election-night event persona chat
all under /api/midterm_event, the logic lives in the midterm_event_api/ folder
full API description: midterm_event_api/README.md
'''

import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from midterm_event_api import attributes
from midterm_event_api.chat import ReplyEvent, reply_events
from midterm_event_api.config import get_settings
from midterm_event_api.limits import client_key, limiter
from midterm_event_api.personas import get_store

router = APIRouter(prefix="/midterm_event")

CHAT_PAUSED_MESSAGE = "The persona chat is paused right now. Please try again in a few minutes."
LIMIT_REACHED_MESSAGE = "Sorry, you have reached the message limit for today."
EMPTY_MESSAGE = "Please type a message first."


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    persona_id: str
    message: str
    # previous messages in this chat, oldest first, without the new message
    chat_history: list[ChatTurn] = Field(default_factory=list, max_length=200)


def _sse(event: str, text: str) -> str:
    # same event format as the old /api/chat/chat_message endpoint
    return f"event: {event}\ndata: {json.dumps({'text': text})}\n\n"


def _sse_response(events) -> StreamingResponse:
    async def body():
        async for item in events:
            yield _sse(item.event, item.text)
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


def _single_message(text: str, event: str = "error") -> StreamingResponse:
    async def events():
        yield ReplyEvent(event, text)

    return _sse_response(events())


def _persona_or_404(persona_id: str):
    persona = get_store().get(persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail=f"Unknown persona_id '{persona_id}'")
    return persona


# ENDPOINTS BELOW

# GET the allowed values for each attribute, for building the dropdowns
@router.get("/attributes")
def get_attributes():
    return {
        "attributes": list(attributes.ATTRIBUTES),
        "values": attributes.ALLOWED_VALUES,
        "any_value": attributes.ANY_VALUE,
        "state_names": attributes.STATE_NAMES,
    }


# GET every persona's ID, display name and attributes (never the profile text)
@router.get("/personas")
def list_personas():
    personas = get_store().all()
    return {"count": len(personas), "personas": [persona.public() for persona in personas]}


@router.get("/personas/{persona_id}")
def get_persona(persona_id: str):
    return _persona_or_404(persona_id).public()


# GET the best persona for the visitor's dropdown choices, e.g.
# /api/midterm_event/match?gender=Female&age_group=43-47&education=Post-grad&state=FL&race=all
@router.get("/match")
def match_persona(
    gender: str | None = None,
    age_group: str | None = None,
    education: str | None = None,
    state: str | None = None,
    race: str | None = None,
):
    chosen = {"gender": gender, "age_group": age_group, "education": education, "state": state, "race": race}

    filters = {}
    for name, value in chosen.items():
        if value is None or value.strip() == "" or value.strip().lower() == attributes.ANY_VALUE:
            continue
        try:
            filters[name] = attributes.normalize(name, value)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))

    result = get_store().match(filters)
    if result is None:
        raise HTTPException(status_code=503, detail="No personas are loaded")

    return {
        "persona": result.persona.public(),
        "exact_match": result.exact,
        "matched_attributes": result.matched_attributes,
        "unmatched_attributes": result.unmatched_attributes,
        "equally_good_matches": result.candidates,
    }


# POST a visitor message, get the persona's reply back as server-sent events
@router.post("/chat")
async def chat(request: Request, request_body: ChatRequest):
    settings = get_settings()

    # kill switch: MIDTERM_CHAT_ENABLED=false pauses the chat without a code change
    if not settings.chat_enabled:
        return _single_message(CHAT_PAUSED_MESSAGE)

    persona = _persona_or_404(request_body.persona_id)

    message = request_body.message.strip()
    if not message:
        return _single_message(EMPTY_MESSAGE)
    if len(message) > settings.max_message_chars:
        return _single_message(
            f"That message is too long. Please keep it under {settings.max_message_chars} characters."
        )

    # FLAG: limit is 10,000/day by default, i.e. effectively off for the event (see limits.py)
    if not limiter.allow(client_key(request), settings.daily_message_limit):
        return _single_message(LIMIT_REACHED_MESSAGE)

    history = [turn.model_dump() for turn in request_body.chat_history]
    return _sse_response(reply_events(persona, message, history, settings))


# GET a quick health check for the event: is the chat on, are personas and the model configured
@router.get("/status")
def status():
    settings = get_settings()
    store = get_store()
    return {
        "chat_enabled": settings.chat_enabled,
        "reply_mode": settings.reply_mode,
        "personas_loaded": len(store.personas),
        "persona_file_problems": store.problems,
        "model_configured": bool(settings.azure_api_key and settings.azure_base_url and settings.model),
        "daily_message_limit": settings.daily_message_limit,
    }
