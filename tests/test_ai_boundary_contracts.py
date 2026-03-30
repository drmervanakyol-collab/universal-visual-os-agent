from __future__ import annotations

from dataclasses import replace

from test_semantic_candidate_exposure import _scored_snapshot

from universal_visual_os_agent.ai_boundary import (
    AiActionEligibility,
    AiBoundaryRejectionCode,
    AiBoundaryValidationContext,
    CloudPlannerContract,
    LocalVisualResolverContract,
    ObserveOnlyAiBoundaryValidator,
    PlannerActionSuggestionContract,
    ResolverPointContract,
)
from universal_visual_os_agent.config import AgentMode, RunConfig
from universal_visual_os_agent.policy import (
    KillSwitchState,
    PauseState,
    PauseStatus,
    PolicyEvaluationContext,
    ProtectedContextAssessment,
    ProtectedContextStatus,
)
from universal_visual_os_agent.semantics import ObserveOnlyCandidateExposer
from universal_visual_os_agent.semantics.semantic_delta import SemanticDeltaCategory
from universal_visual_os_agent.verification import (
    ExpectedSemanticChange,
    ExpectedSemanticOutcome,
    SemanticTransitionExpectation,
)


class _ExplodingAiBoundaryValidator(ObserveOnlyAiBoundaryValidator):
    def _coerce_confidence(self, value, *, source, field_path, rejections):
        del value, source, field_path, rejections
        raise RuntimeError("ai boundary exploded")


def _boundary_context():
    snapshot = _scored_snapshot()
    exposure_result = ObserveOnlyCandidateExposer().expose(snapshot)
    assert exposure_result.success is True
    assert exposure_result.exposure_view is not None
    exposure_view = exposure_result.exposure_view
    candidate = snapshot.get_candidate(exposure_view.candidates[0].candidate_id)
    assert candidate is not None
    return snapshot, exposure_view, candidate


def _center_point(candidate) -> ResolverPointContract:
    return ResolverPointContract(
        x=candidate.bounds.left + (candidate.bounds.width / 2.0),
        y=candidate.bounds.top + (candidate.bounds.height / 2.0),
    )


def test_ai_boundary_accepts_valid_structured_planner_output() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    contract = CloudPlannerContract(
        decision_id="planner-1",
        summary="Select the exposed candidate in dry-run form.",
        action_suggestion=PlannerActionSuggestionContract(
            action_type="candidate_select",
            candidate_id=candidate.candidate_id,
            candidate_label=candidate.label,
            target_label="candidate_center",
            confidence=0.82,
            dry_run_only=True,
            live_execution_requested=False,
        ),
        expected_transition=SemanticTransitionExpectation(
            summary="Candidate remains present but may change after later action handling.",
            expected_outcomes=(
                ExpectedSemanticOutcome(
                    outcome_id="candidate-change",
                    category=SemanticDeltaCategory.candidate,
                    item_id=candidate.candidate_id,
                    expected_change=ExpectedSemanticChange.changed,
                    expected_before_state={"label": candidate.label},
                ),
            ),
        ),
    )

    result = ObserveOnlyAiBoundaryValidator().validate_planner_contract(
        contract,
        context=AiBoundaryValidationContext(
            run_config=RunConfig(mode=AgentMode.observe_only),
            snapshot=snapshot,
            exposure_view=exposure_view,
        ),
    )

    assert result.success is True
    assert result.validated_output is not None
    assert result.validated_output.observe_only is True
    assert result.validated_output.read_only is True
    assert result.validated_output.non_executing is True
    assert result.validated_output.action_suggestion is not None
    assert result.validated_output.action_suggestion.action_eligibility is AiActionEligibility.dry_run_only
    assert result.validated_output.action_suggestion.target_label.value == "candidate_center"


