"""Scenario definition models for reusable, safety-first task scaffolding."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.actions.dry_run_models import DryRunActionEvaluation
from universal_visual_os_agent.actions.safe_click import SafeClickExecution
from universal_visual_os_agent.actions.scaffolding_models import ActionIntentScaffoldView
from universal_visual_os_agent.actions.models import (
    ActionPrecondition,
    ActionSafetyGate,
    ActionTargetValidation,
)
from universal_visual_os_agent.recovery.models import RecoveryHandlingPlan
from universal_visual_os_agent.scenarios.state_machine import ScenarioStateMachineTrace
from universal_visual_os_agent.semantics.state import SemanticCandidateClass
from universal_visual_os_agent.semantics.candidate_exposure import CandidateExposureView
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot
from universal_visual_os_agent.verification.models import (
    SemanticTransitionExpectation,
    VerificationResult,
)


class ScenarioDefinitionStatus(StrEnum):
    """Validation status for scenario definitions and steps."""

    defined = "defined"
    incomplete = "incomplete"
    invalid = "invalid"


class ScenarioExecutionEligibility(StrEnum):
    """Eligibility level declared by a scenario step."""

    dry_run_only = "dry_run_only"
    real_click_eligible = "real_click_eligible"


class ScenarioStepStage(StrEnum):
    """Ordered stage markers produced by the scenario loop."""

    started = "started"
    observed = "observed"
    understood = "understood"
    verified = "verified"
    incomplete = "incomplete"
    failed = "failed"


class ScenarioRunStatus(StrEnum):
    """Terminal status for one scenario-run attempt."""

    completed = "completed"
    incomplete = "incomplete"
    failed = "failed"


class ScenarioActionDisposition(StrEnum):
    """Resolved action path for one scenario step in the Phase 6C loop."""

    dry_run_only = "dry_run_only"
    blocked = "blocked"
    real_click_eligible = "real_click_eligible"
    real_click_executed = "real_click_executed"
    incomplete = "incomplete"


class ScenarioActionStepStage(StrEnum):
    """Ordered stage markers for the observe-act-verify scenario loop."""

    started = "started"
    observed = "observed"
    understood = "understood"
    intent_selected = "intent_selected"
    dry_run_evaluated = "dry_run_evaluated"
    action_resolved = "action_resolved"
    post_observed = "post_observed"
    post_understood = "post_understood"
    verified = "verified"
    incomplete = "incomplete"
    failed = "failed"


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


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioStepRun:
    """Structured result for one non-executing observe-understand-verify step."""

    step_id: str
    summary: str
    execution_eligibility: ScenarioExecutionEligibility
    final_stage: ScenarioStepStage
    stage_history: tuple[ScenarioStepStage, ...]
    reason: str
    observed_snapshot: SemanticStateSnapshot | None = None
    exposure_view: CandidateExposureView | None = None
    verification_result: VerificationResult | None = None
    recovery_plan: RecoveryHandlingPlan | None = None
    matched_candidate_ids: tuple[str, ...] = ()
    signal_status: str = "absent"
    state_machine_trace: ScenarioStateMachineTrace | None = None
    observe_only: bool = True
    non_executing: bool = True
    live_execution_attempted: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.step_id:
            raise ValueError("step_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.stage_history:
            raise ValueError("stage_history must not be empty.")
        if self.stage_history[0] is not ScenarioStepStage.started:
            raise ValueError("stage_history must begin with started.")
        if self.stage_history[-1] is not self.final_stage:
            raise ValueError("stage_history must end with final_stage.")
        if not self.reason:
            raise ValueError("reason must not be empty.")
        if self.signal_status not in {"available", "partial", "absent"}:
            raise ValueError("signal_status must be available, partial, or absent.")
        if self.recovery_plan is not None and not self.recovery_plan.non_executing:
            raise ValueError("Scenario step recovery plans must remain non-executing.")
        if (
            self.state_machine_trace is not None
            and self.state_machine_trace.live_execution_attempted
        ):
            raise ValueError("Observe-understand-verify step traces must remain non-executing.")
        if not self.observe_only or not self.non_executing or self.live_execution_attempted:
            raise ValueError("Scenario step runs must remain observe-only and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioRun:
    """Structured result for one non-executing scenario loop."""

    scenario_id: str
    title: str
    summary: str
    status: ScenarioRunStatus
    step_runs: tuple[ScenarioStepRun, ...]
    verified_step_count: int
    incomplete_step_count: int
    failed_step_count: int
    current_snapshot: SemanticStateSnapshot | None = None
    initial_snapshot: SemanticStateSnapshot | None = None
    signal_status: str = "absent"
    observe_only: bool = True
    non_executing: bool = True
    live_execution_attempted: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise ValueError("scenario_id must not be empty.")
        if not self.title:
            raise ValueError("title must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if (
            self.verified_step_count
            + self.incomplete_step_count
            + self.failed_step_count
            != len(self.step_runs)
        ):
            raise ValueError("Step outcome counts must match len(step_runs).")
        if self.signal_status not in {"available", "partial", "absent"}:
            raise ValueError("signal_status must be available, partial, or absent.")
        if not self.observe_only or not self.non_executing or self.live_execution_attempted:
            raise ValueError("Scenario runs must remain observe-only and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioRunResult:
    """Structured wrapper for one scenario-loop attempt."""

    runner_name: str
    success: bool
    scenario_definition: ScenarioDefinition | None = None
    scenario_run: ScenarioRun | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.runner_name:
            raise ValueError("runner_name must not be empty.")
        if self.success and (self.scenario_definition is None or self.scenario_run is None):
            raise ValueError(
                "Successful scenario-run results must include scenario_definition and scenario_run."
            )
        if not self.success and self.error_code is None:
            raise ValueError("Failed scenario-run results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful scenario-run results must not include error details.")
        if not self.success and self.scenario_run is not None:
            raise ValueError("Failed scenario-run results must not include scenario_run.")

    @classmethod
    def ok(
        cls,
        *,
        runner_name: str,
        scenario_definition: ScenarioDefinition,
        scenario_run: ScenarioRun,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            runner_name=runner_name,
            success=True,
            scenario_definition=scenario_definition,
            scenario_run=scenario_run,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        runner_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            runner_name=runner_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioActionStepRun:
    """Structured result for one safety-first observe-act-verify scenario step."""

    step_id: str
    summary: str
    execution_eligibility: ScenarioExecutionEligibility
    action_disposition: ScenarioActionDisposition
    final_stage: ScenarioActionStepStage
    stage_history: tuple[ScenarioActionStepStage, ...]
    reason: str
    pre_action_snapshot: SemanticStateSnapshot | None = None
    post_action_snapshot: SemanticStateSnapshot | None = None
    exposure_view: CandidateExposureView | None = None
    scaffold_view: ActionIntentScaffoldView | None = None
    dry_run_evaluation: DryRunActionEvaluation | None = None
    safe_click_execution: SafeClickExecution | None = None
    verification_result: VerificationResult | None = None
    recovery_plan: RecoveryHandlingPlan | None = None
    matched_candidate_ids: tuple[str, ...] = ()
    selected_candidate_id: str | None = None
    selected_intent_id: str | None = None
    signal_status: str = "absent"
    state_machine_trace: ScenarioStateMachineTrace | None = None
    observe_only_inputs: bool = True
    safety_first: bool = True
    non_executing: bool = True
    live_execution_attempted: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.step_id:
            raise ValueError("step_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.stage_history:
            raise ValueError("stage_history must not be empty.")
        if self.stage_history[0] is not ScenarioActionStepStage.started:
            raise ValueError("stage_history must begin with started.")
        if self.stage_history[-1] is not self.final_stage:
            raise ValueError("stage_history must end with final_stage.")
        if not self.reason:
            raise ValueError("reason must not be empty.")
        if self.signal_status not in {"available", "partial", "absent"}:
            raise ValueError("signal_status must be available, partial, or absent.")
        if not self.observe_only_inputs:
            raise ValueError("Scenario action step runs must preserve observe-only inputs.")
        if not self.safety_first:
            raise ValueError("Scenario action step runs must remain safety-first.")
        if self.recovery_plan is not None and not self.recovery_plan.non_executing:
            raise ValueError("Scenario action step recovery plans must remain non-executing.")
        if (
            self.state_machine_trace is not None
            and self.state_machine_trace.live_execution_attempted != self.live_execution_attempted
        ):
            raise ValueError(
                "state_machine_trace.live_execution_attempted must match step live_execution_attempted."
            )
        if self.live_execution_attempted != (
            self.action_disposition is ScenarioActionDisposition.real_click_executed
        ):
            raise ValueError(
                "live_execution_attempted must match whether the action disposition is real_click_executed."
            )
        if self.non_executing == self.live_execution_attempted:
            raise ValueError(
                "non_executing must be false only when a real click was actually executed."
            )


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioActionRun:
    """Structured result for one safety-first observe-act-verify scenario loop."""

    scenario_id: str
    title: str
    summary: str
    status: ScenarioRunStatus
    step_runs: tuple[ScenarioActionStepRun, ...]
    verified_step_count: int
    incomplete_step_count: int
    failed_step_count: int
    dry_run_only_step_count: int
    blocked_step_count: int
    real_click_eligible_step_count: int
    real_click_executed_step_count: int
    action_incomplete_step_count: int
    current_snapshot: SemanticStateSnapshot | None = None
    initial_snapshot: SemanticStateSnapshot | None = None
    signal_status: str = "absent"
    observe_only_inputs: bool = True
    safety_first: bool = True
    non_executing: bool = True
    live_execution_attempted: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise ValueError("scenario_id must not be empty.")
        if not self.title:
            raise ValueError("title must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if (
            self.verified_step_count
            + self.incomplete_step_count
            + self.failed_step_count
            != len(self.step_runs)
        ):
            raise ValueError("Step outcome counts must match len(step_runs).")
        if (
            self.dry_run_only_step_count
            + self.blocked_step_count
            + self.real_click_eligible_step_count
            + self.real_click_executed_step_count
            + self.action_incomplete_step_count
            != len(self.step_runs)
        ):
            raise ValueError("Action disposition counts must match len(step_runs).")
        if self.signal_status not in {"available", "partial", "absent"}:
            raise ValueError("signal_status must be available, partial, or absent.")
        if not self.observe_only_inputs:
            raise ValueError("Scenario action runs must preserve observe-only inputs.")
        if not self.safety_first:
            raise ValueError("Scenario action runs must remain safety-first.")
        if self.live_execution_attempted != any(
            step_run.live_execution_attempted for step_run in self.step_runs
        ):
            raise ValueError(
                "live_execution_attempted must reflect whether any step executed a real click."
            )
        if self.non_executing == self.live_execution_attempted:
            raise ValueError(
                "non_executing must be false only when a real click was actually executed."
            )


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioActionRunResult:
    """Structured wrapper for one observe-act-verify scenario loop attempt."""

    runner_name: str
    success: bool
    scenario_definition: ScenarioDefinition | None = None
    scenario_run: ScenarioActionRun | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.runner_name:
            raise ValueError("runner_name must not be empty.")
        if self.success and (self.scenario_definition is None or self.scenario_run is None):
            raise ValueError(
                "Successful scenario action-run results must include scenario_definition and scenario_run."
            )
        if not self.success and self.error_code is None:
            raise ValueError("Failed scenario action-run results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError(
                "Successful scenario action-run results must not include error details."
            )
        if not self.success and self.scenario_run is not None:
            raise ValueError(
                "Failed scenario action-run results must not include scenario_run."
            )

    @classmethod
    def ok(
        cls,
        *,
        runner_name: str,
        scenario_definition: ScenarioDefinition,
        scenario_run: ScenarioActionRun,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            runner_name=runner_name,
            success=True,
            scenario_definition=scenario_definition,
            scenario_run=scenario_run,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        runner_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            runner_name=runner_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )
