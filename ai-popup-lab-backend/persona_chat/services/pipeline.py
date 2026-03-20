"""
________________________________________________________________________________________________________________________
                                              chat_workflow.py
________________________________________________________________________________________________________________________
----------------------------------------------------
DESCRIPTION:
----------------------------------------------------
Orchestrates the full conversational flow for a persona chat session:
from session loading and retrieval, through pre-LLM validation and answer
generation, to post-LLM guardrails, coherence, and persistence.

This module defines the step-by-step runtime workflow of a single
user message interaction.

________________________________________________________________________________________________________________________
                                                PIPELINE STEPS:
________________________________________________________________________________________________________________________
----------------------------------------------------
STEP 1 — Session & Persona Loading
----------------------------------------------------
- Load session metadata from `chat_sessions`
- Load persona profile from `persona.db`
- Validate session and persona existence

----------------------------------------------------
STEP 2 — Persist User Message
----------------------------------------------------
- Generate a new `message_id`
- Store user message in `chat_messages` table
- Timestamp with UTC ISO format

----------------------------------------------------
STEP 3 — Retrieval & Grounding
----------------------------------------------------
- Retrieve top-k relevant persona answers (similarity-based)
- Filter by minimum relevance score
- Load full list of persona questions
- Construct a `GroundingBundle` containing:
  - persona profile
  - relevant answers
  - suggested questions

----------------------------------------------------
STEP 4 — Pre-LLM Guardrails (Validation Gate)
----------------------------------------------------
- Call combined validator (LLM-based judge)
- Compute injection decision
- Compute scope/scope decision
- Map validator output to:
  - `InjectionGateBundle`
  - `TopicGateBundle`
- Log structured debug output
- Potential early refusal/steering decision

----------------------------------------------------
STEP 5 — Answer Generation (LLM Call)
----------------------------------------------------
- Build dynamic system prompt based on scope tier
- Prepare structured grounding payload
- Call provider `.generate()`
- Retry on failure (up to `max_retries`)
- Return `LlmAnswerBundle`

----------------------------------------------------
STEP 6 — Post-LLM Enforcement & Monitoring
----------------------------------------------------
- Build unified post-generation context
- Run enforcing guardrails (can fail)
- Run coherence modules (never fail)
- Aggregate results into `GuardrailBundle`
- If enforcing checks fail → replace answer with refusal

----------------------------------------------------
STEP 7 — Trace & Persistence
----------------------------------------------------
- Build structured trace payload including:
  - scope debug
  - injection debug
  - guardrail results
- Store assistant message + citations + trace
- Return final content + trace_id
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any

from app.core.utils import get_logger
from app.db.conn import get_conn
from app.services.persona_repository import (
    get_persona_profile,
    list_questions_for_persona,
    retrieve_relevant_answers,
)

# Guardrails as a single module boundary for the pipeline
from app.guardrails.manager import run_pre_guardrails
from app.guardrails.post.engine import run_post_enforcing_guardrails

from app.coherence.manager import run_monitors

from app.coherence.reporting.session_store import append_turn_result, get_session_turns
from app.coherence.reporting.session_report import (
    build_session_coherence_report,
    save_session_report_json,
    save_session_report_csv,
)

from app.llm.system_prompts import PromptSignals, TopicSignals, build_system_prompt

from app.services.models import (
    SessionInfo,
    GroundingBundle,
    LlmAnswerBundle,
)

from app.guardrails.gates.gates import (
    TopicGateBundle,
    InjectionGateBundle,
    GuardrailBundle,
)

log = get_logger(__name__)


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def _refuse_generic() -> str:
    return (
        "Sorry — I can’t help with that request. "
        "Please ask something related to the persona’s background or views."
    )


def _steer_generic() -> str:
    return (
        "I can’t help with that. "
        "If you want, ask a question about the persona’s background or views (based on the profile and recorded answers)."
    )


# ======================================================================================================================
#                                          STEP 1 — Session + persona loading
# ======================================================================================================================

def load_session_info(session_id: str) -> SessionInfo:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM chat_sessions WHERE session_id=?", (session_id,)).fetchone()
    if not row:
        raise ValueError("Invalid session")
    d = dict(row)
    return SessionInfo(
        session_id=d["session_id"],
        persona_id=d["persona_id"],
        snapshot_id=d["snapshot_id"],
        model_version=d["model_version"],
    )


def load_persona_profile(persona_id: str, snapshot_id: str) -> dict[str, Any]:
    profile = get_persona_profile(persona_id, snapshot_id)
    if not profile:
        raise ValueError("Persona not found")
    return profile


# ======================================================================================================================
#                                          STEP 2 — Persist user message
# ======================================================================================================================

def store_user_message(session_id: str, user_text: str) -> str:
    message_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages
            (message_id, session_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, session_id, "user", user_text, utc_now_iso()),
        )
        conn.commit()
    return message_id


# ======================================================================================================================
#                                  STEP 3 — Retrieval: build grounding bundle
# ======================================================================================================================

def build_grounding_bundle(
    *,
    persona_id: str,
    snapshot_id: str,
    profile: dict[str, Any],
    user_text: str,
) -> GroundingBundle:
    retrieved = retrieve_relevant_answers(persona_id, snapshot_id, user_text, k=4)
    answers = [r for r in retrieved if r.score >= 0.25]
    suggested_questions = list_questions_for_persona(persona_id, snapshot_id)

    answers_payload: list[dict[str, Any]] = [
        {
            "question_id": a.question_id,
            "question_text": a.question_text,
            "answer_value": a.answer_value,
            "answer_text": a.answer_text,
            "wave": a.wave,
            "confidence": a.confidence,
        }
        for a in answers
    ]

    return GroundingBundle(
        persona_id=persona_id,
        snapshot_id=snapshot_id,
        profile=profile,
        answers=answers_payload,
        suggested_questions=suggested_questions,
    )


# ======================================================================================================================
#                    STEP 4 — PRE-LLM guardrails entrypoint (combined validator + mapping)
# ======================================================================================================================
'''
This stage evaluates the incoming user message BEFORE it reaches
the persona answer-generation LLM.

It acts as the input boundary protection layer.

IMPORTANT DISTINCTION:

   - Injection Gate        → Protects against manipulation attempts
   - Topic/Scope Gate      → Protects against off-profile or irrelevant content

------------------------------------
SUBSTEPS:
------------------------------------
4.1 — Run Combined Validator (LLM-as-Judge)
       - Uses a clean validation prompt
       - Evaluates:
           • Prompt injection signals
           • Topic relevance
           • Scope boundaries
           • Segment-level decisions
       - Produces structured JSON output
       - Does NOT generate a persona answer

4.2 — Injection Analysis & Mapping
       - Compute lexical injection score
       - Interpret validator injection signals
       - Decide injection_action:
             • allow
             • sanitize
             • refuse
       - Produce sanitized `user_for_llm` if needed
       - Map to InjectionGateBundle

4.3 — Topic / Scope Analysis & Mapping
       - Interpret validator scope decisions
       - Segment user input if mixed relevance
       - Identify:
             • kept_segments
             • dropped_segments
       - Determine overall_tier:
             • allow
             • steer
             • deny
       - Derive topic_action:
             • ANSWER
             • CAUTIOUS
             • REFUSE
       - Map to TopicGateBundle

4.4 — Action Derivation
       - Combine injection and scope outcomes
       - Determine whether pipeline:
             • Proceeds to LLM answer generation
             • Steers user
             • Refuses early
       - No persona answer is generated at this stage

------------------------------------
OUTPUT:
------------------------------------
- InjectionGateBundle
- TopicGateBundle
- Combined validator debug payload

If overall_tier == deny OR injection_action == refuse:
   → Pipeline may short-circuit before LLM generation.
'''

# NOTE:
# The pre-guardrails implementation lives in app/guardrails/manager.py.
# We intentionally do NOT re-define run_pre_guardrails here, to avoid
# shadowing the imported entrypoint and causing NameError/circular issues.


def log_injection_debug(user_text: str, inj: InjectionGateBundle) -> None:
    lines: list[str] = []
    lines.append("\n========== INJECTION (PRE) DEBUG ==========")
    lines.append(f"ORIGINAL: {user_text!r}")
    lines.append(f"ACTION: {inj.injection_action}")
    lines.append(f"LEXICAL_SCORE: {inj.lexical_score}")
    lines.append(f"JUDGE_USED: {inj.judge_used}")
    lines.append(f"USER_FOR_LLM: {inj.user_for_llm!r}")
    mode = (inj.debug or {}).get("mode")
    lines.append(f"MODE: {mode}")
    lines.append("===========================================\n")
    log.info("\n".join(lines))


def log_topic_debug(user_text: str, gate: TopicGateBundle) -> None:
    debug_block = gate.debug or {}
    items = debug_block.get("items") or []

    lines: list[str] = []
    lines.append("\n========== TOPIC (PRE) DEBUG ==========")
    lines.append(f"ORIGINAL: {user_text!r}")
    lines.append(f"ITEMS: {len(items)}")
    for i, it in enumerate(items, 1):
        lines.append(
            f"{i:02d}. {it.get('text')!r} | DECISION={it.get('decision')} | SCOPE={it.get('scope')} | TOPIC={it.get('topic_label')}"
        )
    lines.append(f"KEPT: {gate.kept_segments}")
    lines.append(f"DROPPED: {gate.dropped_segments}")
    lines.append(f"OVERALL_TIER: {gate.overall_tier}")
    lines.append(f"TOPIC_ACTION: {gate.topic_action}")
    lines.append(f"USER_FOR_LLM: {gate.user_for_llm!r}")
    lines.append("=======================================\n")
    log.info("\n".join(lines))


# ======================================================================================================================
#                         STEP 5 — Build prompt signals + answer via LLM (LLM call #2)
# ======================================================================================================================
'''
This stage generates the persona's answer using the main "actor" LLM.

It consumes:
- The PRE-gate decisions (TopicGateBundle + InjectionGateBundle)
- The grounding bundle (profile + retrieved Q/A evidence)
- A dynamically constructed system prompt that encodes allowed behavior

IMPORTANT DISTINCTION:

   - System Prompt Builder  → Encodes policy + persona constraints (control layer)
   - Answer Generation LLM   → Produces the actual response (actor layer)

------------------------------------
SUBSTEPS:
------------------------------------
5.1 — Build Prompt Signals (Policy Encoding)
       - Convert TopicGateBundle → PromptSignals / TopicSignals
       - Embed tier + action into the system prompt:
           • tier: allow / steer / deny
           • action: ANSWER / CAUTIOUS / REFUSE
       - Mark whether user input contained irrelevant segments (has_irrelevant)
       - Produce final system prompt via build_system_prompt(signals)

5.2 — Construct Grounding Payload (Evidence Pack)
       - Assemble structured context for the actor LLM:
           • persona_id + snapshot_id
           • persona profile fields
           • retrieved relevant answers (top-k, filtered)
           • suggested questions list
       - Include scope metadata for downstream logging / behavior control
       - NOTE: This payload is the ONLY permitted knowledge source beyond the system prompt

5.3 — Execute LLM Call (Actor Generation)
       - Call provider.generate(system, user, grounding)
       - user input is `user_for_llm` (sanitized by pre-guardrails)
       - system prompt is the dynamic prompt from 5.1
       - grounding is the structured payload from 5.2

5.4 — Retry & Failure Handling
       - Retry up to max_retries on transient provider errors
       - Backoff between attempts (sleep)
       - If all attempts fail:
           • return a fallback LlmAnswerBundle
           • mark safety metadata as provider error

5.5 — Normalize Provider Response
       - Extract:
           • content
           • citations
           • safety metadata (if provided)
       - Ensure defaults for missing fields
       - Log preview of raw content for trace/debug

------------------------------------
OUTPUT:
------------------------------------
- LlmAnswerBundle
    • content: final assistant response text (pre post-guardrails)
    • citations: any grounding references if provider supports them
    • safety: provider metadata (optional)

This output is NOT final yet:
it will still be evaluated by STEP 6 post-LLM enforcing guardrails.
'''

def build_answer_system_prompt(gate: TopicGateBundle) -> str:
    signals = PromptSignals(
        topic=TopicSignals(
            user_score=0.0,
            tier=gate.overall_tier,
            action=gate.topic_action,
            reason="combined_validator",
            has_irrelevant=gate.has_mixed,
        ),
        validators=[],
    )
    return build_system_prompt(signals)


async def generate_answer(
    *,
    provider: Any,
    system_prompt: str,
    user_for_llm: str,
    grounding: GroundingBundle,
    max_retries: int = 3,
) -> LlmAnswerBundle:
    attempt = 0
    llm = None

    grounding_payload: dict[str, Any] = {
        "persona_id": grounding.persona_id,
        "snapshot_id": grounding.snapshot_id,
        "profile": grounding.profile,
        "answers": grounding.answers,
        "suggested_questions": grounding.suggested_questions,
        "scope": {"tier": "allow"},
    }

    while attempt < max_retries:
        try:
            llm = await provider.generate(system=system_prompt, user=user_for_llm, grounding=grounding_payload)
            break
        except Exception as e:
            attempt += 1
            log.error("[PIPELINE] LLM attempt %s failed: %s", attempt, str(e))
            await asyncio.sleep(1.5)

    if llm is None:
        return LlmAnswerBundle(
            content="The persona is temporarily unavailable.",
            citations=[],
            safety={"provider": "error", "action": "fallback"},
        )

    content = getattr(llm, "content", "") or ""
    citations = getattr(llm, "citations", []) or []
    safety = getattr(llm, "safety", None)

    log.info("[PIPELINE] LLM raw content: %s", content[:300])
    return LlmAnswerBundle(content=content, citations=citations, safety=safety)


# ======================================================================================================================
#                            STEP 6 — POST-LLM: enforcing guardrails + coherence
# ======================================================================================================================
'''
This stage evaluates the generated LLM answer before returning it to the user.

IMPORTANT DISTINCTION:

   - Enforcing Guardrails  → Can refuse / replace answer
   - Monitoring Modules    → Never refuse (analytics only)

------------------------------------
SUBSTEPS:
------------------------------------
6.1 — Build Unified Post Context
       - Includes:
           • Persona profile
           • Retrieved answers
           • Suggested questions
           • Original user input
           • Sanitized user input (after pre-gate)
           • Raw LLM output
           • Pre-check debug info

6.2 — Run Enforcing Guardrails
       - Grounding enforcement
       - Identity drift checks
       - Scope violation checks
       - Safety violations
       - Returns GuardrailResult objects
       - Failures are aggregated

6.3 — Run Monitoring Modules
       - Drift scoring
       - Style deviation
       - Confidence scoring
       - Risk signals
       - These NEVER block the response

 6.4 — Aggregate Results
       - GuardrailBundle.results → enforcing + coherence
       - GuardrailBundle.failed  → enforcing failures only
       - ok flag derived from enforcing failures

 6.5 — Enforcement Decision
       - If enforcing failures exist:
             replace answer with generic refusal
       - Otherwise:
             allow answer through

------------------------------------
OUTPUT:
------------------------------------
- GuardrailBundle
'''

def build_post_context(
    *,
    session_id: str,
    persona_id: str,
    snapshot_id: str,
    user_text: str,
    user_for_llm: str,
    grounding: GroundingBundle,
    llm_answer: LlmAnswerBundle,
    topic_debug: dict[str, Any],
    injection_debug: dict[str, Any],
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "persona_id": persona_id,
        "snapshot_id": snapshot_id,
        "profile": grounding.profile,
        "answers": grounding.answers,
        "suggested_questions": grounding.suggested_questions,
        "llm_output": llm_answer.content,
        "citations": llm_answer.citations,
        "user_text": user_text,
        "user_relevant_text": user_for_llm,
        "topic_precheck": topic_debug,
        "injection_precheck": injection_debug,
    }


async def run_post_checks(
    *,
    session_id: str,
    persona_id: str,
    snapshot_id: str,
    user_text: str,
    user_for_llm: str,
    grounding: GroundingBundle,
    llm_answer: LlmAnswerBundle,
    gate_debug: dict[str, Any],
    injection_debug: dict[str, Any],
) -> GuardrailBundle:
    """
    Runs BOTH:
    - enforcing post guardrails (can force refusal)
    - coherence modules (never force refusal)

    GuardrailBundle.failed contains only enforcing failures.
    GuardrailBundle.results contains enforcing + coherence results.
    """
    context = build_post_context(
        session_id=session_id,
        persona_id=persona_id,
        snapshot_id=snapshot_id,
        user_text=user_text,
        user_for_llm=user_for_llm,
        grounding=grounding,
        llm_answer=llm_answer,
        topic_debug=gate_debug,
        injection_debug=injection_debug,
    )

    enforcing_results = await run_post_enforcing_guardrails(context)
    monitoring_results = await run_monitors(context)

    # ----------------------------
    # Coherence reporting (per session)
    # ----------------------------
    session_id = context["session_id"]

    # turn index = number of assistant turns seen so far in this session + 1
    # since we are still before storing the assistant message in DB
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM chat_messages
            WHERE session_id=? AND role='assistant'
            """,
            (session_id,),
        ).fetchone()

    prior_assistant_turns = int(dict(row)["n"]) if row else 0
    turn_index = prior_assistant_turns + 1

    append_turn_result(
        session_id=session_id,
        turn_index=turn_index,
        user_text=user_text,
        assistant_output=llm_answer.content,
        monitor_results=monitoring_results,
    )

    turn_records = get_session_turns(session_id)

    report = build_session_coherence_report(
        session_id=session_id,
        persona_id=persona_id,
        snapshot_id=snapshot_id,
        turn_records=turn_records,
    )

    json_path = save_session_report_json(report)
    csv_path = save_session_report_csv(report)

    log.info(
        "[COHERENCE REPORT] session=%s json=%s csv=%s",
        session_id,
        str(json_path),
        str(csv_path),
    )

    failed = [r for r in enforcing_results if not r.ok]
    ok = not bool(failed)

    return GuardrailBundle(results=[*enforcing_results, *monitoring_results], ok=ok, failed=failed)


