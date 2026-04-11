"""Typed containers used by the guardrailed response pipeline."""

from dataclasses import dataclass, field


# =============================================================================
# Input and Signal Models
# =============================================================================

@dataclass(slots=True)
class GuardrailInput:
    """Container for the runtime inputs needed by the guardrail pipeline."""

    persona_biography: str
    stylometric_profile: dict
    user_message: str
    chat_history: list[dict]
    session_trace: "GuardrailSessionTrace"


@dataclass(slots=True)
class GuardrailSessionTrace:
    """Session metadata used for per-session transcript logging."""

    session_id: str
    persona_key: str
    persona_label: str
    log_path: str
    turn_index: int
    is_new_session: bool = False


@dataclass(slots=True)
class LexicalSignal:
    """Signal produced by prompt-injection term detection."""

    triggered: bool
    matched_terms: list[str] = field(default_factory=list)
    risk_level: str = "low"


@dataclass(slots=True)
class RelevanceSignal:
    """Signal produced by the relevance preparation layer."""

    summary: str = ""
    judge_prompt: str = ""


@dataclass(slots=True)
class EpistemicSignal:
    """Signal produced by the epistemic preparation layer."""

    summary: str = ""
    judge_prompt: str = ""


@dataclass(slots=True)
class StylometricSignal:
    """Signal produced by the stylometric preparation layer."""

    summary: str = ""
    judge_prompt: str = ""


@dataclass(slots=True)
class GuardrailSignals:
    """Bundle of all pre-judge checks passed into policy selection."""

    lexical: LexicalSignal
    relevance: RelevanceSignal
    epistemic: EpistemicSignal
    stylometric: StylometricSignal


# =============================================================================
# Policy Models
# =============================================================================

@dataclass(slots=True)
class PolicyDecision:
    """Policy outcome that controls how the final response is produced."""

    action: str
    rationale: str
    response_guidance: str
    response_length_target: str = "short"
    detail_allowed: bool = False
    expertise_basis: str = "none"
    hedging_style: str = "medium"
    confidence_style: str = "balanced"
    register_style: str = "everyday"
    sentence_style: str = "mixed"
    abstraction_level: str = "mixed"
    vocabulary_level: str = "moderate"
    explanation_style: str = "balanced"
    lexical_score: float = 0.0
    relevance_score: float = 0.0
    epistemic_score: float = 0.0
    knowledge_level: str = "limited"
    language_level: str = "plain"
    tone_style: str = "calm"
    emotional_style: str = "neutral"
