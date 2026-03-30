from __future__ import annotations

from dataclasses import replace

from test_action_intent_scaffolding import _exposure_view

from universal_visual_os_agent.actions import (
    ActionIntentReasonCode,
    ActionIntentStatus,
    ActionRequirementStatus,
    DryRunActionDisposition,
    ObserveOnlyActionIntentScaffolder,
    ObserveOnlyDryRunActionEngine,
)
from universal_visual_os_agent.geometry import NormalizedPoint


class _ExplodingDryRunActionEngine(ObserveOnlyDryRunActionEngine):
    def _evaluate_intent(self, intent, *, snapshot):
        del intent, snapshot
        raise RuntimeError("dry-run action engine exploded")


def _scaffold_view():
    snapshot, exposure_view = _exposure_view()
    scaffolding_result = ObserveOnlyActionIntentScaffolder().scaffold(
        snapshot,
        exposure_view=exposure_view,
    )
    assert scaffolding_result.success is True
    assert scaffolding_result.scaffold_view is not None
    return snapshot, scaffolding_result.scaffold_view


def test_dry_run_action_engine_evaluates_scaffolded_intents_without_execution() -> None:
    snapshot, scaffold_view = _scaffold_view()
    engine = ObserveOnlyDryRunActionEngine()

    batch_result = engine.evaluate_scaffold(scaffold_view, snapshot=snapshot)
    single_result = engine.evaluate_intent(scaffold_view.intents[0], snapshot=snapshot)
    action_result = engine.execute(scaffold_view.intents[0])

    assert batch_result.success is True
    assert batch_result.evaluation_view is not None
    evaluation_view = batch_result.evaluation_view
    assert evaluation_view.would_execute_count == len(evaluation_view.evaluations)
    assert evaluation_view.would_block_count == 0
    assert evaluation_view.incomplete_count == 0
    assert evaluation_view.rejected_count == 0
    assert evaluation_view.signal_status == "available"
    assert all(
        evaluation.disposition is DryRunActionDisposition.would_execute
        for evaluation in evaluation_view.evaluations
    )
    assert all(evaluation.simulated is True for evaluation in evaluation_view.evaluations)
    assert all(evaluation.non_executing is True for evaluation in evaluation_view.evaluations)
    assert all(
        "explicit_execution_enablement_required" in evaluation.pending_safety_gate_ids
        for evaluation in evaluation_view.evaluations
    )
    assert single_result.success is True
    assert single_result.evaluation is not None
    assert single_result.evaluation.disposition is DryRunActionDisposition.would_execute
    assert action_result.accepted is True
    assert action_result.simulated is True
    assert action_result.details["non_executing"] is True


def test_dry_run_action_engine_marks_blocked_intents_as_would_block() -> None:
    snapshot, scaffold_view = _scaffold_view()
    first_intent = scaffold_view.intents[0]
    blocked_gate = replace(
        first_intent.safety_gating_requirements[0],
        status=ActionRequirementStatus.blocked,
    )
    blocked_intent = replace(
        first_intent,
        status=ActionIntentStatus.blocked,
        reason_code=ActionIntentReasonCode.safety_gating_required,
        reason="Safety gate blocked in dry-run test.",
        safety_gating_requirements=(blocked_gate, *first_intent.safety_gating_requirements[1:]),
    )
    blocked_scaffold_view = replace(
        scaffold_view,
        intents=(blocked_intent, *scaffold_view.intents[1:]),
        scaffolded_intent_count=scaffold_view.scaffolded_intent_count - 1,
        blocked_intent_count=scaffold_view.blocked_intent_count + 1,
        signal_status="partial",
    )

    result = ObserveOnlyDryRunActionEngine().evaluate_scaffold(
        blocked_scaffold_view,
        snapshot=snapshot,
    )

    assert result.success is True
    assert result.evaluation_view is not None
    blocked_evaluation = result.evaluation_view.evaluations[0]
    assert blocked_evaluation.disposition is DryRunActionDisposition.would_block
    assert blocked_evaluation.blocked_safety_gate_ids == ("observe_only_origin_confirmed",)
    assert blocked_evaluation.blocking_reasons


