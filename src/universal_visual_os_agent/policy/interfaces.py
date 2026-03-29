"""Policy engine and safety hook interfaces."""

from __future__ import annotations

from typing import Mapping, Protocol

from universal_visual_os_agent.actions.models import ActionIntent
from universal_visual_os_agent.policy.models import (
    KillSwitchState,
    PauseState,
    PolicyDecision,
    PolicyEvaluationContext,
    ProtectedContextAssessment,
)


class ProtectedContextDetector(Protocol):
    """Hook for identifying protected contexts before execution."""

    def assess(
        self,
        action: ActionIntent,
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> ProtectedContextAssessment:
        """Assess whether the action targets a protected context."""


class KillSwitch(Protocol):
    """Kill switch abstraction for globally blocking actions."""

    def snapshot(self) -> KillSwitchState:
        """Return the current kill-switch state."""


class PauseController(Protocol):
    """Pause/resume abstraction for action gating."""

    def snapshot(self) -> PauseState:
        """Return the current pause state."""


class PolicyEngine(Protocol):
    """Policy engine for action intent review."""

    def evaluate(
        self,
        action: ActionIntent,
        *,
        context: PolicyEvaluationContext | None = None,
    ) -> PolicyDecision:
        """Review an action intent before execution or simulation."""
