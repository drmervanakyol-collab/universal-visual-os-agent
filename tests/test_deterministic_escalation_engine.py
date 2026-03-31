from __future__ import annotations

from dataclasses import replace

from test_ai_boundary_contracts import _boundary_context, _center_point

from universal_visual_os_agent.ai_architecture import (
    AiArchitectureSignalStatus,
    ArbitrationConflict,
    ArbitrationConflictKind,
    ArbitrationSource,
    DeterministicEscalationDisposition,
    DeterministicEscalationReason,
    ObserveOnlyDeterministicEscalationEngine,
    ObserveOnlyPlannerContractBuilder,
    ObserveOnlyResolverContractBuilder,
    ObserveOnlySharedOntologyBinder,
)
from universal_visual_os_agent.ai_boundary import (
    CloudPlannerContract,
    LocalVisualResolverContract,
    PlannerActionSuggestionContract,
)
from universal_visual_os_agent.semantics import CandidateSelectionRiskLevel


class _ExplodingDeterministicEscalationEngine(ObserveOnlyDeterministicEscalationEngine):
    def _build_decision(
        self,
        *,
        deterministic_binding,
        resolver_response,
        planner_response,
        conflicts,
        policy,
        signal_status,
    ):
        del deterministic_binding, resolver_response, planner_response, conflicts, policy, signal_status
        raise RuntimeError("deterministic escalation exploded")


def _binding():
    _snapshot, exposure_view, candidate = _boundary_context()
    binding_result = ObserveOnlySharedOntologyBinder().bind_exposed_candidate(exposure_view.candidates[0])
    assert binding_result.success is True
    assert binding_result.binding is not None
    return binding_result.binding, exposure_view, candidate


def test_deterministic_escalation_returns_deterministic_ok_for_clear_candidate() -> None:
    binding, _exposure_view, _candidate = _binding()

    result = ObserveOnlyDeterministicEscalationEngine().evaluate(
        deterministic_binding=replace(
            binding,
            confidence=0.98,
            selection_risk_level=CandidateSelectionRiskLevel.low,
            requires_local_resolver=False,
            disambiguation_needed=False,
            source_conflict_present=False,
            completeness_status="available",
        )
    )

    assert result.success is True
    assert result.decision is not None
    assert result.decision.disposition is DeterministicEscalationDisposition.deterministic_ok
    assert result.decision.recommended_source is ArbitrationSource.deterministic_pipeline
    assert result.decision.reason_codes == (DeterministicEscalationReason.deterministic_sufficient,)
    assert result.decision.metadata["selected_rule_id"] == "deterministic_ok_clear"
    assert result.details["selected_rule_id"] == "deterministic_ok_clear"
    assert result.decision.observe_only is True
    assert result.decision.read_only is True
    assert result.decision.non_executing is True


def test_deterministic_escalation_recommends_local_resolver_for_ambiguity() -> None:
    binding, _exposure_view, _candidate = _binding()

    result = ObserveOnlyDeterministicEscalationEngine().evaluate(
        deterministic_binding=replace(
            binding,
            confidence=0.83,
            selection_risk_level=CandidateSelectionRiskLevel.medium,
            disambiguation_needed=True,
            requires_local_resolver=False,
            source_conflict_present=False,
            completeness_status="available",
        )
    )

    assert result.success is True
    assert result.decision is not None
    assert result.decision.disposition is DeterministicEscalationDisposition.local_resolver_recommended
    assert result.decision.recommended_source is ArbitrationSource.local_visual_resolver
    assert DeterministicEscalationReason.disambiguation_needed in result.decision.reason_codes
    assert result.decision.metadata["selected_rule_id"] == "local_resolver_recommended"
    assert result.details["selected_rule_id"] == "local_resolver_recommended"


