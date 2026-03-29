"""Action executor interfaces."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.actions.models import ActionIntent, ActionResult


class ActionExecutor(Protocol):
    """Executor contract for simulated or future live actions."""

    def execute(self, action: ActionIntent) -> ActionResult:
        """Handle an action intent without assuming live OS control."""

