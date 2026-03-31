from __future__ import annotations

from dataclasses import replace

from test_ai_boundary_contracts import _center_point
from test_deterministic_escalation_engine import _binding
from test_dry_run_action_engine import _scaffold_view

from universal_visual_os_agent.actions import (
    ObserveOnlyActionToolBoundaryGuard,
    ObserveOnlyDryRunActionEngine,
)
from universal_visual_os_agent.ai_architecture import (
    ArbitrationConflict,
    ArbitrationConflictKind,
    ArbitrationSource,
    ObserveOnlyDeterministicEscalationEngine,
    ObserveOnlyPlannerContractBuilder,
    ObserveOnlyResolverContractBuilder,
)
from universal_visual_os_agent.ai_boundary import (
    CloudPlannerContract,
    LocalVisualResolverContract,
    PlannerActionSuggestionContract,
)
from universal_visual_os_agent.config import AgentMode, RunConfig
from universal_visual_os_agent.geometry import ScreenPoint
from universal_visual_os_agent.recovery.handling import ObserveOnlyRecoveryEscalationHitlPlanner
from universal_visual_os_agent.recovery.models import (
    HumanConfirmationStatus,
    RecoveryEscalationOutcome,
    RecoveryFailureOrigin,
    RecoveryHandlingDisposition,
    RecoveryRetryability,
)
from universal_visual_os_agent.scenarios.state_machine import (
    InstrumentedScenarioStateMachine,
    ScenarioFlowState,
)
from universal_visual_os_agent.semantics import CandidateSelectionRiskLevel
from universal_visual_os_agent.verification.models import (
    VerificationReasonCategory,
    VerificationResult,
    VerificationStatus,
    VerificationTaxonomy,
)


class _ExplodingRecoveryPlanner(ObserveOnlyRecoveryEscalationHitlPlanner):
    def _plan_from_verification_result(self, result):  # type: ignore[override]
        del result
        raise RuntimeError("recovery planner exploded")


def test_recovery_planner_marks_retryable_tool_boundary_failures() -> None:
    snapshot, scaffold_view = _scaffold_view()
    intent = scaffold_view.intents[0]
    changed_snapshot = replace(snapshot, snapshot_id="missing-candidate-snapshot", candidates=())

    boundary_result = ObserveOnlyActionToolBoundaryGuard().evaluate_intent_for_dry_run(
        intent,
        snapshot=changed_snapshot,
    )
    assert boundary_result.success is True
    assert boundary_result.assessment is not None

    result = ObserveOnlyRecoveryEscalationHitlPlanner().plan_from_tool_boundary_assessment(
        boundary_result.assessment
    )

    assert result.success is True
    assert result.recovery_plan is not None
    assert result.recovery_plan.disposition is RecoveryHandlingDisposition.retry
    assert result.recovery_plan.retryability is RecoveryRetryability.retryable
    assert result.recovery_plan.failure_origin is RecoveryFailureOrigin.tool_boundary
    assert result.recovery_plan.escalation_outcome is RecoveryEscalationOutcome.blocked
    assert result.recovery_plan.recovery_hints[0].next_expected_signal == "tool_boundary_refresh"


def test_recovery_planner_marks_non_retryable_tool_boundary_failures() -> None:
    snapshot, scaffold_view = _scaffold_view()
    intent = scaffold_view.intents[0]
    dry_run_result = ObserveOnlyDryRunActionEngine().evaluate_intent(intent, snapshot=snapshot)
    assert dry_run_result.success is True
    assert dry_run_result.evaluation is not None

    boundary_result = ObserveOnlyActionToolBoundaryGuard().evaluate_intent_for_safe_click(
        intent,
        config=RunConfig(mode=AgentMode.dry_run),
        target_screen_point=ScreenPoint(x_px=100, y_px=100),
        dry_run_evaluation=dry_run_result.evaluation,
        policy_decision=None,
        snapshot=snapshot,
        execute=True,
        click_transport_available=False,
    )
    assert boundary_result.success is True
    assert boundary_result.assessment is not None

    result = ObserveOnlyRecoveryEscalationHitlPlanner().plan_from_tool_boundary_assessment(
        boundary_result.assessment
    )

    assert result.success is True
    assert result.recovery_plan is not None
    assert result.recovery_plan.disposition is RecoveryHandlingDisposition.blocked
    assert result.recovery_plan.retryability is RecoveryRetryability.non_retryable
    assert result.recovery_plan.recovery_hints[0].next_expected_signal == "operator_review"


def test_recovery_planner_marks_escalation_required_for_cloud_planner_path() -> None:
    binding, _exposure_view, _candidate = _binding()

    escalation_result = ObserveOnlyDeterministicEscalationEngine().evaluate(
        deterministic_binding=replace(
            binding,
            confidence=0.94,
            selection_risk_level=CandidateSelectionRiskLevel.medium,
            requires_local_resolver=False,
            disambiguation_needed=False,
            source_conflict_present=True,
            completeness_status="available",
        )
    )
    assert escalation_result.success is True
    assert escalation_result.decision is not None

    result = ObserveOnlyRecoveryEscalationHitlPlanner().plan_from_escalation_decision(
        escalation_result.decision
    )

    assert result.success is True
    assert result.recovery_plan is not None
    assert result.recovery_plan.disposition is RecoveryHandlingDisposition.escalate
    assert result.recovery_plan.escalation_outcome is RecoveryEscalationOutcome.cloud_planner_recommended
    assert result.recovery_plan.retryability is RecoveryRetryability.non_retryable


