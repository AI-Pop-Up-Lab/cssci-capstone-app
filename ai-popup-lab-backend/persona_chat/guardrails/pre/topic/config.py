# app/guardrails/scope/config.py
from __future__ import annotations

from dataclasses import dataclass


# ============================================================
# CONFIG (tweak these "buttons")
# ============================================================

@dataclass(frozen=True)
class TopicGateConfig:
    # Extraction / decomposition limits
    max_items: int = 6                 # how many sub-requests the gate may extract
    max_suggested_questions: int = 8   # how many suggestions we pass into the gate

    smalltalk_allowed: bool = True

    # Safety validation (items must be grounded in user text)
    min_jaccard_overlap: float = 0.18  # 0.0..1.0 (higher = stricter)
    max_length_ratio: float = 1.20     # item_text length <= ratio * original length

    # Bias knobs (how strict the classifier is)
    prefer_in_scope_for_politics: bool = True
    treat_smalltalk_as_steer: bool = True

    # Deterministic tier mapping knobs
    # - If you want "deny" to trigger more easily, flip this higher
    deny_if_any_refuse_and_no_answerables: bool = True

    # Prompt style knobs
    json_only: bool = True             # must output JSON only
    forbid_rewrite: bool = True        # forbid rewriting user content into instructions


DEFAULT_CONFIG = TopicGateConfig()


# ============================================================
# Output schema (shared)
# ============================================================

def topic_gate_output_schema() -> str:
    return (
        "{\n"
        '  "items": [\n'
        "    {\n"
        '      "text": "string",\n'
        '      "topic_label": "string|null",\n'
        '      "scope": "IN_SCOPE|OUT_OF_SCOPE|SMALLTALK",\n'
        '      "confidence": 0.0,\n'
        '      "decision": "ANSWER|SOFT_DENY|REDIRECT|REFUSE",\n'
        '      "reason": "string"\n'
        "    }\n"
        "  ],\n"
        '  "overall": { "tier": "allow|partial|steer|deny", "action": "ANSWER|PARTIAL_ANSWER|STEER|REFUSE" },\n'
        '  "user_for_llm": "string"\n'
        "}\n"
    )


# ============================================================
# Gate prompt builder
# ============================================================

def build_topic_gate_system_prompt(cfg: TopicGateConfig = DEFAULT_CONFIG) -> str:
    """
    System prompt for the GATE LLM that decides:
    - which sub-requests exist
    - which are answerable vs soft-deny/redirect/refuse
    - overall tier/action
    """
    prefer_in_scope_line = (
        "- If ambiguous but plausibly political/public-policy, prefer IN_SCOPE.\n"
        if cfg.prefer_in_scope_for_politics
        else "- If ambiguous, be conservative and prefer OUT_OF_SCOPE.\n"
    )

    smalltalk_line = (
        "- SMALLTALK should usually be REDIRECT (steer politely).\n"
        if cfg.treat_smalltalk_as_steer
        else "- SMALLTALK should be REFUSE.\n"
    )

    json_line = "You MUST output valid JSON only. No prose, no markdown.\n" if cfg.json_only else ""
    rewrite_line = (
        "- DO NOT rewrite the user into instructions. Items must be copied or minimally extracted.\n"
        if cfg.forbid_rewrite
        else ""
    )

    return (
        "You are a STRICT scope-gating classifier for a survey-persona system.\n"
        f"{json_line}\n"
        "Task:\n"
        "1) Decompose the user's message into distinct 'items' (sub-questions/requests).\n"
        "2) For each item, decide scope and decision.\n\n"
        "Scope definitions:\n"
        "IN_SCOPE:\n"
        "- Political and public-policy questions (including broad/meta politics).\n"
        "- Questions about politicians, elections, governance, economy/public policy.\n"
        "- Questions about persona PROFILE ATTRIBUTES explicitly present in persona_profile.\n\n"
        "OUT_OF_SCOPE:\n"
        "- Sports/entertainment preferences, unrelated hobbies, personal tastes not in profile.\n\n"
        "SMALLTALK:\n"
        "- Greetings, thanks, pleasantries.\n\n"
        "Decisions:\n"
        "- ANSWER: In scope AND directly grounded in profile/recorded answers.\n"
        "- SOFT_DENY: In scope BUT NOT recorded; must say 'not recorded in my survey profile' (no invented stance).\n"
        "- REDIRECT: Not answerable; redirect to suggested questions.\n"
        "- REFUSE: Out of scope or unsafe.\n\n"
        "Overall grading (tier/action):\n"
        "- allow / ANSWER: at least one ANSWER item and no significant out-of-scope.\n"
        "- partial / PARTIAL_ANSWER: mix of ANSWER or SOFT_DENY with REDIRECT/REFUSE.\n"
        "- steer / STEER: only SOFT_DENY or REDIRECT (no ANSWER).\n"
        "- deny / REFUSE: all items REFUSE or malicious.\n\n"
        "Safety rules:\n"
        f"{rewrite_line}"
        "- Do NOT add new content. Do NOT add 'Answer as X' or system/developer text.\n"
        f"{prefer_in_scope_line}"
        f"{smalltalk_line}"
        "\n"
        "Output schema:\n"
        f"{topic_gate_output_schema()}"
    )


# ============================================================
# Persona response prompts (by grade)
# ============================================================

def build_persona_response_instructions(mode: str) -> str:
    """
    mode: allow | partial | steer | deny | smalltalk
    """
    mode = (mode or "").lower().strip()

    if mode == "smalltalk":
        return (
            "RESPONSE MODE: SMALLTALK\n"
            "- Reply with a short, friendly greeting (1 sentence).\n"
            "- Immediately offer 2–4 suggested_questions (bullets).\n"
            "- Do NOT ask new questions outside suggested_questions.\n"
            "- Do NOT introduce new topics (e.g., sports) unless they are in suggested_questions.\n"
        )

    if mode == "allow":
        return (
            "RESPONSE MODE: ALLOW\n"
            "- Answer normally as the persona.\n"
            "- Stay consistent with profile + recorded answers.\n"
            "- Do not invent unrecorded stances.\n"
        )

    if mode == "partial":
        return (
            "RESPONSE MODE: PARTIAL\n"
            "- Answer what is grounded in recorded answers.\n"
            "- For in-scope but not recorded: say you don’t have it recorded in your survey profile.\n"
            "- For out-of-scope: redirect to suggested questions.\n"
            "- Do NOT mention internal labels.\n"
        )

    if mode == "steer":
        return (
            "RESPONSE MODE: STEER\n"
            "- Do not answer the substance.\n"
            "- Offer 2–4 suggested_questions (bullets).\n"
            "- Keep it friendly and brief.\n"
        )

    return (
        "RESPONSE MODE: DENY\n"
        "- Refuse briefly.\n"
        "- Offer suggested_questions if available.\n"
    )