def test_ai_boundary_accepts_valid_structured_resolver_output() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    contract = LocalVisualResolverContract(
        resolution_id="resolver-1",
        summary="Resolve the candidate center point.",
        action_type="candidate_select",
        candidate_id=candidate.candidate_id,
        candidate_label=candidate.label,
        target_label="candidate_center",
        point=_center_point(candidate),
        confidence=0.93,
    )

    result = ObserveOnlyAiBoundaryValidator().validate_resolver_contract(
        contract,
        context=AiBoundaryValidationContext(
            snapshot=snapshot,
            exposure_view=exposure_view,
        ),
    )

    assert result.success is True
    assert result.validated_output is not None
    assert result.validated_output.observe_only is True
    assert result.validated_output.read_only is True
    assert result.validated_output.non_executing is True
    assert result.validated_output.candidate_id == candidate.candidate_id
    assert result.validated_output.target_label.value == "candidate_center"


def test_ai_boundary_rejects_out_of_bounds_resolver_coordinates() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    contract = LocalVisualResolverContract(
        resolution_id="resolver-oob",
        summary="Resolve an invalid point.",
        action_type="candidate_select",
        candidate_id=candidate.candidate_id,
        target_label="candidate_point",
        point=ResolverPointContract(x=1.2, y=0.5),
        confidence=0.6,
    )

    result = ObserveOnlyAiBoundaryValidator().validate_resolver_contract(
        contract,
        context=AiBoundaryValidationContext(snapshot=snapshot, exposure_view=exposure_view),
    )

    assert result.success is False
    assert result.rejections
    assert result.rejections[0].code is AiBoundaryRejectionCode.out_of_bounds_coordinate


def test_ai_boundary_rejects_invalid_candidate_reference() -> None:
    snapshot, exposure_view, _candidate = _boundary_context()
    contract = CloudPlannerContract(
        decision_id="planner-missing-candidate",
        summary="Try to select a missing candidate.",
        action_suggestion=PlannerActionSuggestionContract(
            action_type="candidate_select",
            candidate_id="missing-candidate",
            target_label="candidate_center",
            confidence=0.7,
        ),
    )

    result = ObserveOnlyAiBoundaryValidator().validate_planner_contract(
        contract,
        context=AiBoundaryValidationContext(snapshot=snapshot, exposure_view=exposure_view),
    )

    assert result.success is False
    assert any(
        rejection.code is AiBoundaryRejectionCode.invalid_candidate_reference
        for rejection in result.rejections
    )


def test_ai_boundary_rejects_malformed_confidence() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    contract = LocalVisualResolverContract(
        resolution_id="resolver-bad-confidence",
        summary="Resolve with malformed confidence.",
        action_type="candidate_select",
        candidate_id=candidate.candidate_id,
        target_label="candidate_center",
        point=_center_point(candidate),
        confidence="high",
    )

    result = ObserveOnlyAiBoundaryValidator().validate_resolver_contract(
        contract,
        context=AiBoundaryValidationContext(snapshot=snapshot, exposure_view=exposure_view),
    )

    assert result.success is False
    assert any(
        rejection.code is AiBoundaryRejectionCode.malformed_confidence
        for rejection in result.rejections
    )