def test_recovery_planner_marks_human_confirmation_required_for_high_risk_conflict() -> None:
    binding, exposure_view, candidate = _binding()
    planner_candidate = exposure_view.candidates[-1]
    resolver_response_result = ObserveOnlyResolverContractBuilder().bind_response(
        LocalVisualResolverContract(
            resolution_id="resolver-agrees",
            summary="Choose the deterministic candidate center.",
            action_type="candidate_select",
            candidate_id=binding.candidate_id,
            candidate_label=binding.candidate_label,
            target_label="candidate_center",
            point=_center_point(candidate),
            confidence=0.93,
        ),
        exposure_view=exposure_view,
    )
    planner_response_result = ObserveOnlyPlannerContractBuilder().bind_response(
        CloudPlannerContract(
            decision_id="planner-conflict",
            summary="Choose a different candidate.",
            action_suggestion=PlannerActionSuggestionContract(
                action_type="candidate_select",
                candidate_id=planner_candidate.candidate_id,
                candidate_label=planner_candidate.label,
                target_label="candidate_center",
                confidence=0.89,
                dry_run_only=True,
                live_execution_requested=False,
            ),
        ),
        exposure_view=exposure_view,
    )
    assert resolver_response_result.success is True
    assert resolver_response_result.response_contract is not None
    assert planner_response_result.success is True
    assert planner_response_result.response_contract is not None

    escalation_result = ObserveOnlyDeterministicEscalationEngine().evaluate(
        deterministic_binding=replace(
            binding,
            confidence=0.95,
            selection_risk_level=CandidateSelectionRiskLevel.high,
            requires_local_resolver=False,
            disambiguation_needed=False,
            source_conflict_present=True,
            completeness_status="available",
        ),
        resolver_response=resolver_response_result.response_contract,
        planner_response=planner_response_result.response_contract,
        conflicts=(
            ArbitrationConflict(
                kind=ArbitrationConflictKind.candidate_reference_mismatch,
                summary="Deterministic and planner candidate IDs differ.",
                sources=(
                    ArbitrationSource.deterministic_pipeline,
                    ArbitrationSource.cloud_planner,
                ),
                candidate_ids=(binding.candidate_id, planner_candidate.candidate_id),
            ),
        ),
    )
    assert escalation_result.success is True
    assert escalation_result.decision is not None

    result = ObserveOnlyRecoveryEscalationHitlPlanner().plan_from_escalation_decision(
        escalation_result.decision
    )

    assert result.success is True
    assert result.recovery_plan is not None
    assert result.recovery_plan.disposition is RecoveryHandlingDisposition.await_user_confirmation
    assert result.recovery_plan.escalation_outcome is RecoveryEscalationOutcome.human_confirmation_required
    assert (
        result.recovery_plan.human_confirmation_status
        is HumanConfirmationStatus.awaiting_user_confirmation
    )
    assert result.recovery_plan.recovery_hints[0].next_expected_signal == "operator_confirmation"


def test_recovery_planner_marks_unsatisfied_verification_as_aborted() -> None:
    result = ObserveOnlyRecoveryEscalationHitlPlanner().plan_from_verification_result(
        VerificationResult(
            status=VerificationStatus.unsatisfied,
            summary="Expected semantic change was not observed.",
            taxonomy=VerificationTaxonomy(
                summary="Verification unsatisfied with expected_change_not_found.",
                primary_category=VerificationReasonCategory.expected_change_not_found,
                categories=(VerificationReasonCategory.expected_change_not_found,),
                category_counts={"expected_change_not_found": 1},
                error_count=1,
            ),
        )
    )

    assert result.success is True
    assert result.recovery_plan is not None
    assert result.recovery_plan.disposition is RecoveryHandlingDisposition.aborted
    assert result.recovery_plan.retryability is RecoveryRetryability.non_retryable
    assert result.recovery_plan.failure_origin is RecoveryFailureOrigin.verification


def test_state_machine_can_transition_to_awaiting_user_confirmation_from_recovery_plan() -> None:
    planner_result = ObserveOnlyRecoveryEscalationHitlPlanner().plan_for_human_confirmation(
        summary="Action is eligible but still needs operator confirmation.",
        failure_origin=RecoveryFailureOrigin.scenario_action_flow,
    )
    assert planner_result.success is True
    assert planner_result.recovery_plan is not None

    state_machine = InstrumentedScenarioStateMachine(trace_id="hitl-state-machine")
    state_machine.transition(ScenarioFlowState.observed, next_expected_signal="semantic_understanding")
    state_machine.transition(ScenarioFlowState.understood, next_expected_signal="candidate_selection")
    state_machine.transition_for_recovery_plan(planner_result.recovery_plan)
    trace = state_machine.trace(signal_status="available")

    assert trace.current_state is ScenarioFlowState.awaiting_user_confirmation
    assert trace.transitions[-1].to_state is ScenarioFlowState.awaiting_user_confirmation
    assert trace.transitions[-1].next_expected_signal == "operator_confirmation"
    assert (
        trace.transitions[-1].metadata["recovery_plan_disposition"]
        == "await_user_confirmation"
    )
    assert (
        trace.transitions[-1].metadata["recovery_plan_human_confirmation_status"]
        == "awaiting_user_confirmation"
    )


def test_recovery_planner_does_not_propagate_unhandled_exceptions() -> None:
    result = _ExplodingRecoveryPlanner().plan_from_verification_result(
        VerificationResult(
            status=VerificationStatus.unknown,
            summary="Explode while planning recovery.",
        )
    )

    assert result.success is False
    assert result.error_code == "recovery_verification_planning_exception"
    assert result.error_message == "recovery planner exploded"
