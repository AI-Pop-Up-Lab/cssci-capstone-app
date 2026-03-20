"""
app/guardrails/contract.py

============================================================
GUARDRAIL CONTRACTS
============================================================

This module defines the *contract* for guardrails and coherence modules.

Why "contract"?
---------------
Because this file defines stable, shared interfaces used across:
- guardrails (enforcing / gating checks)
- coherence modules (non-enforcing signals)
- orchestration layers (guardrails orchestrator, coherence orchestrator)
- pipeline code (collecting results, storing traces, tests)

Design goals
------------
- Minimal
- Stable
- Explicit
- No business logic
"""

from __future__ import annotations

from typing import Any


class GuardrailResult:
    """
    Standard result object returned by any guardrail/monitor module.

    Attributes
    ----------
    ok : bool
        True if the check passes. False if it fails.
        Note: monitors SHOULD almost always return ok=True.

    name : str
        Unique identifier for the module.

    details : dict
        JSON-serializable diagnostics for logging / trace storage.
    """

    def __init__(self, ok: bool, name: str, details: dict | None = None):
        self.ok = bool(ok)
        self.name = str(name)
        self.details = details or {}


class Guardrail:
    """
    Base interface for any check that runs over a shared runtime `context`.

    Concrete modules must:
    - set `name`
    - implement async `run(context)` returning GuardrailResult
    """

    name: str = "base"

    async def run(self, context: dict[str, Any]) -> GuardrailResult:
        raise NotImplementedError