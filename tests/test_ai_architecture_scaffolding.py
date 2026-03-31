from __future__ import annotations

from dataclasses import replace

from test_ai_boundary_contracts import _boundary_context, _center_point

from universal_visual_os_agent.ai_architecture import (
    AiArchitectureSignalStatus,
    ArbitrationConflict,
    ArbitrationConflictKind,
    ArbitrationSource,
    EscalationAction,
    EscalationPolicy,
    ObserveOnlyAiArbitrator,
    ObserveOnlyEscalationPolicyDecider,
    ObserveOnlyPlannerContractBuilder,
    ObserveOnlyResolverContractBuilder,
    ObserveOnlySharedOntologyBinder,
    SharedTargetLabel,
)
from universal_visual_os_agent.ai_boundary import (
    CloudPlannerContract,
    LocalVisualResolverContract,
    PlannerActionSuggestionContract,
)
from universal_visual_os_agent.semantics import CandidateSelectionRiskLevel


class _ExplodingPlannerContractBuilder(ObserveOnlyPlannerContractBuilder):
    def _bind_exposure_candidates(self, exposure_view):
        del exposure_view
        raise RuntimeError("planner contract builder exploded")


class _ExplodingAiArbitrator(ObserveOnlyAiArbitrator):
    def _collect_conflicts(self, *, deterministic_binding, resolver_response, planner_response, policy):
        del deterministic_binding, resolver_response, planner_response, policy
        raise RuntimeError("ai arbitrator exploded")


class _ExplodingEscalationPolicyDecider(ObserveOnlyEscalationPolicyDecider):
    def _conflict_decision(
        self,
        *,
        conflicts,
        resolver_response,
        planner_response,
        policy,
        high_risk,
        reason_codes,
    ):
        del conflicts, resolver_response, planner_response, policy, high_risk, reason_codes
        raise RuntimeError("escalation policy decider exploded")


def test_shared_ontology_binder_maps_exposed_candidate_consistently() -> None:
    _snapshot, exposure_view, _candidate = _boundary_context()
    exposed_candidate = exposure_view.candidates[0]

    result = ObserveOnlySharedOntologyBinder().bind_exposed_candidate(exposed_candidate)

    assert result.success is True
    assert result.binding is not None
    assert result.binding.candidate_id == exposed_candidate.candidate_id
    assert result.binding.candidate_label == exposed_candidate.label
    assert result.binding.shared_candidate_label is not None
    assert result.binding.source_type is exposed_candidate.source_type
    assert result.binding.selection_risk_level is exposed_candidate.selection_risk_level
    assert result.binding.allowed_target_labels == (
        SharedTargetLabel.candidate_center,
        SharedTargetLabel.candidate_point,
    )
    assert result.binding.metadata["candidate_resolver_readiness_status"] in {
        "ready",
        "conflicted",
    }
    assert result.binding.metadata["candidate_provenance_source_types"]
    assert result.binding.observe_only is True
    assert result.binding.read_only is True
    assert result.binding.non_executing is True


def test_planner_contract_builder_builds_request_and_binds_valid_response() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    builder = ObserveOnlyPlannerContractBuilder()

    request_result = builder.build_request(
        snapshot,
        exposure_view,
        summary="Evaluate the current exposed semantic state for the next safe step.",
        request_id="planner-request-1",
    )
    response_result = builder.bind_response(
        CloudPlannerContract(
            decision_id="planner-response-1",
            summary="Prefer the highest-confidence candidate in dry-run form.",
            action_suggestion=PlannerActionSuggestionContract(
                action_type="candidate_select",
                candidate_id=candidate.candidate_id,
                candidate_label=candidate.label,
                target_label="candidate_center",
                confidence=0.88,
                dry_run_only=True,
                live_execution_requested=False,
            ),
        ),
        exposure_view=exposure_view,
    )

    assert request_result.success is True
    assert request_result.request_contract is not None
    assert request_result.request_contract.signal_status is AiArchitectureSignalStatus.available
    assert request_result.request_contract.snapshot_id == snapshot.snapshot_id
    assert request_result.request_contract.candidate_bindings
    assert request_result.request_contract.observe_only is True
    assert response_result.success is True
    assert response_result.response_contract is not None
    assert response_result.response_contract.action_type.value == "candidate_select"
    assert response_result.response_contract.target_label is SharedTargetLabel.candidate_center
    assert response_result.response_contract.candidate_binding is not None
    assert response_result.response_contract.candidate_binding.candidate_id == candidate.candidate_id
    assert response_result.response_contract.dry_run_only is True
    assert response_result.response_contract.live_execution_requested is False


