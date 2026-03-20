import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.conn import get_persona_conn
from app.core.config import settings
from app.schemas import ChatMessageIn, ChatSessionCreate
from app.services.persona_repository import (
    get_answer_exact,
    get_persona_profile,
    list_personas,
    list_questions_for_persona,
)
from app.services.service import create_session, get_session, handle_user_message, list_messages
from pathlib import Path

from generate_biography import generate_biography
from generate_response import generate_response

router = APIRouter()


class LegacyChatMessage(BaseModel):
    message: str
    persona_details: dict
    persona_country: str

base_dir = Path(__file__).resolve().parent.parent  # goes up from api_endpoints to root
biographies_path = base_dir / "country_data" / "biographies.json"

def _legacy_snapshot_id(country: str) -> str:
    return f"legacy_{(country or 'unknown').lower()}_bridge_v1"


def _legacy_persona_id(country: str, persona_details: dict) -> str:
    raw_index = persona_details.get("index", 0)
    try:
        index = int(raw_index)
    except Exception:
        index = 0

    normalized_country = "".join(ch for ch in (country or "unknown").lower() if ch.isalnum() or ch == "_")
    return f"LEGACY_{normalized_country}_{index}"


def _select_legacy_persona(snapshot_id: str, persona_details: dict) -> dict:
    personas = list_personas(snapshot_id)
    if not personas:
        raise HTTPException(status_code=404, detail="No personas available")

    raw_index = persona_details.get("index", 0)
    try:
        persona_index = int(raw_index)
    except Exception:
        persona_index = 0

    return personas[persona_index % len(personas)]


def _merge_legacy_profile(persona_details: dict, supplemental_profile: dict) -> dict:
    raw_index = persona_details.get("index", 0)
    try:
        persona_number = int(raw_index) + 1
    except Exception:
        persona_number = 1

    merged = {
        "display_name": f"Persona {persona_number}",
        "municipality": persona_details.get("municipality"),
        "municipality_code": persona_details.get("gm_code"),
        "gender": persona_details.get("gender"),
        "age_band": persona_details.get("age_group"),
        "education_level": persona_details.get("education"),
        "vote_2030": persona_details.get("vote_2030"),
    }

    for key, value in supplemental_profile.items():
        if key in merged and merged[key] not in (None, ""):
            continue
        merged[key] = value

    merged["disclosure"] = supplemental_profile.get(
        "disclosure",
        "Synthetic persona composed from survey sample attributes and supplemental persona evidence.",
    )

    return {key: value for key, value in merged.items() if value not in (None, "")}