def test_dry_run_action_engine_marks_incomplete_intents_as_incomplete() -> None:
    snapshot, scaffold_view = _scaffold_view()
    first_intent = scaffold_view.intents[0]
    blocked_precondition = replace(
        first_intent.precondition_requirements[1],
        status=ActionRequirementStatus.blocked,
    )
    incomplete_intent = replace(
        first_intent,
        status=ActionIntentStatus.incomplete,
        reason_code=ActionIntentReasonCode.incomplete_candidate_metadata,
        reason="Candidate metadata incomplete in dry-run test.",
        candidate_score=None,
        precondition_requirements=(
            first_intent.precondition_requirements[0],
            blocked_precondition,
            *first_intent.precondition_requirements[2:],
        ),
    )
    incomplete_scaffold_view = replace(
        scaffold_view,
        intents=(incomplete_intent, *scaffold_view.intents[1:]),
        scaffolded_intent_count=scaffold_view.scaffolded_intent_count - 1,
        incomplete_intent_count=scaffold_view.incomplete_intent_count + 1,
        signal_status="partial",
    )

    result = ObserveOnlyDryRunActionEngine().evaluate_scaffold(
        incomplete_scaffold_view,
        snapshot=snapshot,
    )

    assert result.success is True
    assert result.evaluation_view is not None
    incomplete_evaluation = result.evaluation_view.evaluations[0]
    assert incomplete_evaluation.disposition is DryRunActionDisposition.incomplete
    assert incomplete_evaluation.missing_precondition_ids == ("candidate_score_available",)
    assert incomplete_evaluation.blocking_reasons
    assert result.evaluation_view.signal_status == "partial"


def test_dry_run_action_engine_revalidates_target_requirements_against_snapshot() -> None:
    snapshot, scaffold_view = _scaffold_view()
    source_layout_region_id = scaffold_view.intents[0].metadata["source_layout_region_id"]
    changed_snapshot = replace(
        snapshot,
        snapshot_id="changed-snapshot",
        layout_regions=tuple(
            region
            for region in snapshot.layout_regions
            if region.region_id != source_layout_region_id
        ),
    )

    result = ObserveOnlyDryRunActionEngine().evaluate_scaffold(
        scaffold_view,
        snapshot=changed_snapshot,
    )

    assert result.success is True
    assert result.evaluation_view is not None
    blocked_evaluation = result.evaluation_view.evaluations[0]
    assert blocked_evaluation.disposition is DryRunActionDisposition.would_block
    assert (
        "source_layout_region_consistency"
        in blocked_evaluation.failed_target_validation_ids
    )
    assert blocked_evaluation.metadata["evaluation_snapshot_id"] == "changed-snapshot"


def test_dry_run_action_engine_rejects_invalid_target_candidate_binding_at_final_boundary() -> None:
    snapshot, scaffold_view = _scaffold_view()
    intent = scaffold_view.intents[0]
    assert intent.candidate_id is not None
    assert intent.target is not None
    candidate = snapshot.get_candidate(intent.candidate_id)
    assert candidate is not None

    candidate_right = candidate.bounds.left + candidate.bounds.width
    if candidate_right <= 0.98:
        invalid_x = min(1.0, candidate_right + 0.01)
    else:
        invalid_x = max(0.0, candidate.bounds.left - 0.01)
    tampered_intent = replace(
        intent,
        target=NormalizedPoint(x=invalid_x, y=intent.target.y),
    )

    result = ObserveOnlyDryRunActionEngine().evaluate_intent(
        tampered_intent,
        snapshot=snapshot,
    )

    assert result.success is True
    assert result.evaluation is not None
    assert result.evaluation.disposition is DryRunActionDisposition.rejected
    assert "Normalized target no longer matched the bound candidate geometry." in result.evaluation.blocking_reasons
    assert "target_candidate_binding" in result.evaluation.metadata["tool_boundary_blocked_check_ids"]
    assert "target_candidate_mismatch" in result.evaluation.metadata["tool_boundary_blocking_codes"]


def test_dry_run_action_engine_preserves_non_executing_semantics() -> None:
    snapshot, scaffold_view = _scaffold_view()

    result = ObserveOnlyDryRunActionEngine().evaluate_scaffold(scaffold_view, snapshot=snapshot)

    assert result.success is True
    assert result.evaluation_view is not None
    assert result.evaluation_view.metadata["observe_only"] is True
    assert result.evaluation_view.metadata["analysis_only"] is True
    assert result.evaluation_view.metadata["non_executing"] is True
    assert result.evaluation_view.metadata["simulated"] is True
    for evaluation in result.evaluation_view.evaluations:
        assert evaluation.simulated is True
        assert evaluation.non_executing is True
        assert evaluation.metadata["dry_run_evaluated"] is True
        assert evaluation.metadata["non_executing"] is True
        assert evaluation.metadata["simulated"] is True


def test_dry_run_action_engine_does_not_propagate_unhandled_exceptions() -> None:
    snapshot, scaffold_view = _scaffold_view()

    batch_result = _ExplodingDryRunActionEngine().evaluate_scaffold(
        scaffold_view,
        snapshot=snapshot,
    )
    single_result = _ExplodingDryRunActionEngine().evaluate_intent(
        scaffold_view.intents[0],
        snapshot=snapshot,
    )

    assert batch_result.success is False
    assert batch_result.error_code == "dry_run_action_engine_exception"
    assert batch_result.error_message == "dry-run action engine exploded"
    assert single_result.success is False
    assert single_result.error_code == "dry_run_action_engine_exception"