def test_resolver_contract_builder_builds_request_and_binds_valid_response() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    builder = ObserveOnlyResolverContractBuilder()

    request_result = builder.build_request(
        snapshot,
        exposure_view,
        candidate_id=candidate.candidate_id,
        summary="Resolve the candidate center conservatively.",
        request_id="resolver-request-1",
    )
    response_result = builder.bind_response(
        LocalVisualResolverContract(
            resolution_id="resolver-response-1",
            summary="Return the candidate center point.",
            action_type="candidate_select",
            candidate_id=candidate.candidate_id,
            candidate_label=candidate.label,
            target_label="candidate_center",
            point=_center_point(candidate),
            confidence=0.91,
        ),
        exposure_view=exposure_view,
    )

    assert request_result.success is True
    assert request_result.request_contract is not None
    assert request_result.request_contract.signal_status is AiArchitectureSignalStatus.available
    assert request_result.request_contract.target_candidate_binding.candidate_id == candidate.candidate_id
    assert request_result.request_contract.target_label is SharedTargetLabel.candidate_center
    assert response_result.success is True
    assert response_result.response_contract is not None
    assert response_result.response_contract.action_type.value == "candidate_select"
    assert response_result.response_contract.target_label is SharedTargetLabel.candidate_center
    assert response_result.response_contract.candidate_binding is not None
    assert response_result.response_contract.candidate_binding.candidate_id == candidate.candidate_id
    assert response_result.response_contract.point is not None
    assert response_result.response_contract.point.x == _center_point(candidate).x
    assert response_result.response_contract.point.y == _center_point(candidate).y


def test_contract_builders_handle_incomplete_candidate_metadata_safely() -> None:
    snapshot, exposure_view, _candidate = _boundary_context()
    partial_candidate = replace(
        exposure_view.candidates[0],
        source_type=None,
        selection_risk_level=None,
        source_of_truth_priority=(),
        provenance=(),
        completeness_status="partial",
    )
    partial_exposure_view = replace(
        exposure_view,
        candidates=(partial_candidate,) + exposure_view.candidates[1:],
        signal_status="partial",
    )

    planner_result = ObserveOnlyPlannerContractBuilder().build_request(
        snapshot,
        partial_exposure_view,
        summary="Build a planner request even when one candidate is partial.",
        request_id="planner-request-partial",
    )
    resolver_result = ObserveOnlyResolverContractBuilder().build_request(
        snapshot,
        partial_exposure_view,
        candidate_id=partial_candidate.candidate_id,
        summary="Build a resolver request even when the target candidate is partial.",
        request_id="resolver-request-partial",
    )

    assert planner_result.success is True
    assert planner_result.request_contract is not None
    assert planner_result.request_contract.signal_status is AiArchitectureSignalStatus.partial
    assert partial_candidate.candidate_id in planner_result.request_contract.metadata["partial_candidate_ids"]
    assert resolver_result.success is True
    assert resolver_result.request_contract is not None
    assert resolver_result.request_contract.signal_status is AiArchitectureSignalStatus.partial
    assert resolver_result.request_contract.target_candidate_binding.completeness_status == "partial"
    assert (
        resolver_result.request_contract.target_candidate_binding.metadata[
            "candidate_resolver_readiness_status"
        ]
        == "partial"
    )


def test_planner_response_binding_rejects_invalid_candidate_reference_safely() -> None:
    _snapshot, exposure_view, _candidate = _boundary_context()

    result = ObserveOnlyPlannerContractBuilder().bind_response(
        CloudPlannerContract(
            decision_id="planner-invalid-candidate",
            summary="Reference a missing candidate.",
            action_suggestion=PlannerActionSuggestionContract(
                action_type="candidate_select",
                candidate_id="missing-candidate",
                target_label="candidate_center",
                confidence=0.7,
            ),
        ),
        exposure_view=exposure_view,
    )

    assert result.success is False
    assert result.error_code == "planner_response_bind_exception"
    assert "missing-candidate" in result.error_message


def test_escalation_policy_and_arbitration_remain_consistent() -> None:
    _snapshot, exposure_view, _candidate = _boundary_context()
    binding_result = ObserveOnlySharedOntologyBinder().bind_exposed_candidate(exposure_view.candidates[0])
    assert binding_result.success is True
    assert binding_result.binding is not None
    deterministic_binding = replace(
        binding_result.binding,
        selection_risk_level=CandidateSelectionRiskLevel.high,
        requires_local_resolver=True,
        completeness_status="available",
    )

    decision = ObserveOnlyEscalationPolicyDecider().decide(
        deterministic_binding=deterministic_binding,
    )
    arbitration = ObserveOnlyAiArbitrator().arbitrate(
        deterministic_binding=deterministic_binding,
    )

    assert decision.action is EscalationAction.ask_local_resolver
    assert decision.preferred_source is ArbitrationSource.local_visual_resolver
    assert decision.metadata["selected_rule_id"] == "requires_local_resolver"
    assert arbitration.success is True
    assert arbitration.outcome is not None
    assert arbitration.outcome.escalation_decision.action is EscalationAction.ask_local_resolver
    assert arbitration.outcome.escalation_decision.metadata["selected_rule_id"] == "requires_local_resolver"
    assert arbitration.outcome.metadata["selected_rule_id"] == "requires_local_resolver"
    assert arbitration.details["selected_rule_id"] == "requires_local_resolver"
    assert arbitration.outcome.status.value in {"escalated", "partial"}


