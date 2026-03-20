"""
app/coherence/manager.py

============================================================
MONITORING ORCHESTRATOR (PIPELINE ENTRYPOINT)
============================================================

Monitoring is post-generation and NEVER enforces refusal.

This module:
- defines the coherence module registry
- runs monitors sequentially
- returns GuardrailResult list for trace storage
"""

from __future__ import annotations

import time
from typing import Any

from app.core.utils import get_logger
from app.guardrails.contract import GuardrailResult

from app.coherence.registry import get_monitors


log = get_logger(__name__)


async def run_monitors(context: dict[str, Any]) -> list[GuardrailResult]:
    """
    Runs all registered coherence monitors sequentially.

    Hard rules:
      - Must never raise (monitoring must not break user responses)
      - Must never enforce refusal (monitors should return ok=True)
    """
    results: list[GuardrailResult] = []

    monitors = get_monitors()
    log.info("[MONITORING] Monitors enabled: %s", [m.name for m in monitors])

    for m in monitors:
        start = time.perf_counter()
        try:
            log.info("[MONITORING] Running: %s", m.name)
            res = await m.run(context)
        except Exception as e:
            # Monitoring must never crash the main pipeline.
            duration_ms = int((time.perf_counter() - start) * 1000)
            log.exception("[MONITORING] %s crashed (suppressed). duration_ms=%s", m.name, duration_ms)

            # Create a synthetic result so trace still shows what happened.
            res = GuardrailResult(
                ok=True,
                name=m.name,
                details={
                    "mode": "monitor_only",
                    "issue": "monitor_exception",
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
            )
        else:
            duration_ms = int((time.perf_counter() - start) * 1000)

            # Attach duration into details (without losing existing details).
            # GuardrailResult.details should be dict; if not, coerce.
            try:
                if isinstance(res.details, dict):
                    res.details.setdefault("duration_ms", duration_ms)
                else:
                    res.details = {"duration_ms": duration_ms, "raw_details": res.details}
            except Exception:
                # Don't allow detail mutation to crash monitoring
                pass

            # Coherence monitors *should* always return ok=True
            if not res.ok:
                log.warning("[MONITORING] %s returned ok=False (unexpected) | details=%s", m.name, res.details)
            else:
                # If the monitor surfaced an issue, log it clearly
                issue = res.details.get("issue") if isinstance(res.details, dict) else None
                if issue:
                    log.warning("[MONITORING] %s issue=%s duration_ms=%s", m.name, issue, duration_ms)
                else:
                    log.info("[MONITORING] %s ok duration_ms=%s", m.name, duration_ms)

        results.append(res)

    return results