def test_ai_boundary_rejects_invalid_action_eligibility_for_current_mode() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    contract = CloudPlannerContract(
        decision_id="planner-live-request",
        summary="Request live execution while safety gates are off.",
        action_suggestion=PlannerActionSuggestionContract(
            action_type="candidate_select",
            candidate_id=candidate.candidate_id,
            target_label="candidate_center",
            confidence=0.88,
            live_execution_requested=True,
        ),
    )

    result = ObserveOnlyAiBoundaryValidator().validate_planner_contract(
        contract,
        context=AiBoundaryValidationContext(
            run_config=RunConfig(mode=AgentMode.observe_only),
            snapshot=snapshot,
            exposure_view=exposure_view,
            protected_context_assessment=ProtectedContextAssessment(
                status=ProtectedContextStatus.protected,
                reason="protected",
            ),
            kill_switch_state=KillSwitchState(engaged=True, reason="manual stop"),
            pause_state=PauseState(status=PauseStatus.paused, reason="paused"),
            policy_context=PolicyEvaluationContext(
                live_execution_requested=False,
                live_execution_enabled=False,
            ),
        ),
    )

    assert result.success is False
    invalid_eligibility = next(
        rejection
        for rejection in result.rejections
        if rejection.code is AiBoundaryRejectionCode.invalid_action_eligibility
    )
    assert invalid_eligibility.metadata["failed_gate_ids"] == (
        "run_mode_safe_action",
        "allow_live_input_enabled",
        "protected_context_clear",
        "kill_switch_disengaged",
        "pause_state_running",
        "policy_live_execution_enabled",
        "policy_live_execution_requested",
    )


def test_ai_boundary_rejects_impossible_state_transition() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    contract = CloudPlannerContract(
        decision_id="planner-impossible-transition",
        summary="Claim an already visible candidate will appear.",
        action_suggestion=PlannerActionSuggestionContract(
            action_type="candidate_select",
            candidate_id=candidate.candidate_id,
            target_label="candidate_center",
            confidence=0.74,
        ),
        expected_transition=SemanticTransitionExpectation(
            summary="Impossible transition.",
            expected_outcomes=(
                ExpectedSemanticOutcome(
                    outcome_id="candidate-appears",
                    category=SemanticDeltaCategory.candidate,
                    item_id=candidate.candidate_id,
                    expected_change=ExpectedSemanticChange.appeared,
                ),
            ),
        ),
    )

    result = ObserveOnlyAiBoundaryValidator().validate_planner_contract(
        contract,
        context=AiBoundaryValidationContext(snapshot=snapshot, exposure_view=exposure_view),
    )

    assert result.success is False
    assert any(
        rejection.code is AiBoundaryRejectionCode.impossible_state_transition
        for rejection in result.rejections
    )


def test_ai_boundary_handles_partial_input_safely() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    contract = CloudPlannerContract(
        decision_id="planner-partial",
        summary="Validate a layout-tree outcome without a layout tree.",
        action_suggestion=PlannerActionSuggestionContract(
            action_type="candidate_select",
            candidate_id=candidate.candidate_id,
            target_label="candidate_center",
            confidence=0.79,
        ),
        expected_transition=SemanticTransitionExpectation(
            summary="Needs layout tree.",
            expected_outcomes=(
                ExpectedSemanticOutcome(
                    outcome_id="layout-node-appears",
                    category=SemanticDeltaCategory.layout_tree_node,
                    item_id="node-1",
                    expected_change=ExpectedSemanticChange.appeared,
                ),
            ),
        ),
    )

    result = ObserveOnlyAiBoundaryValidator().validate_planner_contract(
        contract,
        context=AiBoundaryValidationContext(
            snapshot=replace(snapshot, layout_tree=None),
            exposure_view=exposure_view,
        ),
    )

    assert result.success is False
    assert any(
        rejection.code is AiBoundaryRejectionCode.partial_input
        for rejection in result.rejections
    )


def test_ai_boundary_does_not_propagate_unhandled_exceptions() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    contract = CloudPlannerContract(
        decision_id="planner-explodes",
        summary="Exercise exception safety.",
        action_suggestion=PlannerActionSuggestionContract(
            action_type="candidate_select",
            candidate_id=candidate.candidate_id,
            target_label="candidate_center",
            confidence=0.9,
        ),
    )

    result = _ExplodingAiBoundaryValidator().validate_planner_contract(
        contract,
        context=AiBoundaryValidationContext(snapshot=snapshot, exposure_view=exposure_view),
    )

    assert result.success is False
    assert result.error_code == "planner_contract_validation_exception"
    assert result.error_message == "ai boundary exploded"
