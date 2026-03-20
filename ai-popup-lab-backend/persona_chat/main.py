from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.init_db import init_db, seed_demo_data
from app.schemas import ChatMessageIn, ChatSessionCreate
from app.services.service import create_session, handle_user_message, get_session, list_messages
from app.services.persona_repository import (
    get_persona_profile,
    list_personas,
    list_questions_for_persona,
    get_answer_exact,
)

app = FastAPI(title="Ask-the-Persona API", version="1.0.0")

# -------------------------------------------------------------------------------------------------
# CORS (React dev server -> FastAPI)
# -------------------------------------------------------------------------------------------------
origins = [
    "aipopup-mvp-byatgpamb0cpb2du.swedencentral-01.azurewebsites.net",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------------------------------------
# Startup
# -------------------------------------------------------------------------------------------------
@app.on_event("startup")
def _startup():
    init_db()
    seed_demo_data()

# -------------------------------------------------------------------------------------------------
# Root health (helpful so "/" isn't Not Found)
# -------------------------------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "ok": True,
        "service": "Ask-the-Persona API",
        "ui": "http://localhost:3000",
        "docs": "http://127.0.0.1:8000/docs",
    }

# -------------------------------------------------------------------------------------------------
# Personas (for React UI)
# -------------------------------------------------------------------------------------------------
@app.get("/api/personas")
def api_list_personas(snapshot_id: str = "2026_wave_1"):
    personas = list_personas(snapshot_id)
    return {"snapshot_id": snapshot_id, "personas": personas}

@app.get("/api/persona/{persona_id}/profile")
def api_get_persona_profile(persona_id: str, snapshot_id: str = "2026_wave_1"):
    profile = get_persona_profile(persona_id, snapshot_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Persona not found")
    questions = list_questions_for_persona(persona_id, snapshot_id)
    return {"persona_id": persona_id, "snapshot_id": snapshot_id, "profile": profile, "questions": questions}

@app.get("/api/persona/{persona_id}/answers")
def api_get_answers(persona_id: str, snapshot_id: str = "2026_wave_1", question_id: str | None = None):
    if not question_id:
        raise HTTPException(status_code=400, detail="question_id is required")
    return {"answers": get_answer_exact(persona_id, snapshot_id, question_id)}

# -------------------------------------------------------------------------------------------------
# Chat API (unchanged behavior)
# -------------------------------------------------------------------------------------------------
@app.post("/api/chat/session")
def api_create_session(payload: ChatSessionCreate):
    model_version = f"provider:{settings.LLM_PROVIDER}"
    sess_id = create_session(payload.persona_id, payload.snapshot_id, model_version=model_version)
    return {
        "session_id": sess_id,
        "persona_id": payload.persona_id,
        "snapshot_id": payload.snapshot_id,
        "model_version": model_version,
    }

@app.get("/api/chat/{session_id}")
def api_get_session(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    msgs = list_messages(session_id)
    return {"session": sess, "messages": msgs}

@app.post("/api/chat/{session_id}/message")
async def api_send_message(session_id: str, payload: ChatMessageIn):
    try:
        out = await handle_user_message(session_id, payload.content)
        return out
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))