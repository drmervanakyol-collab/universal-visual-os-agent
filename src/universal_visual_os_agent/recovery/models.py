"""Recovery model types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.persistence.models import CheckpointRecord, TaskRecord


@dataclass(slots=True, frozen=True, kw_only=True)
class RecoverySnapshot:
    """Recovered execution context loaded from persistence."""

    task: TaskRecord
    checkpoint: CheckpointRecord
    loaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def task_id(self) -> str:
        """Expose the recovered task identifier."""

        return self.task.task_id

    @property
    def checkpoint_id(self) -> str:
        """Expose the recovered checkpoint identifier."""

        return self.checkpoint.checkpoint_id

    @property
    def context(self) -> Mapping[str, object]:
        """Return recovery metadata needed for future reconciliation."""

        return self.checkpoint.recovery_metadata


@dataclass(slots=True, frozen=True, kw_only=True)
class ReconciliationResult:
    """Result of comparing recovered state against current knowledge."""

    safe_to_resume: bool
    summary: str
    reconciled_state: Mapping[str, object] = field(default_factory=dict)


class RecoveryFailureOrigin(StrEnum):
    """Origin domain for recovery, escalation, and HITL planning."""

    deterministic_escalation = "deterministic_escalation"
    tool_boundary = "tool_boundary"
    verification = "verification"
    scenario_action_flow = "scenario_action_flow"
    scenario_observe_flow = "scenario_observe_flow"


class RecoveryRetryability(StrEnum):
    """Whether a failure is considered safe to retry later."""

    retryable = "retryable"
    non_retryable = "non_retryable"
    not_applicable = "not_applicable"


class RecoveryEscalationOutcome(StrEnum):
    """Escalation outcome surfaced by recovery/HITL planning."""

    none = "none"
    local_resolver_recommended = "local_resolver_recommended"
    cloud_planner_recommended = "cloud_planner_recommended"
    human_confirmation_required = "human_confirmation_required"
    blocked = "blocked"


class HumanConfirmationStatus(StrEnum):
    """HITL readiness state without adding a real operator UI."""

    not_required = "not_required"
    required = "required"
    awaiting_user_confirmation = "awaiting_user_confirmation"


class RecoveryHandlingDisposition(StrEnum):
    """High-level downstream-facing recovery handling outcome."""

    no_recovery_needed = "no_recovery_needed"
    retry = "retry"
    escalate = "escalate"
    await_user_confirmation = "await_user_confirmation"
    blocked = "blocked"
    aborted = "aborted"


@dataclass(slots=True, frozen=True, kw_only=True)
class RecoveryHint:
    """One recovery hint that downstream runtime or operators can surface later."""

    hint_id: str
    summary: str
    next_expected_signal: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.hint_id:
            raise ValueError("hint_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class RecoveryHandlingPlan:
    """Structured recovery/escalation/HITL scaffold that remains non-executing."""

    failure_origin: RecoveryFailureOrigin
    disposition: RecoveryHandlingDisposition
    retryability: RecoveryRetryability
    summary: str
    escalation_outcome: RecoveryEscalationOutcome = RecoveryEscalationOutcome.none
    human_confirmation_status: HumanConfirmationStatus = HumanConfirmationStatus.not_required
    recovery_hints: tuple[RecoveryHint, ...] = ()
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Recovery handling plans must remain observe-only and non-executing.")
        if (
            self.disposition is RecoveryHandlingDisposition.await_user_confirmation
            and self.human_confirmation_status is HumanConfirmationStatus.not_required
        ):
            raise ValueError("Await-user-confirmation plans must require human confirmation.")
        if (
            self.disposition is RecoveryHandlingDisposition.no_recovery_needed
            and self.retryability is not RecoveryRetryability.not_applicable
        ):
            raise ValueError("No-recovery-needed plans must use not_applicable retryability.")
        if (
            self.human_confirmation_status is HumanConfirmationStatus.awaiting_user_confirmation
            and self.escalation_outcome
            is not RecoveryEscalationOutcome.human_confirmation_required
        ):
            raise ValueError(
                "Awaiting-user-confirmation status requires a human_confirmation_required escalation outcome."
            )

    @property
    def awaiting_user_confirmation(self) -> bool:
        """Whether the plan is explicitly waiting for future operator confirmation."""

        return (
            self.disposition is RecoveryHandlingDisposition.await_user_confirmation
            or self.human_confirmation_status
            is HumanConfirmationStatus.awaiting_user_confirmation
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class RecoveryPlanningResult:
    """Failure-safe wrapper for recovery/escalation/HITL planning."""

    planner_name: str
    success: bool
    recovery_plan: RecoveryHandlingPlan | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.planner_name:
            raise ValueError("planner_name must not be empty.")
        if self.success and self.recovery_plan is None:
            raise ValueError("Successful recovery planning must include recovery_plan.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed recovery planning must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful recovery planning must not include error details.")
        if not self.success and self.recovery_plan is not None:
            raise ValueError("Failed recovery planning must not include recovery_plan.")

    @classmethod
    def ok(
        cls,
        *,
        planner_name: str,
        recovery_plan: RecoveryHandlingPlan,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            planner_name=planner_name,
            success=True,
            recovery_plan=recovery_plan,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        planner_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            planner_name=planner_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )
