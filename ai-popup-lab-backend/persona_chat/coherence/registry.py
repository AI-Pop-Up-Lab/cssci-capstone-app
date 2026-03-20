from __future__ import annotations

from typing import Any

from app.coherence.post.persona_p2l.monitor import PersonaPromptToLineMonitor
from app.coherence.post.persona_l2l.monitor import PersonaLineToLineMonitor


def get_monitors() -> list[Any]:
    """
    Add/remove monitors here.
    Monitors should always return ok=True and only provide details.
    """
    return [
        PersonaPromptToLineMonitor(),
        PersonaLineToLineMonitor(),
    ]