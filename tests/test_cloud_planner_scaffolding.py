from __future__ import annotations

from dataclasses import replace

from test_ai_boundary_contracts import _boundary_context

from universal_visual_os_agent.actions.scaffolding import ObserveOnlyActionIntentScaffolder
from universal_visual_os_agent.ai_architecture import (
    AiArchitectureSignalStatus,
    CloudPlannerEscalationRecommendation,
    CloudPlannerOutcome,
    CloudPlannerOutputContract,
    CloudPlannerRationaleCode,
    CloudPlannerSubgoal,
    CloudPlannerSuccessCriterion,
    DeterministicEscalationDecision,
    DeterministicEscalationDisposition,
    ObserveOnlyCloudPlannerScaffolder,
    SharedCandidateLabel,
    SharedTargetLabel,
)
from universal_visual_os_agent.ai_architecture.arbitration import ArbitrationSource
from universal_visual_os_agent.ai_boundary import AiSuggestedActionType
from universal_visual_os_agent.scenarios.models import ScenarioDefinition
from universal_visual_os_agent.semantics.candidate_exposure import CandidateExposureView
from universal_visual_os_agent.verification import (
    SemanticTransitionExpectation,
    VerificationResult,
    VerificationStatus,
)


class _ExplodingCloudPlannerScaffolder(ObserveOnlyCloudPlannerScaffolder):
    def _build_candidate_summary(
        self,
        *,
        exposure_view,
        action_scaffold_view,
    ):
        del exposure_view, action_scaffold_view
        raise RuntimeError("cloud planner exploded")


def _scenario_definition() -> ScenarioDefinition:
    return ScenarioDefinition(
        scenario_id="scenario-confirm-primary",
        title="Confirm Primary Candidate",
        summary="Confirm the highest-confidence deterministic candidate safely.",
    )


def _verification_result(candidate_id: str) -> VerificationResult:
    return VerificationResult(
        status=VerificationStatus.satisfied,
        summary="The current semantic transition still supports the candidate goal.",
        matched_candidate_ids=(candidate_id,),
        matched_outcome_ids=("criterion-1",),
        observe_only=True,
        read_only=True,
        non_actionable=True,
    )


def _escalation_decision() -> DeterministicEscalationDecision:
    return DeterministicEscalationDecision(
        disposition=DeterministicEscalationDisposition.deterministic_ok,
        summary="Deterministic evidence is currently sufficient.",
        signal_status=AiArchitectureSignalStatus.available,
        recommended_source=ArbitrationSource.deterministic_pipeline,
    )


def _scaffold_view(snapshot, exposure_view):
    scaffold_result = ObserveOnlyActionIntentScaffolder().scaffold(
        snapshot,
        exposure_view=exposure_view,
    )
    assert scaffold_result.success is True
    assert scaffold_result.scaffold_view is not None
    return scaffold_result.scaffold_view


def _planned_contract(
    candidate_id: str,
    candidate_label: SharedCandidateLabel,
    *,
    request_id: str = "planner-request-1",
) -> CloudPlannerOutputContract:
    return CloudPlannerOutputContract(
        response_id="planner-response-1",
        request_id=request_id,
        summary="Normalize the current objective into one dry-run candidate selection step.",
        outcome=CloudPlannerOutcome.planned,
        rationale_code=CloudPlannerRationaleCode.goal_decomposition,
        normalized_goal="Confirm the primary button candidate without execution.",
        success_criteria=(
            CloudPlannerSuccessCriterion(
                criterion_id="criterion-1",
                summary="The selected candidate remains present in the semantic state.",
                expectation=SemanticTransitionExpectation(
                    summary="Candidate remains required.",
                    required_candidate_ids=(candidate_id,),
                ),
            ),
        ),
        subgoals=(
            CloudPlannerSubgoal(
                subgoal_id="subgoal-select-primary",
                summary="Bind the current primary candidate into a dry-run scenario step.",
                action_type=AiSuggestedActionType.candidate_select,
                candidate_id=candidate_id,
                candidate_label=candidate_label,
                target_label=SharedTargetLabel.candidate_center,
                success_criterion_ids=("criterion-1",),
            ),
        ),
    )


def test_cloud_planner_builds_valid_request() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    scaffolder = ObserveOnlyCloudPlannerScaffolder()

    result = scaffolder.build_request(
        snapshot,
        exposure_view,
        user_objective_summary="Confirm the primary button candidate safely.",
        request_id="planner-request-1",
        scenario_definition=_scenario_definition(),
        verification_result=_verification_result(candidate.candidate_id),
        action_scaffold_view=_scaffold_view(snapshot, exposure_view),
        escalation_decision=_escalation_decision(),
    )

    assert result.success is True
    assert result.request is not None
    assert result.request.observe_only is True
    assert result.request.read_only is True
    assert result.request.non_executing is True
    assert result.request.signal_status is AiArchitectureSignalStatus.available
    assert result.request.scenario_context is not None
    assert result.request.verification_context is not None
    assert result.request.escalation_context is not None
    assert result.request.candidate_summary
    assert result.request.candidate_summary[0].candidate_binding.candidate_id == candidate.candidate_id
    assert result.request.candidate_summary[0].action_intent_id is not None


