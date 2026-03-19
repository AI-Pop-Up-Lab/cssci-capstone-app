from __future__ import annotations

from typing import Any

from app.core.utils import get_logger
from app.guardrails.contract import Guardrail, GuardrailResult

from app.coherence.post.persona_l2l.config import DEFAULT_CONFIG, PersonaL2LConfig
from app.coherence.post.persona_l2l.gate import run_persona_l2l_gate
from app.coherence.post.persona_l2l.mapper import map_persona_l2l_to_result

log = get_logger(__name__)


class PersonaLineToLineMonitor(Guardrail):
    name = "persona_line_to_line"

    def __init__(self, cfg: PersonaL2LConfig = DEFAULT_CONFIG) -> None:
        self.cfg = cfg

    async def run(self, context: dict[str, Any]) -> GuardrailResult:
        gate_res = await run_persona_l2l_gate(context=context, cfg=self.cfg)

        if gate_res.issue:
            log.warning("[MONITOR] %s issue=%s notes=%s", self.name, gate_res.issue, gate_res.notes)
        else:
            log.info("[MONITOR] %s ok", self.name)

        return map_persona_l2l_to_result(name=self.name, gate=gate_res)