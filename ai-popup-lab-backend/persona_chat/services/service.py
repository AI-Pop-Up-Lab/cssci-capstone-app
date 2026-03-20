from __future__ import annotations

import json
import uuid
from typing import Any

from app.core.utils import get_logger
from app.db.conn import get_conn
from app.llm.providers import get_provider

from app.services.pipeline import (
    utc_now_iso,
    load_session_info,
    load_persona_profile,
    store_user_message,
    build_grounding_bundle,
    run_pre_guardrails,
    log_injection_debug,
    log_topic_debug,
    build_answer_system_prompt,
    generate_answer,
    run_post_checks,
    enforce_post_checks_or_refuse,
    build_trace_payload,
    store_assistant_message,
)

log = get_logger(__name__)


def create_session(persona_id: str, snapshot_id: str, model_version: str) -> str:
    session_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO chat_sessions
            (session_id, persona_id, snapshot_id, model_version, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, persona_id, snapshot_id, model_version, utc_now_iso()),
        )
        conn.commit()
    return session_id


def get_session(session_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM chat_sessions WHERE session_id=?", (session_id,)).fetchone()
        return dict(row) if row else None


def list_messages(session_id: str, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT message_id, session_id, role, content, citations_json, trace_json, created_at
            FROM chat_messages
            WHERE session_id=?
            ORDER BY created_at ASC
            LIMIT ? OFFSET ?
            """,
            (session_id, limit, offset),
        ).fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        try:
            d["citations"] = json.loads(d.get("citations_json") or "[]")
        except Exception:
            d["citations"] = []
        try:
            d["trace"] = json.loads(d.get("trace_json") or "{}")
        except Exception:
            d["trace"] = {}
        out.append(d)
    return out


async def handle_user_message(session_id: str, user_text: str) -> dict[str, Any]:
    # 1) Load session + profile
    session = load_session_info(session_id)
    profile = load_persona_profile(session.persona_id, session.snapshot_id)
    provider = get_provider()

    # 2) Store user message
    store_user_message(session.session_id, user_text)

    # 3) Retrieval bundle
    grounding = build_grounding_bundle(
        persona_id=session.persona_id,
        snapshot_id=session.snapshot_id,
        profile=profile,
        user_text=user_text,
    )

    # 4) PRE-LLM guardrails (single entrypoint)
    inj, gate, combined_debug = await run_pre_guardrails(
        provider=provider,
        persona_id=session.persona_id,
        snapshot_id=session.snapshot_id,
        user_text=user_text,
        grounding=grounding,
    )

    log_injection_debug(user_text, inj)
    log_topic_debug(user_text, gate)

    # Enforce PRE decision (injection is strongest immediate blocker)
    if inj.injection_action == "REFUSE":
        content = "Sorry — I can’t help with that request."
        trace_guardrails = await run_post_checks(
            session_id=session.session_id,
            persona_id=session.persona_id,
            snapshot_id=session.snapshot_id,
            user_text=user_text,
            user_for_llm=gate.user_for_llm,
            grounding=grounding,
            llm_answer=type("X", (), {"content": content, "citations": []})(),
            gate_debug=gate.debug,
            injection_debug=inj.debug,
        )
        trace = build_trace_payload(session=session, gate_debug=gate.debug, injection_debug=inj.debug, guardrails=trace_guardrails)
        store_assistant_message(session=session, content=content, citations=[], trace=trace)
        return {"content": content, "citations": [], "trace_id": trace["trace_id"]}

    if inj.injection_action == "STEER":
        content = "I can’t help with that. Please ask something related to the persona’s background or views."
        trace_guardrails = await run_post_checks(
            session_id=session.session_id,
            persona_id=session.persona_id,
            snapshot_id=session.snapshot_id,
            user_text=user_text,
            user_for_llm=gate.user_for_llm,
            grounding=grounding,
            llm_answer=type("X", (), {"content": content, "citations": []})(),
            gate_debug=gate.debug,
            injection_debug=inj.debug,
        )
        trace = build_trace_payload(session=session, gate_debug=gate.debug, injection_debug=inj.debug, guardrails=trace_guardrails)
        store_assistant_message(session=session, content=content, citations=[], trace=trace)
        return {"content": content, "citations": [], "trace_id": trace["trace_id"]}

    # 5) Answer generation
    system_prompt = build_answer_system_prompt(gate)
    answer_bundle = await generate_answer(
        provider=provider,
        system_prompt=system_prompt,
        user_for_llm=gate.user_for_llm,
        grounding=grounding,
        max_retries=3,
    )

    # 6) POST checks (enforcing + coherence)
    post = await run_post_checks(
        session_id=session.session_id,
        persona_id=session.persona_id,
        snapshot_id=session.snapshot_id,
        user_text=user_text,
        user_for_llm=gate.user_for_llm,
        grounding=grounding,
        llm_answer=answer_bundle,
        gate_debug=gate.debug,
        injection_debug=inj.debug,
    )
    final_answer = enforce_post_checks_or_refuse(answer_bundle, post)

    # 7) Trace + store
    trace = build_trace_payload(session=session, gate_debug=gate.debug, injection_debug=inj.debug, guardrails=post)
    store_assistant_message(session=session, content=final_answer.content, citations=final_answer.citations, trace=trace)

    return {"content": final_answer.content, "citations": final_answer.citations, "trace_id": trace["trace_id"]}