def _upsert_legacy_bridge_persona(
    *,
    legacy_persona_id: str,
    legacy_snapshot_id: str,
    persona_details: dict,
    supplemental_persona: dict,
) -> None:
    profile = _merge_legacy_profile(persona_details, supplemental_persona["profile"])

    with get_persona_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO personas (persona_id, snapshot_id, profile_json, created_at)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (
                legacy_persona_id,
                legacy_snapshot_id,
                json.dumps(profile, ensure_ascii=False),
            ),
        )

        conn.execute(
            "DELETE FROM survey_answers WHERE persona_id=? AND snapshot_id=?",
            (legacy_persona_id, legacy_snapshot_id),
        )

        source_answers = conn.execute(
            """
            SELECT question_id, answer_value, answer_text, wave, confidence, source, calibration_tag
            FROM survey_answers
            WHERE persona_id=? AND snapshot_id=?
            ORDER BY question_id, wave
            """,
            (supplemental_persona["persona_id"], supplemental_persona["snapshot_id"]),
        ).fetchall()

        for row in source_answers:
            conn.execute(
                """
                INSERT OR REPLACE INTO survey_answers (
                    persona_id, snapshot_id, question_id, answer_value, answer_text, wave,
                    confidence, source, calibration_tag, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    legacy_persona_id,
                    legacy_snapshot_id,
                    row["question_id"],
                    row["answer_value"],
                    row["answer_text"],
                    row["wave"],
                    row["confidence"],
                    row["source"],
                    row["calibration_tag"],
                ),
            )

        conn.commit()


@router.get("/personas")
def api_list_personas(snapshot_id: str = "2026_wave_1"):
    personas = list_personas(snapshot_id)
    return {"snapshot_id": snapshot_id, "personas": personas}


@router.get("/persona/{persona_id}/profile")
def api_get_persona_profile(persona_id: str, snapshot_id: str = "2026_wave_1"):
    profile = get_persona_profile(persona_id, snapshot_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Persona not found")

    questions = list_questions_for_persona(persona_id, snapshot_id)
    return {
        "persona_id": persona_id,
        "snapshot_id": snapshot_id,
        "profile": profile,
        "questions": questions,
    }


@router.get("/persona/{persona_id}/answers")
def api_get_answers(persona_id: str, snapshot_id: str = "2026_wave_1", question_id: str | None = None):
    if not question_id:
        raise HTTPException(status_code=400, detail="question_id is required")

    return {"answers": get_answer_exact(persona_id, snapshot_id, question_id)}


@router.post("/chat/session")
def api_create_session(payload: ChatSessionCreate):
    model_version = f"provider:{settings.LLM_PROVIDER}"
    session_id = create_session(payload.persona_id, payload.snapshot_id, model_version=model_version)

    return {
        "session_id": session_id,
        "persona_id": payload.persona_id,
        "snapshot_id": payload.snapshot_id,
        "model_version": model_version,
    }


@router.get("/chat/{session_id}")
def api_get_session(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = list_messages(session_id)
    return {"session": session, "messages": messages}


# @router.post("/chat/{session_id}/message")
# async def api_send_message(session_id: str, payload: ChatMessageIn):
#     try:
#         return await handle_user_message(session_id, payload.content)
#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc)) from exc


# @router.post("/chat/chat_message")
# async def api_legacy_chat_message(payload: LegacyChatMessage):
#     source_snapshot_id = "2026_wave_1"
#     supplemental_persona = _select_legacy_persona(source_snapshot_id, payload.persona_details)
#     bridged_snapshot_id = _legacy_snapshot_id(payload.persona_country)
#     bridged_persona_id = _legacy_persona_id(payload.persona_country, payload.persona_details)

#     _upsert_legacy_bridge_persona(
#         legacy_persona_id=bridged_persona_id,
#         legacy_snapshot_id=bridged_snapshot_id,
#         persona_details=payload.persona_details,
#         supplemental_persona=supplemental_persona,
#     )

#     model_version = f"provider:{settings.LLM_PROVIDER}"
#     session_id = create_session(
#         bridged_persona_id,
#         bridged_snapshot_id,
#         model_version=model_version,
#     )

#     try:
#         result = await handle_user_message(session_id, payload.message)
#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc)) from exc

#     return {
#         "message": result["content"],
#         "citations": result.get("citations", []),
#         "trace_id": result.get("trace_id"),
#         "persona_id": bridged_persona_id,
#         "snapshot_id": bridged_snapshot_id,
#     }

@router.post("/chat/chat_message")
async def personaResponse(request_body: LegacyChatMessage):

    persona_index = request_body.persona_details['index']

    persona_details = request_body.persona_details

    with open(biographies_path, 'r') as f:
        data = json.load(f)

    if str(persona_index) in data:
        biography = data[str(persona_index)]
    else:
        biography = generate_biography(age_group=persona_details['age_group'], gender=persona_details['gender'], vote_2030=persona_details['vote_2030'], education=persona_details['education'], municipality=persona_details['municipality'])
        data[str(persona_index)] = biography

        with open(biographies_path, "w") as f:
            json.dump(data, f, indent=4, sort_keys=True)

    response = generate_response(persona_biography=biography, user_message=request_body.message)

    return {"message": response}