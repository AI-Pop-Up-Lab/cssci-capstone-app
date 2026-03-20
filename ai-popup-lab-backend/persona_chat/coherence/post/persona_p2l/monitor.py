from __future__ import annotations

from typing import Any

from app.core.utils import get_logger
from app.guardrails.contract import Guardrail, GuardrailResult

from app.coherence.post.persona_p2l.config import PersonaP2LConfig, DEFAULT_CONFIG
from app.coherence.post.persona_p2l.gate import run_persona_p2l_gate
from app.coherence.post.persona_p2l.mapper import map_persona_p2l_to_result


log = get_logger(__name__)


class PersonaPromptToLineMonitor(Guardrail):
    """
    Persona prompt-to-line coherence monitor (POST, monitor-only).

    Detects inconsistencies between:
      - persona profile / stored answers
      - generated assistant output
    """
    name = "persona_prompt_to_line"

    def __init__(self, cfg: PersonaP2LConfig = DEFAULT_CONFIG) -> None:
        self.cfg = cfg

    async def run(self, context: dict[str, Any]) -> GuardrailResult:
        gate_res = await run_persona_p2l_gate(context=context, cfg=self.cfg)

        if gate_res.issue:
            log.warning("[MONITOR] %s issue=%s verdict=%s score=%.3f", self.name, gate_res.issue, gate_res.verdict, gate_res.coherence_score)
        else:
            log.info("[MONITOR] %s ok verdict=%s score=%.3f", self.name, gate_res.verdict, gate_res.coherence_score)

        return map_persona_p2l_to_result(name=self.name, gate=gate_res)