def test_cloud_planner_binds_valid_planned_response() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    request_result = ObserveOnlyCloudPlannerScaffolder().build_request(
        snapshot,
        exposure_view,
        user_objective_summary="Confirm the primary button candidate safely.",
        request_id="planner-request-1",
        scenario_definition=_scenario_definition(),
        verification_result=_verification_result(candidate.candidate_id),
        action_scaffold_view=_scaffold_view(snapshot, exposure_view),
        escalation_decision=_escalation_decision(),
    )
    assert request_result.success is True
    assert request_result.request is not None
    candidate_label = request_result.request.candidate_summary[0].candidate_binding.shared_candidate_label
    assert candidate_label is not None

    response_result = ObserveOnlyCloudPlannerScaffolder().bind_response(
        request_result.request,
        contract=_planned_contract(candidate.candidate_id, candidate_label),
    )

    assert response_result.success is True
    assert response_result.response is not None
    assert response_result.response.outcome is CloudPlannerOutcome.planned
    assert response_result.response.scenario_definition is not None
    assert response_result.response.scenario_definition_view is not None
    assert response_result.response.scenario_definition.status.value == "defined"
    assert response_result.response.referenced_candidate_ids == (candidate.candidate_id,)
    assert response_result.response.referenced_action_intent_ids
    assert response_result.response.bound_subgoals[0].scenario_step.action_type == "candidate_select"
    assert response_result.response.bound_subgoals[0].scenario_step.expected_outcome is not None
    assert response_result.response.signal_status is AiArchitectureSignalStatus.available
    assert response_result.response.observe_only is True
    assert response_result.response.read_only is True
    assert response_result.response.non_executing is True


def test_cloud_planner_supports_unresolved_need_more_context_path() -> None:
    snapshot, exposure_view, _candidate = _boundary_context()
    request_result = ObserveOnlyCloudPlannerScaffolder().build_request(
        snapshot,
        exposure_view,
        user_objective_summary="Confirm the primary button candidate safely.",
        request_id="planner-request-unknown",
    )
    assert request_result.success is True
    assert request_result.request is not None

    response_result = ObserveOnlyCloudPlannerScaffolder().bind_response(
        request_result.request,
        contract=CloudPlannerOutputContract(
            response_id="planner-response-unknown",
            request_id=request_result.request.request_id,
            summary="The planner needs richer scenario context before decomposing the goal.",
            outcome=CloudPlannerOutcome.unresolved,
            rationale_code=CloudPlannerRationaleCode.insufficient_context,
            need_more_context=True,
            escalation_recommendation=CloudPlannerEscalationRecommendation(
                summary="Ask the cloud planner again later with richer scenario context.",
                recommended_disposition=DeterministicEscalationDisposition.cloud_planner_recommended,
                recommended_source=ArbitrationSource.cloud_planner,
            ),
        ),
    )

    assert response_result.success is True
    assert response_result.response is not None
    assert response_result.response.outcome is CloudPlannerOutcome.unresolved
    assert response_result.response.need_more_context is True
    assert response_result.response.scenario_definition is None
    assert response_result.response.signal_status is AiArchitectureSignalStatus.partial


def test_cloud_planner_handles_partial_and_conflicting_input_safely() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    partial_candidate = replace(exposure_view.candidates[0], completeness_status="partial")
    partial_exposure_view = replace(
        exposure_view,
        candidates=(partial_candidate,) + exposure_view.candidates[1:],
        signal_status="partial",
    )
    scaffolder = ObserveOnlyCloudPlannerScaffolder()

    partial_request_result = scaffolder.build_request(
        snapshot,
        partial_exposure_view,
        user_objective_summary="Build a partial request safely.",
        request_id="planner-request-partial",
        action_scaffold_view=_scaffold_view(snapshot, exposure_view),
    )
    assert partial_request_result.success is True
    assert partial_request_result.request is not None
    assert partial_request_result.request.signal_status is AiArchitectureSignalStatus.partial

    request_result = scaffolder.build_request(
        snapshot,
        exposure_view,
        user_objective_summary="Confirm the primary button candidate safely.",
        request_id="planner-request-conflict",
        action_scaffold_view=_scaffold_view(snapshot, exposure_view),
    )
    assert request_result.success is True
    assert request_result.request is not None
    current_label = request_result.request.candidate_summary[0].candidate_binding.shared_candidate_label
    assert current_label is not None
    conflicting_label = next(label for label in SharedCandidateLabel if label is not current_label)

    response_result = scaffolder.bind_response(
        request_result.request,
        contract=_planned_contract(
            candidate.candidate_id,
            conflicting_label,
            request_id=request_result.request.request_id,
        ),
    )

    assert response_result.success is False
    assert response_result.error_code == "cloud_planner_response_bind_exception"
    assert "label" in response_result.error_message


def test_cloud_planner_does_not_propagate_unhandled_exceptions() -> None:
    snapshot, exposure_view, _candidate = _boundary_context()

    result = _ExplodingCloudPlannerScaffolder().build_request(
        snapshot,
        exposure_view,
        user_objective_summary="Exercise exception safety.",
        request_id="planner-request-explodes",
    )

    assert result.success is False
    assert result.error_code == "cloud_planner_request_build_exception"
    assert result.error_message == "cloud planner exploded"
