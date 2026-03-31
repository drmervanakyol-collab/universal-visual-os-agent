"""Structured final-boundary models for action-tool safety checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self

from .models import ActionRequirementStatus


class ActionToolBoundarySurface(StrEnum):
    """OS-facing tool surfaces that require explicit final-boundary checks."""

    dry_run_engine = "dry_run_engine"
    safe_click_prototype = "safe_click_prototype"


class ActionToolBoundarySourceKind(StrEnum):
    """Kinds of upstream structured inputs evaluated at the tool boundary."""

    action_intent = "action_intent"
    planner_action_suggestion = "planner_action_suggestion"
    resolver_output = "resolver_output"


class ActionToolBoundaryBlockCode(StrEnum):
    """Stable block/rejection codes for final action-tool boundary checks."""

    ai_boundary_validation_missing = "ai_boundary_validation_missing"
    direct_ai_output_requires_binding = "direct_ai_output_requires_binding"
    unsupported_action_type = "unsupported_action_type"
    intent_scaffold_origin_missing = "intent_scaffold_origin_missing"
    observe_only_contract_violation = "observe_only_contract_violation"
    dry_run_contract_violation = "dry_run_contract_violation"
    missing_candidate_id = "missing_candidate_id"
    missing_normalized_target = "missing_normalized_target"
    candidate_binding_mismatch = "candidate_binding_mismatch"
    snapshot_candidate_missing = "snapshot_candidate_missing"
    target_candidate_mismatch = "target_candidate_mismatch"
    real_click_mode_disabled = "real_click_mode_disabled"
    candidate_class_ineligible = "candidate_class_ineligible"
    candidate_rank_ineligible = "candidate_rank_ineligible"
    candidate_metadata_incomplete = "candidate_metadata_incomplete"
    candidate_score_ineligible = "candidate_score_ineligible"
    dry_run_not_accepted = "dry_run_not_accepted"
    policy_denied = "policy_denied"
    missing_screen_target = "missing_screen_target"
    screen_target_cross_validation_failed = "screen_target_cross_validation_failed"
    click_transport_unavailable = "click_transport_unavailable"


class ActionToolBoundaryStatus(StrEnum):
    """Whether a given tool surface is allowed or blocked."""

    allowed = "allowed"
    blocked = "blocked"


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionToolBoundaryCheckOutcome:
    """One explicit final-boundary validation outcome."""

    check_id: str
    summary: str
    status: ActionRequirementStatus
    reason: str
    block_code: ActionToolBoundaryBlockCode | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.check_id:
            raise ValueError("check_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.reason:
            raise ValueError("reason must not be empty.")
        if self.status is not ActionRequirementStatus.blocked and self.block_code is not None:
            raise ValueError("block_code may only be set for blocked check outcomes.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionToolBoundaryAssessment:
    """Structured final-boundary assessment for one tool surface."""

    surface: ActionToolBoundarySurface
    source_kind: ActionToolBoundarySourceKind
    status: ActionToolBoundaryStatus
    summary: str
    action_type: str | None = None
    candidate_id: str | None = None
    check_outcomes: tuple[ActionToolBoundaryCheckOutcome, ...] = ()
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        blocked_checks = tuple(
            outcome for outcome in self.check_outcomes if outcome.status is ActionRequirementStatus.blocked
        )
        if self.status is ActionToolBoundaryStatus.allowed and blocked_checks:
            raise ValueError("Allowed tool-boundary assessments must not contain blocked checks.")
        if self.status is ActionToolBoundaryStatus.blocked and not blocked_checks:
            raise ValueError("Blocked tool-boundary assessments must contain at least one blocked check.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Tool-boundary assessments must remain observe-only and non-executing.")

    @property
    def accepted(self) -> bool:
        """Whether the surface may continue past the final boundary."""

        return self.status is ActionToolBoundaryStatus.allowed

    @property
    def blocked_check_ids(self) -> tuple[str, ...]:
        """Stable blocked check identifiers."""

        return tuple(
            outcome.check_id
            for outcome in self.check_outcomes
            if outcome.status is ActionRequirementStatus.blocked
        )

    @property
    def blocking_codes(self) -> tuple[ActionToolBoundaryBlockCode, ...]:
        """Stable block codes for blocked checks."""

        return tuple(
            outcome.block_code
            for outcome in self.check_outcomes
            if outcome.block_code is not None
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionToolBoundaryEvaluationResult:
    """Failure-safe wrapper for tool-boundary assessment."""

    guard_name: str
    success: bool
    assessment: ActionToolBoundaryAssessment | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.guard_name:
            raise ValueError("guard_name must not be empty.")
        if self.success and self.assessment is None:
            raise ValueError("Successful tool-boundary results must include assessment.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed tool-boundary results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful tool-boundary results must not include error details.")
        if not self.success and self.assessment is not None:
            raise ValueError("Failed tool-boundary results must not include assessment.")

    @classmethod
    def ok(
        cls,
        *,
        guard_name: str,
        assessment: ActionToolBoundaryAssessment,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            guard_name=guard_name,
            success=True,
            assessment=assessment,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        guard_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            guard_name=guard_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


__all__ = [
    "ActionToolBoundaryAssessment",
    "ActionToolBoundaryBlockCode",
    "ActionToolBoundaryCheckOutcome",
    "ActionToolBoundaryEvaluationResult",
    "ActionToolBoundarySourceKind",
    "ActionToolBoundaryStatus",
    "ActionToolBoundarySurface",
]