def enforce_post_checks_or_refuse(answer: LlmAnswerBundle, guardrails: GuardrailBundle) -> LlmAnswerBundle:
    """
    Enforce only POST enforcing guardrails.
    Monitoring can never refuse because it never appears in guardrails.failed.
    """
    if guardrails.ok:
        return answer

    return LlmAnswerBundle(
        content=_refuse_generic(),
        citations=[],
        safety={"action": "refuse_post_enforced"},
    )


# ======================================================================================================================
#                              STEP 7 — Persistence: store assistant output + trace
# ======================================================================================================================

def build_trace_payload(
    *,
    session: SessionInfo,
    gate_debug: dict[str, Any],
    injection_debug: dict[str, Any],
    guardrails: GuardrailBundle,
) -> dict[str, Any]:
    trace_id = str(uuid.uuid4())
    return {
        "trace_id": trace_id,
        "persona_id": session.persona_id,
        "snapshot_id": session.snapshot_id,
        "model_version": session.model_version,
        "topic_debug": gate_debug,
        "injection_debug": injection_debug,
        "guardrails": [{"name": r.name, "ok": r.ok, "details": r.details} for r in guardrails.results],
    }


def store_assistant_message(
    *,
    session: SessionInfo,
    content: str,
    citations: list[Any],
    trace: dict[str, Any],
) -> tuple[str, str]:
    assistant_msg_id = str(uuid.uuid4())

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages
            (message_id, session_id, role, content, citations_json, trace_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (assistant_msg_id, session.session_id, "assistant", content, json.dumps(citations), json.dumps(trace), utc_now_iso()),
        )
        conn.commit()

    return assistant_msg_id, trace["trace_id"]