def test_deterministic_escalation_recommends_cloud_planner_for_source_conflict() -> None:
    binding, _exposure_view, _candidate = _binding()

    result = ObserveOnlyDeterministicEscalationEngine().evaluate(
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

    assert result.success is True
    assert result.decision is not None
    assert result.decision.disposition is DeterministicEscalationDisposition.cloud_planner_recommended
    assert result.decision.recommended_source is ArbitrationSource.cloud_planner
    assert DeterministicEscalationReason.source_conflict_present in result.decision.reason_codes
    assert result.decision.metadata["selected_rule_id"] == "planner_recommended_for_conflict"
    assert result.details["selected_rule_id"] == "planner_recommended_for_conflict"


def test_deterministic_escalation_requires_human_confirmation_for_high_risk_multi_source_conflict() -> None:
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

    conflicts = (
        ArbitrationConflict(
            kind=ArbitrationConflictKind.candidate_reference_mismatch,
            summary="Deterministic and planner candidate IDs differ.",
            sources=(
                ArbitrationSource.deterministic_pipeline,
                ArbitrationSource.cloud_planner,
            ),
            candidate_ids=(binding.candidate_id, planner_candidate.candidate_id),
        ),
    )

    result = ObserveOnlyDeterministicEscalationEngine().evaluate(
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
        conflicts=conflicts,
    )

    assert result.success is True
    assert result.decision is not None
    assert result.decision.disposition is DeterministicEscalationDisposition.human_confirmation_required
    assert result.decision.recommended_source is None
    assert DeterministicEscalationReason.conflicting_high_risk_signals in result.decision.reason_codes
    assert result.decision.metadata["selected_rule_id"] == "resolver_conflict_human_confirmation"
    assert result.details["selected_rule_id"] == "resolver_conflict_human_confirmation"


def test_deterministic_escalation_blocks_on_missing_or_partial_input() -> None:
    binding, exposure_view, candidate = _binding()
    resolver_response_result = ObserveOnlyResolverContractBuilder().bind_response(
        LocalVisualResolverContract(
            resolution_id="resolver-partial",
            summary="Return the candidate center point.",
            action_type="candidate_select",
            candidate_id=binding.candidate_id,
            candidate_label=binding.candidate_label,
            target_label="candidate_center",
            point=_center_point(candidate),
            confidence=0.91,
        ),
        exposure_view=exposure_view,
    )
    assert resolver_response_result.success is True
    assert resolver_response_result.response_contract is not None

    missing_result = ObserveOnlyDeterministicEscalationEngine().evaluate(
        deterministic_binding=None,
    )
    partial_result = ObserveOnlyDeterministicEscalationEngine().evaluate(
        deterministic_binding=replace(binding, completeness_status="partial"),
        resolver_response=replace(
            resolver_response_result.response_contract,
            signal_status=AiArchitectureSignalStatus.partial,
        ),
    )

    assert missing_result.success is True
    assert missing_result.decision is not None
    assert missing_result.decision.disposition is DeterministicEscalationDisposition.blocked
    assert missing_result.decision.reason_codes == (
        DeterministicEscalationReason.deterministic_binding_missing,
    )
    assert missing_result.decision.metadata["selected_rule_id"] == "blocked_missing_binding"
    assert partial_result.success is True
    assert partial_result.decision is not None
    assert partial_result.decision.disposition is DeterministicEscalationDisposition.blocked
    assert partial_result.decision.signal_status.value == "partial"
    assert partial_result.decision.reason_codes == (
        DeterministicEscalationReason.deterministic_binding_partial,
    )
    assert partial_result.decision.metadata["selected_rule_id"] == "blocked_partial_binding"


def test_deterministic_escalation_does_not_propagate_unhandled_exceptions() -> None:
    binding, _exposure_view, _candidate = _binding()

    result = _ExplodingDeterministicEscalationEngine().evaluate(
        deterministic_binding=binding,
    )

    assert result.success is False
    assert result.error_code == "deterministic_escalation_exception"
    assert result.error_message == "deterministic escalation exploded"
    assert result.details["exception_type"] == "RuntimeError"
    assert result.details["exception_stage"] == "evaluate"
