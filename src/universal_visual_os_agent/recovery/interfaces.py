"""Recovery loading and reconciliation contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Mapping, Protocol

from universal_visual_os_agent.recovery.models import (
    ReconciliationResult,
    RecoveryFailureOrigin,
    RecoveryPlanningResult,
    RecoverySnapshot,
)

if TYPE_CHECKING:
    from universal_visual_os_agent.actions.tool_boundary_models import ActionToolBoundaryAssessment
    from universal_visual_os_agent.ai_architecture.escalation_engine import DeterministicEscalationDecision
    from universal_visual_os_agent.verification.models import VerificationResult


class RecoverySnapshotLoader(Protocol):
    """Load persisted recovery state without touching live OS state."""

    def load_latest(self, task_id: str) -> RecoverySnapshot | None:
        """Return the latest recovery snapshot for a task, if available."""


class StateReconciler(Protocol):
    """Compare recovered state to current observed or replayed state."""

    def reconcile(
        self,
        snapshot: RecoverySnapshot,
        observed_state: Mapping[str, object] | None = None,
    ) -> ReconciliationResult:
        """Produce a reconciliation result without performing live actions."""


class RecoveryEscalationHitlPlanner(Protocol):
    """Plan conservative recovery, escalation, and HITL next steps."""

    def plan_from_escalation_decision(
        self,
        decision: "DeterministicEscalationDecision",
    ) -> RecoveryPlanningResult:
        """Return a failure-safe recovery plan derived from an escalation decision."""

    def plan_from_tool_boundary_assessment(
        self,
        assessment: "ActionToolBoundaryAssessment",
    ) -> RecoveryPlanningResult:
        """Return a failure-safe recovery plan derived from a final tool-boundary assessment."""

    def plan_from_verification_result(
        self,
        result: "VerificationResult",
    ) -> RecoveryPlanningResult:
        """Return a failure-safe recovery plan derived from verification output."""

    def plan_for_human_confirmation(
        self,
        *,
        summary: str,
        failure_origin: RecoveryFailureOrigin,
        metadata: Mapping[str, object] | None = None,
    ) -> RecoveryPlanningResult:
        """Return a failure-safe HITL plan without requiring a real operator UI."""
