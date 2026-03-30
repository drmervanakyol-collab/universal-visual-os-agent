"""Scenario definition models for reusable, safety-first task scaffolding."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.actions.models import (
    ActionPrecondition,
    ActionSafetyGate,
    ActionTargetValidation,
)
from universal_visual_os_agent.semantics.state import SemanticCandidateClass
from universal_visual_os_agent.verification.models import SemanticTransitionExpectation


class ScenarioDefinitionStatus(StrEnum):
    """Validation status for scenario definitions and steps."""

    defined = "defined"
    incomplete = "incomplete"
    invalid = "invalid"


class ScenarioExecutionEligibility(StrEnum):
    """Eligibility level declared by a scenario step."""

    dry_run_only = "dry_run_only"
    real_click_eligible = "real_click_eligible"


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioCandidateSelectionConstraint:
    """Selection constraints used to narrow which candidates a step may target."""

    candidate_classes: tuple[SemanticCandidateClass, ...] = ()
    allowed_candidate_ids: tuple[str, ...] = ()
    minimum_score: float | None = None
    maximum_candidate_rank: int | None = None
    require_visible: bool = True
    require_complete: bool = True
    allow_real_click_prototype: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.minimum_score is not None and not 0.0 <= self.minimum_score <= 1.0:
            raise ValueError("minimum_score must be between 0.0 and 1.0 inclusive.")
        if self.maximum_candidate_rank is not None and self.maximum_candidate_rank <= 0:
            raise ValueError("maximum_candidate_rank must be positive when provided.")
        if len(set(self.allowed_candidate_ids)) != len(self.allowed_candidate_ids):
            raise ValueError("allowed_candidate_ids must be unique.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioSafetyRequirement:
    """Safety requirements that a scenario step expects downstream systems to honor."""

    require_observe_only_inputs: bool = True
    require_definition_only: bool = True
    require_preconditions: bool = True
    require_target_validation: bool = True
    require_explicit_safety_gates: bool = True
    require_protected_context_clear: bool = True
    require_policy_clearance_for_real_click: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioStepDefinition:
    """One reusable scenario step built on existing action and verification contracts."""

    step_id: str
    summary: str
    action_type: str = ""
    candidate_constraint: ScenarioCandidateSelectionConstraint = field(
        default_factory=ScenarioCandidateSelectionConstraint
    )
    expected_outcome: SemanticTransitionExpectation | None = None
    precondition_requirements: tuple[ActionPrecondition, ...] = ()
    target_validation_requirements: tuple[ActionTargetValidation, ...] = ()
    safety_gating_requirements: tuple[ActionSafetyGate, ...] = ()
    safety_requirement: ScenarioSafetyRequirement = field(
        default_factory=ScenarioSafetyRequirement
    )
    execution_eligibility: ScenarioExecutionEligibility = (
        ScenarioExecutionEligibility.dry_run_only
    )
    status: ScenarioDefinitionStatus = ScenarioDefinitionStatus.defined
    status_reason: str | None = None
    observe_only: bool = True
    safety_first: bool = True
    definition_only: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioDefinition:
    """Reusable scenario definition assembled from structured steps."""

    scenario_id: str
    title: str
    summary: str
    steps: tuple[ScenarioStepDefinition, ...] = ()
    status: ScenarioDefinitionStatus = ScenarioDefinitionStatus.defined
    status_reason: str | None = None
    dry_run_eligible: bool = True
    real_click_eligible: bool = False
    observe_only: bool = True
    safety_first: bool = True
    definition_only: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioDefinitionView:
    """Stable summary view for downstream consumers of scenario definitions."""

    scenario_id: str
    title: str
    summary: str
    status: ScenarioDefinitionStatus
    step_count: int
    defined_step_count: int
    incomplete_step_count: int
    invalid_step_count: int
    dry_run_only_step_ids: tuple[str, ...] = ()
    real_click_eligible_step_ids: tuple[str, ...] = ()
    signal_status: str = "absent"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.step_count < 0:
            raise ValueError("step_count must not be negative.")
        if self.defined_step_count < 0:
            raise ValueError("defined_step_count must not be negative.")
        if self.incomplete_step_count < 0:
            raise ValueError("incomplete_step_count must not be negative.")
        if self.invalid_step_count < 0:
            raise ValueError("invalid_step_count must not be negative.")
        if (
            self.defined_step_count
            + self.incomplete_step_count
            + self.invalid_step_count
            != self.step_count
        ):
            raise ValueError("Step status counts must match step_count.")
        if self.signal_status not in {"available", "partial", "absent"}:
            raise ValueError("signal_status must be available, partial, or absent.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioDefinitionResult:
    """Structured result wrapper for scenario-definition scaffolding."""

    builder_name: str
    success: bool
    source_definition: ScenarioDefinition | None = None
    scenario_definition: ScenarioDefinition | None = None
    definition_view: ScenarioDefinitionView | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.builder_name:
            raise ValueError("builder_name must not be empty.")
        if self.success and (
            self.source_definition is None
            or self.scenario_definition is None
            or self.definition_view is None
        ):
            raise ValueError(
                "Successful scenario-definition results must include source_definition, scenario_definition, and definition_view."
            )
        if not self.success and self.error_code is None:
            raise ValueError("Failed scenario-definition results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError(
                "Successful scenario-definition results must not include error details."
            )
        if not self.success and self.definition_view is not None:
            raise ValueError(
                "Failed scenario-definition results must not include definition_view."
            )

    @classmethod
    def ok(
        cls,
        *,
        builder_name: str,
        source_definition: ScenarioDefinition,
        scenario_definition: ScenarioDefinition,
        definition_view: ScenarioDefinitionView,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            builder_name=builder_name,
            success=True,
            source_definition=source_definition,
            scenario_definition=scenario_definition,
            definition_view=definition_view,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        builder_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            builder_name=builder_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )
