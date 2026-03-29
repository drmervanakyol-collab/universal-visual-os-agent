"""Policy engine interfaces."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.actions.models import ActionIntent
from universal_visual_os_agent.policy.models import PolicyDecision


class PolicyEngine(Protocol):
    """Policy engine for action intent review."""

    def evaluate(self, action: ActionIntent) -> PolicyDecision:
        """Review an action intent before execution or simulation."""

