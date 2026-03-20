from __future__ import annotations

from app.core.utils import get_logger
from app.guardrails.contract import Guardrail, GuardrailResult

from app.guardrails.post.scope.gate import llm_topic_gate
from app.guardrails.post.scope.mapper import map_relevance_to_guardrail_result
from app.guardrails.post.scope.config import DEFAULT_CONFIG, TopicGateConfig

log = get_logger(__name__)


class OutputScopeGuardrail(Guardrail):
    """
    POST enforcing guardrail unit.

    Purpose:
    - Implements the Guardrail contract (run -> GuardrailResult)
    - Delegates to scope module internals:
        * gate.py   (decision logic + bypass)
        * lexical.py (scoring)
        * mapper.py (standardize output)
        * config.py (thresholds)
    """

    name = "output_scope_check"

    def __init__(self, cfg: TopicGateConfig = DEFAULT_CONFIG) -> None:
        self.cfg = cfg

    async def run(self, context: dict) -> GuardrailResult:
        gate_res = await llm_topic_gate(context=context, cfg=self.cfg)

        if gate_res.bypassed:
            log.info("[GUARDRAILS][POST] %s bypassed (%s)", self.name, gate_res.bypass_reason)
            return GuardrailResult(ok=True, name=self.name, details={"reason": gate_res.bypass_reason})

        rel = gate_res.relevance
        if rel is None:
            return GuardrailResult(ok=False, name=self.name, details={"reason": "missing_relevance"})

        res = map_relevance_to_guardrail_result(
            name=self.name,
            relevance=rel,
            min_output_score=self.cfg.min_output_score,
        )

        log.info(
            "[GUARDRAILS][POST] %s score=%.4f ok=%s tier=%s reason=%s",
            self.name,
            res.details.get("output_score", 0.0),
            res.ok,
            res.details.get("tier"),
            res.details.get("reason"),
        )
        return res