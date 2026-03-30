"""Observe-only cloud planner scaffolding and safe plan binding."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.actions.models import (
    ActionPrecondition,
    ActionRequirementStatus,
    ActionSafetyGate,
    ActionTargetValidation,
)
from universal_visual_os_agent.actions.scaffolding_models import ActionIntentScaffoldView
from universal_visual_os_agent.ai_architecture.arbitration import ArbitrationSource
from universal_visual_os_agent.ai_architecture.contracts import AiArchitectureSignalStatus
from universal_visual_os_agent.ai_architecture.escalation_engine import (
    DeterministicEscalationDecision,
    DeterministicEscalationDisposition,
    DeterministicEscalationReason,
)
from universal_visual_os_agent.ai_architecture.ontology import (
    ObserveOnlySharedOntologyBinder,
    SharedCandidateLabel,
    SharedCandidateOntologyBinding,
    SharedTargetLabel,
)
from universal_visual_os_agent.ai_boundary.models import AiSuggestedActionType
from universal_visual_os_agent.scenarios.definition import SafetyFirstScenarioDefinitionBuilder
from universal_visual_os_agent.scenarios.models import (
    ScenarioCandidateSelectionConstraint,
    ScenarioDefinition,
    ScenarioDefinitionView,
    ScenarioExecutionEligibility,
    ScenarioSafetyRequirement,
    ScenarioStepDefinition,
)
from universal_visual_os_agent.semantics.candidate_exposure import CandidateExposureView
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot
from universal_visual_os_agent.verification.models import (
    SemanticTransitionExpectation,
    VerificationResult,
    VerificationStatus,
)


class CloudPlannerOutcome(StrEnum):
    """Stable non-executing outcomes for future cloud-planner scaffolding."""

    planned = "planned"
    unresolved = "unresolved"
    unknown = "unknown"


class CloudPlannerRationaleCode(StrEnum):
    """Structured rationale codes for cloud-planner outputs."""

    goal_decomposition = "goal_decomposition"
    verification_guided = "verification_guided"
    escalation_guided = "escalation_guided"
    insufficient_context = "insufficient_context"
    conflicting_input = "conflicting_input"
    unknown = "unknown"


class CloudPlannerForbiddenActionLabel(StrEnum):
    """Explicitly forbidden action classes for planner scaffolding."""

    keyboard_input = "keyboard_input"
    text_entry = "text_entry"
    drag_drop = "drag_drop"
    live_execution = "live_execution"


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerCandidateSummaryEntry:
    """Compact planner-facing summary of one exposed deterministic candidate."""

    candidate_binding: SharedCandidateOntologyBinding
    rank: int
    visible: bool
    score: float | None = None
    completeness_status: str = "available"
    action_intent_id: str | None = None
    action_intent_status: str | None = None
    action_type: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.rank <= 0:
            raise ValueError("rank must be positive.")
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0 inclusive.")
        if self.completeness_status not in {"available", "partial"}:
            raise ValueError("completeness_status must be available or partial.")
        if self.action_intent_status is not None and self.action_intent_id is None:
            raise ValueError("action_intent_status requires action_intent_id.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerScenarioContext:
    """Compact scenario-definition context for future planner decomposition."""

    scenario_id: str
    title: str
    summary: str
    step_ids: tuple[str, ...] = ()
    status: str = "defined"
    dry_run_eligible: bool = True
    real_click_eligible: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise ValueError("scenario_id must not be empty.")
        if not self.title:
            raise ValueError("title must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerVerificationContext:
    """Compact verification summary for future planner requests."""

    status: VerificationStatus
    summary: str
    matched_outcome_ids: tuple[str, ...] = ()
    unsatisfied_outcome_ids: tuple[str, ...] = ()
    unknown_outcome_ids: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerEscalationContext:
    """Compact escalation summary for future planner routing."""

    disposition: DeterministicEscalationDisposition
    summary: str
    recommended_source: ArbitrationSource | None = None
    reason_codes: tuple[DeterministicEscalationReason, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerRequest:
    """Structured non-executing request for a future cloud planner."""

    request_id: str
    user_objective_summary: str
    snapshot_id: str
    candidate_summary: tuple[CloudPlannerCandidateSummaryEntry, ...]
    scenario_context: CloudPlannerScenarioContext | None = None
    verification_context: CloudPlannerVerificationContext | None = None
    escalation_context: CloudPlannerEscalationContext | None = None
    signal_status: AiArchitectureSignalStatus = AiArchitectureSignalStatus.available
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("request_id must not be empty.")
        if not self.user_objective_summary:
            raise ValueError("user_objective_summary must not be empty.")
        if not self.snapshot_id:
            raise ValueError("snapshot_id must not be empty.")
        candidate_ids = tuple(
            entry.candidate_binding.candidate_id for entry in self.candidate_summary
        )
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("candidate_summary candidate IDs must be unique.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Cloud planner requests must remain safety-first and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerSuccessCriterion:
    """One structured success criterion for a future cloud planner."""

    criterion_id: str
    summary: str
    expectation: SemanticTransitionExpectation
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.criterion_id:
            raise ValueError("criterion_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerSubgoal:
    """One structured planner subgoal bound later into scenario/action scaffolds."""

    subgoal_id: str
    summary: str
    action_type: AiSuggestedActionType
    candidate_id: str | None = None
    candidate_label: SharedCandidateLabel | None = None
    target_label: SharedTargetLabel | None = None
    success_criterion_ids: tuple[str, ...] = ()
    dry_run_only: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.subgoal_id:
            raise ValueError("subgoal_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if (
            self.action_type is AiSuggestedActionType.candidate_select
            and self.candidate_id is None
        ):
            raise ValueError("candidate_select subgoals require candidate_id.")
        if len(set(self.success_criterion_ids)) != len(self.success_criterion_ids):
            raise ValueError("success_criterion_ids must not contain duplicates.")
        if not self.dry_run_only:
            raise ValueError("Planner subgoals must remain dry-run only.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerFallbackPlan:
    """Structured fallback behavior for future planner integration."""

    summary: str
    recommended_disposition: DeterministicEscalationDisposition
    reason_codes: tuple[DeterministicEscalationReason, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerEscalationRecommendation:
    """Structured escalation recommendation from a future cloud planner."""

    summary: str
    recommended_disposition: DeterministicEscalationDisposition
    recommended_source: ArbitrationSource | None = None
    reason_codes: tuple[DeterministicEscalationReason, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerOutputContract:
    """Typed future cloud-planner output before safe binding to local pipeline state."""

    response_id: str
    request_id: str
    summary: str
    outcome: CloudPlannerOutcome
    rationale_code: CloudPlannerRationaleCode
    normalized_goal: str | None = None
    subgoals: tuple[CloudPlannerSubgoal, ...] = ()
    success_criteria: tuple[CloudPlannerSuccessCriterion, ...] = ()
    forbidden_actions: tuple[CloudPlannerForbiddenActionLabel, ...] = (
        CloudPlannerForbiddenActionLabel.keyboard_input,
        CloudPlannerForbiddenActionLabel.text_entry,
        CloudPlannerForbiddenActionLabel.drag_drop,
        CloudPlannerForbiddenActionLabel.live_execution,
    )
    fallback_plan: CloudPlannerFallbackPlan | None = None
    escalation_recommendation: CloudPlannerEscalationRecommendation | None = None
    need_more_context: bool = False
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.response_id:
            raise ValueError("response_id must not be empty.")
        if not self.request_id:
            raise ValueError("request_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if len({subgoal.subgoal_id for subgoal in self.subgoals}) != len(self.subgoals):
            raise ValueError("subgoal identifiers must be unique.")
        if (
            len({criterion.criterion_id for criterion in self.success_criteria})
            != len(self.success_criteria)
        ):
            raise ValueError("success criterion identifiers must be unique.")
        if len(set(self.forbidden_actions)) != len(self.forbidden_actions):
            raise ValueError("forbidden_actions must not contain duplicates.")
        if CloudPlannerForbiddenActionLabel.live_execution not in self.forbidden_actions:
            raise ValueError("Cloud planner scaffolding must always forbid live_execution.")
        if self.outcome is CloudPlannerOutcome.planned:
            if not self.normalized_goal:
                raise ValueError("Planned cloud planner outputs require normalized_goal.")
            if not self.subgoals:
                raise ValueError("Planned cloud planner outputs require at least one subgoal.")
            if self.need_more_context:
                raise ValueError("Planned cloud planner outputs cannot require more context.")
        else:
            if self.normalized_goal is not None:
                raise ValueError("Unresolved or unknown planner outputs must not include normalized_goal.")
            if self.subgoals or self.success_criteria:
                raise ValueError(
                    "Unresolved or unknown planner outputs must not include subgoals or success criteria."
                )
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError(
                "Cloud planner output contracts must remain safety-first and non-executing."
            )


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerBoundSubgoal:
    """A planner subgoal bound back into current deterministic scenario/action structures."""

    subgoal_id: str
    summary: str
    action_type: AiSuggestedActionType
    scenario_step: ScenarioStepDefinition
    success_criteria: tuple[CloudPlannerSuccessCriterion, ...] = ()
    candidate_binding: SharedCandidateOntologyBinding | None = None
    target_label: SharedTargetLabel | None = None
    action_intent_id: str | None = None
    action_intent_status: str | None = None
    dry_run_only: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.subgoal_id:
            raise ValueError("subgoal_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.scenario_step.step_id != self.subgoal_id:
            raise ValueError("scenario_step.step_id must match subgoal_id.")
        if (
            self.action_type is AiSuggestedActionType.candidate_select
            and self.candidate_binding is None
        ):
            raise ValueError("Candidate-select bound subgoals require candidate_binding.")
        if not self.dry_run_only:
            raise ValueError("Bound planner subgoals must remain dry-run only.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerBoundResponse:
    """Planner response safely bound into scenario, verification, and action-intent structures."""

    response_id: str
    request_id: str
    outcome: CloudPlannerOutcome
    rationale_code: CloudPlannerRationaleCode
    summary: str
    normalized_goal: str | None = None
    bound_subgoals: tuple[CloudPlannerBoundSubgoal, ...] = ()
    success_criteria: tuple[CloudPlannerSuccessCriterion, ...] = ()
    scenario_definition: ScenarioDefinition | None = None
    scenario_definition_view: ScenarioDefinitionView | None = None
    referenced_candidate_ids: tuple[str, ...] = ()
    referenced_action_intent_ids: tuple[str, ...] = ()
    forbidden_actions: tuple[CloudPlannerForbiddenActionLabel, ...] = ()
    fallback_plan: CloudPlannerFallbackPlan | None = None
    escalation_recommendation: CloudPlannerEscalationRecommendation | None = None
    signal_status: AiArchitectureSignalStatus = AiArchitectureSignalStatus.available
    need_more_context: bool = False
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.response_id:
            raise ValueError("response_id must not be empty.")
        if not self.request_id:
            raise ValueError("request_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.outcome is CloudPlannerOutcome.planned:
            if self.scenario_definition is None or self.scenario_definition_view is None:
                raise ValueError("Planned bound responses require scenario_definition and scenario_definition_view.")
            if not self.normalized_goal:
                raise ValueError("Planned bound responses require normalized_goal.")
        else:
            if self.scenario_definition is not None or self.scenario_definition_view is not None:
                raise ValueError(
                    "Unresolved or unknown bound responses must not include scenario definitions."
                )
            if self.bound_subgoals:
                raise ValueError(
                    "Unresolved or unknown bound responses must not include bound_subgoals."
                )
        if len(set(self.referenced_candidate_ids)) != len(self.referenced_candidate_ids):
            raise ValueError("referenced_candidate_ids must be unique.")
        if len(set(self.referenced_action_intent_ids)) != len(self.referenced_action_intent_ids):
            raise ValueError("referenced_action_intent_ids must be unique.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError(
                "Cloud planner bound responses must remain safety-first and non-executing."
            )


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerRequestBuildResult:
    """Failure-safe result for building a future cloud-planner request."""

    scaffolder_name: str
    success: bool
    request: CloudPlannerRequest | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scaffolder_name:
            raise ValueError("scaffolder_name must not be empty.")
        if self.success and self.request is None:
            raise ValueError("Successful request build results must include request.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed request build results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful request build results must not include error details.")
        if not self.success and self.request is not None:
            raise ValueError("Failed request build results must not include request.")

    @classmethod
    def ok(
        cls,
        *,
        scaffolder_name: str,
        request: CloudPlannerRequest,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            scaffolder_name=scaffolder_name,
            success=True,
            request=request,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        scaffolder_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            scaffolder_name=scaffolder_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerResponseBindResult:
    """Failure-safe result for binding a planner output back into local pipeline state."""

    scaffolder_name: str
    success: bool
    response: CloudPlannerBoundResponse | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scaffolder_name:
            raise ValueError("scaffolder_name must not be empty.")
        if self.success and self.response is None:
            raise ValueError("Successful response bind results must include response.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed response bind results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful response bind results must not include error details.")
        if not self.success and self.response is not None:
            raise ValueError("Failed response bind results must not include response.")

    @classmethod
    def ok(
        cls,
        *,
        scaffolder_name: str,
        response: CloudPlannerBoundResponse,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            scaffolder_name=scaffolder_name,
            success=True,
            response=response,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        scaffolder_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            scaffolder_name=scaffolder_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


class ObserveOnlyCloudPlannerScaffolder:
    """Build and bind typed cloud-planner scaffolding without model execution."""

    scaffolder_name = "ObserveOnlyCloudPlannerScaffolder"

    def __init__(
        self,
        *,
        ontology_binder: ObserveOnlySharedOntologyBinder | None = None,
        scenario_builder: SafetyFirstScenarioDefinitionBuilder | None = None,
    ) -> None:
        self._ontology_binder = (
            ObserveOnlySharedOntologyBinder() if ontology_binder is None else ontology_binder
        )
        self._scenario_builder = (
            SafetyFirstScenarioDefinitionBuilder()
            if scenario_builder is None
            else scenario_builder
        )

    def build_request(
        self,
        snapshot: SemanticStateSnapshot,
        exposure_view: CandidateExposureView,
        *,
        user_objective_summary: str,
        request_id: str,
        scenario_definition: ScenarioDefinition | None = None,
        verification_result: VerificationResult | None = None,
        action_scaffold_view: ActionIntentScaffoldView | None = None,
        escalation_decision: DeterministicEscalationDecision | None = None,
    ) -> CloudPlannerRequestBuildResult:
        if exposure_view.snapshot_id != snapshot.snapshot_id:
            return CloudPlannerRequestBuildResult.failure(
                scaffolder_name=self.scaffolder_name,
                error_code="cloud_planner_request_snapshot_mismatch",
                error_message=(
                    "Exposure view must come from the same semantic snapshot as the cloud planner request."
                ),
                details={
                    "snapshot_id": snapshot.snapshot_id,
                    "exposure_snapshot_id": exposure_view.snapshot_id,
                },
            )
        if (
            action_scaffold_view is not None
            and action_scaffold_view.snapshot_id != snapshot.snapshot_id
        ):
            return CloudPlannerRequestBuildResult.failure(
                scaffolder_name=self.scaffolder_name,
                error_code="cloud_planner_request_scaffold_snapshot_mismatch",
                error_message=(
                    "Action-intent scaffold view must come from the same semantic snapshot as the cloud planner request."
                ),
                details={
                    "snapshot_id": snapshot.snapshot_id,
                    "scaffold_snapshot_id": action_scaffold_view.snapshot_id,
                },
            )
        try:
            candidate_summary, partial_candidate_ids, failed_candidate_ids = (
                self._build_candidate_summary(
                    exposure_view=exposure_view,
                    action_scaffold_view=action_scaffold_view,
                )
            )
            scenario_context = _scenario_context(scenario_definition)
            verification_context = _verification_context(verification_result)
            escalation_context = _escalation_context(escalation_decision)
            signal_status = _request_signal_status(
                exposure_signal_status=_signal_status_from_value(exposure_view.signal_status),
                candidate_summary=candidate_summary,
                scenario_context=scenario_context,
                verification_context=verification_context,
                escalation_decision=escalation_decision,
                action_scaffold_view=action_scaffold_view,
                failed_candidate_ids=failed_candidate_ids,
            )
            request = CloudPlannerRequest(
                request_id=request_id,
                user_objective_summary=user_objective_summary,
                snapshot_id=snapshot.snapshot_id,
                candidate_summary=candidate_summary,
                scenario_context=scenario_context,
                verification_context=verification_context,
                escalation_context=escalation_context,
                signal_status=signal_status,
                metadata={
                    "candidate_ids": tuple(
                        entry.candidate_binding.candidate_id for entry in candidate_summary
                    ),
                    "candidate_binding_ids": tuple(
                        entry.candidate_binding.binding_id for entry in candidate_summary
                    ),
                    "partial_candidate_ids": partial_candidate_ids,
                    "failed_candidate_ids": failed_candidate_ids,
                    "candidate_count": len(candidate_summary),
                    "scenario_context_present": scenario_context is not None,
                    "verification_context_present": verification_context is not None,
                    "escalation_context_present": escalation_context is not None,
                    "action_scaffold_present": action_scaffold_view is not None,
                    "observe_only": True,
                    "read_only": True,
                    "non_executing": True,
                },
            )
        except Exception as exc:  # noqa: BLE001 - scaffolding must remain failure-safe
            return CloudPlannerRequestBuildResult.failure(
                scaffolder_name=self.scaffolder_name,
                error_code="cloud_planner_request_build_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return CloudPlannerRequestBuildResult.ok(
            scaffolder_name=self.scaffolder_name,
            request=request,
            details={
                "signal_status": request.signal_status.value,
                "candidate_count": len(request.candidate_summary),
            },
        )

    def bind_response(
        self,
        request: CloudPlannerRequest,
        *,
        contract: CloudPlannerOutputContract,
    ) -> CloudPlannerResponseBindResult:
        try:
            if contract.request_id != request.request_id:
                return CloudPlannerResponseBindResult.failure(
                    scaffolder_name=self.scaffolder_name,
                    error_code="cloud_planner_response_request_mismatch",
                    error_message="Cloud planner output request_id did not match the originating request.",
                    details={
                        "request_id": request.request_id,
                        "contract_request_id": contract.request_id,
                    },
                )

            if contract.outcome is not CloudPlannerOutcome.planned:
                response = CloudPlannerBoundResponse(
                    response_id=contract.response_id,
                    request_id=request.request_id,
                    outcome=contract.outcome,
                    rationale_code=contract.rationale_code,
                    summary=contract.summary,
                    forbidden_actions=contract.forbidden_actions,
                    fallback_plan=contract.fallback_plan,
                    escalation_recommendation=contract.escalation_recommendation,
                    signal_status=AiArchitectureSignalStatus.partial,
                    need_more_context=contract.need_more_context,
                    metadata={
                        **dict(contract.metadata),
                        "request_signal_status": request.signal_status.value,
                        "observe_only": True,
                        "read_only": True,
                        "non_executing": True,
                    },
                )
                return CloudPlannerResponseBindResult.ok(
                    scaffolder_name=self.scaffolder_name,
                    response=response,
                    details={
                        "signal_status": response.signal_status.value,
                        "outcome": response.outcome.value,
                    },
                )

            candidate_entries = {
                entry.candidate_binding.candidate_id: entry for entry in request.candidate_summary
            }
            criteria_by_id = {
                criterion.criterion_id: criterion for criterion in contract.success_criteria
            }
            bound_subgoals = tuple(
                self._bind_subgoal(
                    request=request,
                    subgoal=subgoal,
                    candidate_entries=candidate_entries,
                    criteria_by_id=criteria_by_id,
                    forbidden_actions=contract.forbidden_actions,
                )
                for subgoal in contract.subgoals
            )
            scenario_source = self._build_scenario_definition(
                request=request,
                contract=contract,
                bound_subgoals=bound_subgoals,
            )
            scenario_result = self._scenario_builder.build(scenario_source)
            if (
                not scenario_result.success
                or scenario_result.scenario_definition is None
                or scenario_result.definition_view is None
            ):
                return CloudPlannerResponseBindResult.failure(
                    scaffolder_name=self.scaffolder_name,
                    error_code="cloud_planner_response_scenario_build_failed",
                    error_message=(
                        scenario_result.error_message
                        or "Cloud planner scenario binding could not build a normalized scenario definition."
                    ),
                    details={"upstream_error_code": scenario_result.error_code},
                )

            referenced_candidate_ids = tuple(
                dict.fromkeys(
                    subgoal.candidate_binding.candidate_id
                    for subgoal in bound_subgoals
                    if subgoal.candidate_binding is not None
                )
            )
            referenced_action_intent_ids = tuple(
                dict.fromkeys(
                    subgoal.action_intent_id
                    for subgoal in bound_subgoals
                    if subgoal.action_intent_id is not None
                )
            )
            signal_status = _bound_signal_status(
                request_signal_status=request.signal_status,
                scenario_view_signal_status=scenario_result.definition_view.signal_status,
            )
            response = CloudPlannerBoundResponse(
                response_id=contract.response_id,
                request_id=request.request_id,
                outcome=contract.outcome,
                rationale_code=contract.rationale_code,
                summary=contract.summary,
                normalized_goal=contract.normalized_goal,
                bound_subgoals=bound_subgoals,
                success_criteria=contract.success_criteria,
                scenario_definition=scenario_result.scenario_definition,
                scenario_definition_view=scenario_result.definition_view,
                referenced_candidate_ids=referenced_candidate_ids,
                referenced_action_intent_ids=referenced_action_intent_ids,
                forbidden_actions=contract.forbidden_actions,
                fallback_plan=contract.fallback_plan,
                escalation_recommendation=contract.escalation_recommendation,
                signal_status=signal_status,
                need_more_context=False,
                metadata={
                    **dict(contract.metadata),
                    "bound_subgoal_ids": tuple(subgoal.subgoal_id for subgoal in bound_subgoals),
                    "scenario_status": scenario_result.scenario_definition.status.value,
                    "scenario_signal_status": scenario_result.definition_view.signal_status,
                    "observe_only": True,
                    "read_only": True,
                    "non_executing": True,
                },
            )
        except Exception as exc:  # noqa: BLE001 - scaffolding must remain failure-safe
            return CloudPlannerResponseBindResult.failure(
                scaffolder_name=self.scaffolder_name,
                error_code="cloud_planner_response_bind_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return CloudPlannerResponseBindResult.ok(
            scaffolder_name=self.scaffolder_name,
            response=response,
            details={
                "signal_status": response.signal_status.value,
                "outcome": response.outcome.value,
                "bound_subgoal_count": len(response.bound_subgoals),
            },
        )

    def _build_candidate_summary(
        self,
        *,
        exposure_view: CandidateExposureView,
        action_scaffold_view: ActionIntentScaffoldView | None,
    ) -> tuple[
        tuple[CloudPlannerCandidateSummaryEntry, ...],
        tuple[str, ...],
        tuple[str, ...],
    ]:
        intents_by_candidate_id = (
            {}
            if action_scaffold_view is None
            else {
                intent.candidate_id: intent
                for intent in action_scaffold_view.intents
                if intent.candidate_id is not None
            }
        )
        summary_entries: list[CloudPlannerCandidateSummaryEntry] = []
        partial_candidate_ids: list[str] = []
        failed_candidate_ids: list[str] = []
        for candidate in exposure_view.candidates:
            binding_result = self._ontology_binder.bind_exposed_candidate(candidate)
            if not binding_result.success or binding_result.binding is None:
                failed_candidate_ids.append(candidate.candidate_id)
                continue
            intent = intents_by_candidate_id.get(candidate.candidate_id)
            completeness_status = (
                "partial"
                if (
                    candidate.completeness_status != "available"
                    or binding_result.binding.completeness_status != "available"
                    or (intent is not None and intent.status.value != "scaffolded")
                )
                else "available"
            )
            if completeness_status != "available":
                partial_candidate_ids.append(candidate.candidate_id)
            summary_entries.append(
                CloudPlannerCandidateSummaryEntry(
                    candidate_binding=binding_result.binding,
                    rank=candidate.rank,
                    visible=candidate.visible,
                    score=candidate.score,
                    completeness_status=completeness_status,
                    action_intent_id=None if intent is None else intent.intent_id,
                    action_intent_status=None if intent is None else intent.status.value,
                    action_type=None if intent is None else intent.action_type,
                    metadata={
                        **dict(candidate.metadata),
                        "candidate_rank": candidate.rank,
                        "candidate_visible": candidate.visible,
                    },
                )
            )
        return (
            tuple(summary_entries),
            tuple(sorted(set(partial_candidate_ids))),
            tuple(sorted(set(failed_candidate_ids))),
        )

    def _bind_subgoal(
        self,
        *,
        request: CloudPlannerRequest,
        subgoal: CloudPlannerSubgoal,
        candidate_entries: Mapping[str, CloudPlannerCandidateSummaryEntry],
        criteria_by_id: Mapping[str, CloudPlannerSuccessCriterion],
        forbidden_actions: tuple[CloudPlannerForbiddenActionLabel, ...],
    ) -> CloudPlannerBoundSubgoal:
        candidate_entry: CloudPlannerCandidateSummaryEntry | None = None
        if subgoal.candidate_id is not None:
            candidate_entry = candidate_entries.get(subgoal.candidate_id)
            if candidate_entry is None:
                raise ValueError(
                    f"Planner subgoal '{subgoal.subgoal_id}' referenced candidate '{subgoal.candidate_id}' which is not present in the request candidate summary."
                )
            if (
                subgoal.candidate_label is not None
                and candidate_entry.candidate_binding.shared_candidate_label
                is not subgoal.candidate_label
            ):
                raise ValueError(
                    f"Planner subgoal '{subgoal.subgoal_id}' label did not match the deterministic candidate ontology binding."
                )

        success_criteria: tuple[CloudPlannerSuccessCriterion, ...] = tuple(
            criteria_by_id[criterion_id] for criterion_id in subgoal.success_criterion_ids
        )
        if len(success_criteria) != len(subgoal.success_criterion_ids):
            raise ValueError(
                f"Planner subgoal '{subgoal.subgoal_id}' referenced missing success criteria."
            )
        scenario_step = _scenario_step_from_subgoal(
            request=request,
            subgoal=subgoal,
            candidate_entry=candidate_entry,
            success_criteria=success_criteria,
            forbidden_actions=forbidden_actions,
        )
        return CloudPlannerBoundSubgoal(
            subgoal_id=subgoal.subgoal_id,
            summary=subgoal.summary,
            action_type=subgoal.action_type,
            scenario_step=scenario_step,
            success_criteria=success_criteria,
            candidate_binding=(
                None if candidate_entry is None else candidate_entry.candidate_binding
            ),
            target_label=subgoal.target_label,
            action_intent_id=(
                None if candidate_entry is None else candidate_entry.action_intent_id
            ),
            action_intent_status=(
                None if candidate_entry is None else candidate_entry.action_intent_status
            ),
            dry_run_only=True,
            metadata={
                **dict(subgoal.metadata),
                "forbidden_actions": tuple(action.value for action in forbidden_actions),
            },
        )

    def _build_scenario_definition(
        self,
        *,
        request: CloudPlannerRequest,
        contract: CloudPlannerOutputContract,
        bound_subgoals: tuple[CloudPlannerBoundSubgoal, ...],
    ) -> ScenarioDefinition:
        scenario_id = (
            request.scenario_context.scenario_id
            if request.scenario_context is not None
            else f"{request.request_id}:planner_scenario"
        )
        title = (
            request.scenario_context.title
            if request.scenario_context is not None
            else contract.normalized_goal
        )
        summary = contract.normalized_goal
        return ScenarioDefinition(
            scenario_id=scenario_id,
            title=title,
            summary=summary or request.user_objective_summary,
            steps=tuple(bound_subgoal.scenario_step for bound_subgoal in bound_subgoals),
            dry_run_eligible=True,
            real_click_eligible=False,
            observe_only=True,
            safety_first=True,
            definition_only=True,
            metadata={
                "cloud_planner_bound": True,
                "cloud_planner_request_id": request.request_id,
                "cloud_planner_response_id": contract.response_id,
                "cloud_planner_outcome": contract.outcome.value,
                "cloud_planner_rationale_code": contract.rationale_code.value,
                "cloud_planner_forbidden_actions": tuple(
                    action.value for action in contract.forbidden_actions
                ),
                "observe_only": True,
                "safety_first": True,
                "definition_only": True,
            },
        )


def _scenario_context(
    scenario_definition: ScenarioDefinition | None,
) -> CloudPlannerScenarioContext | None:
    if scenario_definition is None:
        return None
    return CloudPlannerScenarioContext(
        scenario_id=scenario_definition.scenario_id,
        title=scenario_definition.title,
        summary=scenario_definition.summary,
        step_ids=tuple(step.step_id for step in scenario_definition.steps),
        status=scenario_definition.status.value,
        dry_run_eligible=scenario_definition.dry_run_eligible,
        real_click_eligible=scenario_definition.real_click_eligible,
        metadata={
            **dict(scenario_definition.metadata),
            "step_count": len(scenario_definition.steps),
        },
    )


def _verification_context(
    verification_result: VerificationResult | None,
) -> CloudPlannerVerificationContext | None:
    if verification_result is None:
        return None
    return CloudPlannerVerificationContext(
        status=verification_result.status,
        summary=verification_result.summary,
        matched_outcome_ids=verification_result.matched_outcome_ids,
        unsatisfied_outcome_ids=verification_result.unsatisfied_outcome_ids,
        unknown_outcome_ids=verification_result.unknown_outcome_ids,
        metadata={
            "matched_candidate_ids": verification_result.matched_candidate_ids,
            "missing_candidate_ids": verification_result.missing_candidate_ids,
            "unexpected_candidate_ids": verification_result.unexpected_candidate_ids,
        },
    )


def _escalation_context(
    escalation_decision: DeterministicEscalationDecision | None,
) -> CloudPlannerEscalationContext | None:
    if escalation_decision is None:
        return None
    return CloudPlannerEscalationContext(
        disposition=escalation_decision.disposition,
        summary=escalation_decision.summary,
        recommended_source=escalation_decision.recommended_source,
        reason_codes=escalation_decision.reason_codes,
        metadata=dict(escalation_decision.metadata),
    )


def _signal_status_from_value(value: str) -> AiArchitectureSignalStatus:
    try:
        return AiArchitectureSignalStatus(value)
    except ValueError:
        return AiArchitectureSignalStatus.partial


def _request_signal_status(
    *,
    exposure_signal_status: AiArchitectureSignalStatus,
    candidate_summary: tuple[CloudPlannerCandidateSummaryEntry, ...],
    scenario_context: CloudPlannerScenarioContext | None,
    verification_context: CloudPlannerVerificationContext | None,
    escalation_decision: DeterministicEscalationDecision | None,
    action_scaffold_view: ActionIntentScaffoldView | None,
    failed_candidate_ids: tuple[str, ...],
) -> AiArchitectureSignalStatus:
    statuses = [exposure_signal_status]
    if any(entry.completeness_status != "available" for entry in candidate_summary):
        statuses.append(AiArchitectureSignalStatus.partial)
    if failed_candidate_ids:
        statuses.append(AiArchitectureSignalStatus.partial)
    if scenario_context is not None and scenario_context.status != "defined":
        statuses.append(AiArchitectureSignalStatus.partial)
    if (
        verification_context is not None
        and verification_context.status is VerificationStatus.unknown
    ):
        statuses.append(AiArchitectureSignalStatus.partial)
    if escalation_decision is not None:
        statuses.append(escalation_decision.signal_status)
    if action_scaffold_view is not None:
        statuses.append(_signal_status_from_value(action_scaffold_view.signal_status))
    if any(status is AiArchitectureSignalStatus.partial for status in statuses):
        return AiArchitectureSignalStatus.partial
    if any(status is AiArchitectureSignalStatus.absent for status in statuses):
        return AiArchitectureSignalStatus.partial
    if not candidate_summary:
        return AiArchitectureSignalStatus.absent
    return AiArchitectureSignalStatus.available


def _bound_signal_status(
    *,
    request_signal_status: AiArchitectureSignalStatus,
    scenario_view_signal_status: str,
) -> AiArchitectureSignalStatus:
    if request_signal_status is not AiArchitectureSignalStatus.available:
        return AiArchitectureSignalStatus.partial
    if scenario_view_signal_status != "available":
        return AiArchitectureSignalStatus.partial
    return AiArchitectureSignalStatus.available


def _scenario_step_from_subgoal(
    *,
    request: CloudPlannerRequest,
    subgoal: CloudPlannerSubgoal,
    candidate_entry: CloudPlannerCandidateSummaryEntry | None,
    success_criteria: tuple[CloudPlannerSuccessCriterion, ...],
    forbidden_actions: tuple[CloudPlannerForbiddenActionLabel, ...],
) -> ScenarioStepDefinition:
    return ScenarioStepDefinition(
        step_id=subgoal.subgoal_id,
        summary=subgoal.summary,
        action_type=subgoal.action_type.value,
        candidate_constraint=_candidate_constraint(
            request=request,
            candidate_entry=candidate_entry,
        ),
        expected_outcome=_merge_success_criteria(
            success_criteria,
            summary=subgoal.summary,
        ),
        precondition_requirements=_preconditions_for_subgoal(
            candidate_entry=candidate_entry,
        ),
        target_validation_requirements=_target_validations_for_subgoal(
            candidate_entry=candidate_entry,
        ),
        safety_gating_requirements=_safety_gates_for_subgoal(
            forbidden_actions=forbidden_actions,
        ),
        safety_requirement=ScenarioSafetyRequirement(),
        execution_eligibility=ScenarioExecutionEligibility.dry_run_only,
        status_reason=None,
        observe_only=True,
        safety_first=True,
        definition_only=True,
        metadata={
            **dict(subgoal.metadata),
            "planner_bound_subgoal": True,
            "planner_action_type": subgoal.action_type.value,
            "planner_target_label": (
                None if subgoal.target_label is None else subgoal.target_label.value
            ),
            "planner_success_criterion_ids": tuple(
                criterion.criterion_id for criterion in success_criteria
            ),
            "planner_candidate_id": (
                None if candidate_entry is None else candidate_entry.candidate_binding.candidate_id
            ),
            "planner_action_intent_id": (
                None if candidate_entry is None else candidate_entry.action_intent_id
            ),
            "planner_action_intent_status": (
                None if candidate_entry is None else candidate_entry.action_intent_status
            ),
            "observe_only": True,
            "safety_first": True,
            "definition_only": True,
        },
    )


def _candidate_constraint(
    *,
    request: CloudPlannerRequest,
    candidate_entry: CloudPlannerCandidateSummaryEntry | None,
) -> ScenarioCandidateSelectionConstraint:
    if candidate_entry is not None:
        candidate_class = candidate_entry.candidate_binding.deterministic_candidate_class
        return ScenarioCandidateSelectionConstraint(
            candidate_classes=() if candidate_class is None else (candidate_class,),
            allowed_candidate_ids=(candidate_entry.candidate_binding.candidate_id,),
            minimum_score=candidate_entry.score,
            maximum_candidate_rank=candidate_entry.rank,
            require_visible=True,
            require_complete=True,
            allow_real_click_prototype=False,
            metadata={
                "planner_candidate_binding_id": candidate_entry.candidate_binding.binding_id,
                "planner_candidate_completeness_status": candidate_entry.completeness_status,
            },
        )

    fallback_candidate_ids = tuple(
        entry.candidate_binding.candidate_id for entry in request.candidate_summary
    )
    candidate_classes = tuple(
        dict.fromkeys(
            entry.candidate_binding.deterministic_candidate_class
            for entry in request.candidate_summary
            if entry.candidate_binding.deterministic_candidate_class is not None
        )
    )
    return ScenarioCandidateSelectionConstraint(
        candidate_classes=candidate_classes,
        allowed_candidate_ids=fallback_candidate_ids,
        require_visible=True,
        require_complete=True,
        allow_real_click_prototype=False,
        metadata={"planner_fallback_candidate_scope": fallback_candidate_ids},
    )


def _preconditions_for_subgoal(
    *,
    candidate_entry: CloudPlannerCandidateSummaryEntry | None,
) -> tuple[ActionPrecondition, ...]:
    return (
        ActionPrecondition(
            requirement_id="planner_goal_bound",
            summary="Planner subgoal is grounded in a structured normalized goal.",
            status=ActionRequirementStatus.satisfied,
            metadata={"source": "cloud_planner"},
        ),
        ActionPrecondition(
            requirement_id="planner_action_intent_reference",
            summary="Candidate-targeted planner steps should reference an existing dry-run action intent when available.",
            status=(
                ActionRequirementStatus.satisfied
                if candidate_entry is not None and candidate_entry.action_intent_id is not None
                else ActionRequirementStatus.pending
            ),
            metadata={
                "action_intent_id": (
                    None if candidate_entry is None else candidate_entry.action_intent_id
                ),
                "action_intent_status": (
                    None if candidate_entry is None else candidate_entry.action_intent_status
                ),
            },
        ),
    )


def _target_validations_for_subgoal(
    *,
    candidate_entry: CloudPlannerCandidateSummaryEntry | None,
) -> tuple[ActionTargetValidation, ...]:
    return (
        ActionTargetValidation(
            validation_id="planner_candidate_binding_available",
            summary="Planner-bound steps must keep their deterministic candidate binding available.",
            status=(
                ActionRequirementStatus.satisfied
                if candidate_entry is not None
                and candidate_entry.completeness_status == "available"
                else ActionRequirementStatus.pending
            ),
            metadata={
                "candidate_id": (
                    None
                    if candidate_entry is None
                    else candidate_entry.candidate_binding.candidate_id
                ),
                "completeness_status": (
                    None if candidate_entry is None else candidate_entry.completeness_status
                ),
            },
        ),
        ActionTargetValidation(
            validation_id="planner_target_validation_required",
            summary="Planner-bound steps still require downstream deterministic target validation.",
            status=ActionRequirementStatus.pending,
            metadata={"source": "cloud_planner"},
        ),
    )


def _safety_gates_for_subgoal(
    *,
    forbidden_actions: tuple[CloudPlannerForbiddenActionLabel, ...],
) -> tuple[ActionSafetyGate, ...]:
    return (
        ActionSafetyGate(
            gate_id="planner_observe_only_enforced",
            summary="Planner-bound scenario steps must remain observe-only and non-executing.",
            status=ActionRequirementStatus.satisfied,
            metadata={"observe_only": True, "non_executing": True},
        ),
        ActionSafetyGate(
            gate_id="planner_live_execution_forbidden",
            summary="Planner-bound scenario steps must preserve the live-execution kill switch.",
            status=(
                ActionRequirementStatus.satisfied
                if CloudPlannerForbiddenActionLabel.live_execution in forbidden_actions
                else ActionRequirementStatus.blocked
            ),
            metadata={
                "forbidden_actions": tuple(action.value for action in forbidden_actions),
            },
        ),
    )


def _merge_success_criteria(
    criteria: tuple[CloudPlannerSuccessCriterion, ...],
    *,
    summary: str,
) -> SemanticTransitionExpectation | None:
    if not criteria:
        return None
    required_candidate_ids: list[str] = []
    forbidden_candidate_ids: list[str] = []
    required_node_ids: list[str] = []
    expected_outcomes: list[object] = []
    seen_outcome_ids: set[str] = set()
    for criterion in criteria:
        expectation = criterion.expectation
        required_candidate_ids.extend(expectation.required_candidate_ids)
        forbidden_candidate_ids.extend(expectation.forbidden_candidate_ids)
        required_node_ids.extend(expectation.required_node_ids)
        for outcome in expectation.expected_outcomes:
            if outcome.outcome_id in seen_outcome_ids:
                continue
            seen_outcome_ids.add(outcome.outcome_id)
            expected_outcomes.append(outcome)
    return SemanticTransitionExpectation(
        summary=summary,
        required_candidate_ids=tuple(dict.fromkeys(required_candidate_ids)),
        forbidden_candidate_ids=tuple(dict.fromkeys(forbidden_candidate_ids)),
        required_node_ids=tuple(dict.fromkeys(required_node_ids)),
        expected_outcomes=tuple(expected_outcomes),
    )
