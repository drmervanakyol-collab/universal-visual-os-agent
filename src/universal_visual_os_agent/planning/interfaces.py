"""Planner interfaces."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.planning.models import PlannerDecision
from universal_visual_os_agent.recovery.models import RecoverySnapshot


class Planner(Protocol):
    """Planner abstraction for forward progress."""

    def plan(self) -> PlannerDecision:
        """Produce the next planning decision."""


class RecoveryPlanner(Protocol):
    """Planner abstraction for restart reconciliation."""

    def plan_recovery(self, snapshot: RecoverySnapshot) -> PlannerDecision:
        """Produce a recovery-focused planning decision."""

