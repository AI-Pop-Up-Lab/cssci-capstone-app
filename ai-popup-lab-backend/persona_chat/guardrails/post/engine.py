from __future__ import annotations

from typing import Any

from app.core.utils import get_logger
from app.guardrails.contract import Guardrail, GuardrailResult
from app.guardrails.post.scope.guardrail import OutputScopeGuardrail

log = get_logger(__name__)


def _get_post_enforcing_guardrails() -> list[Guardrail]:
    """
    POST enforcing registry (kept private to avoid import sprawl).
    Add/remove enforcing post guardrails here.
    """
    return [
        OutputScopeGuardrail(),
    ]


async def run_post_enforcing_guardrails(context: dict[str, Any]) -> list[GuardrailResult]:
    """
    POST-LLM enforcing engine (single entrypoint).

    - owns the registry list
    - runs enforcing post guardrails sequentially
    - returns GuardrailResult list (pipeline decides whether to refuse)
    """
    results: list[GuardrailResult] = []

    for rail in _get_post_enforcing_guardrails():
        log.info("[GUARDRAILS][POST] Running: %s", rail.name)
        res = await rail.run(context)
        results.append(res)

        if not res.ok:
            log.warning("[GUARDRAILS][POST] %s failed | details=%s", rail.name, res.details)
        else:
            log.info("[GUARDRAILS][POST] %s passed", rail.name)

    return results