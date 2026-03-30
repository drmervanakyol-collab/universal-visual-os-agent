"""Action intent and result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping
from uuid import uuid4

from universal_visual_os_agent.geometry.models import NormalizedPoint


class ActionIntentStatus(StrEnum):
    """Lifecycle status for a scaffolded action intent."""

    scaffolded = "scaffolded"
    incomplete = "incomplete"
    blocked = "blocked"


class ActionIntentReasonCode(StrEnum):
    """Stable reason codes for safe action-intent scaffolding."""

    scaffold_only = "scaffold_only"
    incomplete_candidate_metadata = "incomplete_candidate_metadata"
    target_validation_incomplete = "target_validation_incomplete"
    safety_gating_required = "safety_gating_required"


class ActionRequirementStatus(StrEnum):
    """Status for intent preconditions, validations, and safety gates."""

    satisfied = "satisfied"
    pending = "pending"
    blocked = "blocked"


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionPrecondition:
    """A precondition required before an intent could ever be attempted."""

    requirement_id: str
    summary: str
    status: ActionRequirementStatus
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.requirement_id:
            raise ValueError("requirement_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionTargetValidation:
    """Validation requirements that must hold for the action target."""

    validation_id: str
    summary: str
    status: ActionRequirementStatus
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.validation_id:
            raise ValueError("validation_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionSafetyGate:
    """A safety gate that constrains action execution."""

    gate_id: str
    summary: str
    status: ActionRequirementStatus
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.gate_id:
            raise ValueError("gate_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionIntent:
    """An action the planner would like to perform."""

    action_type: str
    target: NormalizedPoint | None = None
    intent_id: str = field(default_factory=lambda: str(uuid4()))
    status: ActionIntentStatus = ActionIntentStatus.scaffolded
    reason_code: ActionIntentReasonCode = ActionIntentReasonCode.scaffold_only
    reason: str = "Observe-only action scaffold only; execution remains disabled."
    candidate_id: str | None = None
    candidate_label: str | None = None
    candidate_rank: int | None = None
    candidate_score: float | None = None
    precondition_requirements: tuple[ActionPrecondition, ...] = ()
    target_validation_requirements: tuple[ActionTargetValidation, ...] = ()
    safety_gating_requirements: tuple[ActionSafetyGate, ...] = ()
    dry_run_only: bool = True
    executable: bool = False
    observe_only_source: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action_type:
            raise ValueError("action_type must not be empty.")
        if not self.intent_id:
            raise ValueError("intent_id must not be empty.")
        if not self.reason:
            raise ValueError("reason must not be empty.")
        if self.candidate_rank is not None and self.candidate_rank <= 0:
            raise ValueError("candidate_rank must be positive when provided.")
        if self.candidate_score is not None and not 0.0 <= self.candidate_score <= 1.0:
            raise ValueError("candidate_score must be between 0.0 and 1.0 inclusive.")
        if self.executable:
            raise ValueError("Phase 5A action intents must remain non-executing.")
        if not self.dry_run_only:
            raise ValueError("Phase 5A action intents must remain dry-run only.")
        if not self.observe_only_source:
            raise ValueError("Phase 5A action intents must remain observe-only in origin.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionResult:
    """Result returned by a dry-run or future executor."""

    accepted: bool
    simulated: bool
    details: Mapping[str, object] = field(default_factory=dict)