def test_arbitration_detects_conflicts_and_escalates_to_cloud_safely() -> None:
    _snapshot, exposure_view, candidate = _boundary_context()
    binder = ObserveOnlySharedOntologyBinder()
    deterministic = binder.bind_exposed_candidate(exposure_view.candidates[0]).binding
    planner_candidate = exposure_view.candidates[-1]
    assert deterministic is not None

    resolver_response_result = ObserveOnlyResolverContractBuilder().bind_response(
        LocalVisualResolverContract(
            resolution_id="resolver-conflict",
            summary="Choose the first candidate.",
            action_type="candidate_select",
            candidate_id=deterministic.candidate_id,
            target_label="candidate_point",
            point=_center_point(candidate),
            confidence=0.9,
        ),
        exposure_view=exposure_view,
    )
    planner_response_result = ObserveOnlyPlannerContractBuilder().bind_response(
        CloudPlannerContract(
            decision_id="planner-conflict",
            summary="Choose a different candidate and ask for live execution.",
            action_suggestion=PlannerActionSuggestionContract(
                action_type="candidate_select",
                candidate_id=planner_candidate.candidate_id,
                candidate_label=planner_candidate.label,
                target_label="candidate_center",
                confidence=0.52,
                live_execution_requested=True,
            ),
        ),
        exposure_view=exposure_view,
    )
    assert resolver_response_result.success is True
    assert resolver_response_result.response_contract is not None
    assert planner_response_result.success is True
    assert planner_response_result.response_contract is not None

    outcome_result = ObserveOnlyAiArbitrator().arbitrate(
        deterministic_binding=replace(
            deterministic,
            source_conflict_present=True,
            selection_risk_level=CandidateSelectionRiskLevel.medium,
            completeness_status="available",
        ),
        resolver_response=resolver_response_result.response_contract,
        planner_response=planner_response_result.response_contract,
        policy=EscalationPolicy(
            block_on_incomplete_contracts=True,
            block_on_unresolved_disagreement=True,
            cloud_planner_for_source_conflict=True,
        ),
    )

    assert outcome_result.success is True
    assert outcome_result.outcome is not None
    assert outcome_result.outcome.escalation_decision.action is EscalationAction.escalate_to_cloud_planner
    assert outcome_result.outcome.selected_source is ArbitrationSource.cloud_planner
    assert outcome_result.outcome.metadata["selected_rule_id"] == "source_conflict_cloud_planner"
    assert any(
        conflict.kind in {
            ArbitrationConflictKind.candidate_reference_mismatch,
            ArbitrationConflictKind.confidence_disagreement,
            ArbitrationConflictKind.safety_ineligibility,
        }
        for conflict in outcome_result.outcome.conflicts
    )
    assert outcome_result.outcome.metadata["evaluated_source_pairs"] == (
        "deterministic_pipeline->local_visual_resolver",
        "deterministic_pipeline->cloud_planner",
        "local_visual_resolver->cloud_planner",
    )
    assert outcome_result.details["selected_rule_id"] == "source_conflict_cloud_planner"


def test_escalation_policy_decider_preserves_exception_visibility_in_failsafe_mode() -> None:
    _snapshot, exposure_view, _candidate = _boundary_context()
    binding_result = ObserveOnlySharedOntologyBinder().bind_exposed_candidate(exposure_view.candidates[0])
    assert binding_result.success is True
    assert binding_result.binding is not None

    decision = _ExplodingEscalationPolicyDecider().decide(
        deterministic_binding=binding_result.binding,
        conflicts=(
            ArbitrationConflict(
                kind=ArbitrationConflictKind.confidence_disagreement,
                summary="Exercise policy exception fallback after conflict handling begins.",
                sources=(
                    ArbitrationSource.deterministic_pipeline,
                    ArbitrationSource.local_visual_resolver,
                ),
                candidate_ids=(binding_result.binding.candidate_id,),
            ),
        ),
    )

    assert decision.action is EscalationAction.block_for_user_confirmation
    assert decision.metadata["selected_rule_id"] == "policy_exception_fallback"
    assert decision.metadata["exception_type"] == "RuntimeError"
    assert decision.metadata["exception_stage"] == "decide"


def test_ai_architecture_does_not_propagate_unhandled_exceptions() -> None:
    snapshot, exposure_view, _candidate = _boundary_context()
    binding_result = ObserveOnlySharedOntologyBinder().bind_exposed_candidate(exposure_view.candidates[0])
    assert binding_result.success is True

    planner_result = _ExplodingPlannerContractBuilder().build_request(
        snapshot,
        exposure_view,
        summary="Exercise planner exception safety.",
        request_id="planner-request-explodes",
    )
    arbitration_result = _ExplodingAiArbitrator().arbitrate(
        deterministic_binding=binding_result.binding,
    )

    assert planner_result.success is False
    assert planner_result.error_code == "planner_request_build_exception"
    assert planner_result.error_message == "planner contract builder exploded"
    assert arbitration_result.success is False
    assert arbitration_result.error_code == "ai_arbitration_exception"
    assert arbitration_result.error_message == "ai arbitrator exploded"
