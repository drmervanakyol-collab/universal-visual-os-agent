from __future__ import annotations

from dataclasses import replace

from test_semantic_candidate_exposure import _scored_snapshot

from universal_visual_os_agent.actions import (
    ActionIntentReasonCode,
    ActionIntentStatus,
    ActionRequirementStatus,
    ObserveOnlyActionIntentScaffolder,
)
from universal_visual_os_agent.semantics import ObserveOnlyCandidateExposer


class _ExplodingActionIntentScaffolder(ObserveOnlyActionIntentScaffolder):
    def _build_intents(self, snapshot, *, exposure_view):
        del snapshot, exposure_view
        raise RuntimeError("action intent scaffolder exploded")


def _exposure_view():
    snapshot = _scored_snapshot()
    exposure_result = ObserveOnlyCandidateExposer().expose(snapshot)
    assert exposure_result.success is True
    assert exposure_result.exposure_view is not None
    return snapshot, exposure_result.exposure_view


def test_action_intent_scaffolding_builds_non_executing_candidate_select_intents() -> None:
    snapshot, exposure_view = _exposure_view()

    result = ObserveOnlyActionIntentScaffolder().scaffold(snapshot, exposure_view=exposure_view)

    assert result.success is True
    assert result.scaffold_view is not None
    scaffold_view = result.scaffold_view
    assert scaffold_view.total_exposed_candidate_count == exposure_view.exposed_candidate_count
    assert scaffold_view.scaffolded_intent_count == len(scaffold_view.intents)
    assert scaffold_view.incomplete_intent_count == 0
    assert scaffold_view.blocked_intent_count == 0
    assert scaffold_view.signal_status == "available"
    assert all(intent.action_type == "candidate_select" for intent in scaffold_view.intents)
    assert all(intent.status is ActionIntentStatus.scaffolded for intent in scaffold_view.intents)
    assert all(intent.dry_run_only is True for intent in scaffold_view.intents)
    assert all(intent.executable is False for intent in scaffold_view.intents)
    assert all(intent.observe_only_source is True for intent in scaffold_view.intents)
    assert all(intent.target is not None for intent in scaffold_view.intents)


def test_action_intent_scaffolding_metadata_is_consistent() -> None:
    snapshot, exposure_view = _exposure_view()

    result = ObserveOnlyActionIntentScaffolder().scaffold(snapshot, exposure_view=exposure_view)

    assert result.success is True
    assert result.scaffold_view is not None
    scaffold_view = result.scaffold_view
    exposed_candidates_by_id = {
        candidate.candidate_id: candidate for candidate in exposure_view.candidates
    }
    assert scaffold_view.metadata["sorted_intent_ids"] == tuple(
        intent.intent_id for intent in scaffold_view.intents
    )
    assert scaffold_view.metadata["source_exposed_candidate_ids"] == tuple(
        candidate.candidate_id for candidate in exposure_view.candidates
    )
    for intent in scaffold_view.intents:
        source_exposed_candidate = exposed_candidates_by_id[intent.candidate_id]
        source_snapshot_candidate = snapshot.get_candidate(intent.candidate_id)
        assert source_snapshot_candidate is not None
        assert intent.candidate_label == source_exposed_candidate.label
        assert intent.candidate_rank == source_exposed_candidate.rank
        assert intent.candidate_score == source_exposed_candidate.score
        assert intent.metadata["action_intent_scaffolded"] is True
        assert intent.metadata["source_snapshot_id"] == snapshot.snapshot_id
        assert intent.metadata["source_candidate_id"] == intent.candidate_id
        assert intent.metadata["precondition_ids"] == tuple(
            requirement.requirement_id for requirement in intent.precondition_requirements
        )
        assert intent.metadata["target_validation_ids"] == tuple(
            validation.validation_id for validation in intent.target_validation_requirements
        )
        assert intent.metadata["safety_gate_ids"] == tuple(
            gate.gate_id for gate in intent.safety_gating_requirements
        )
        assert intent.target is not None
        assert intent.target.x == source_snapshot_candidate.bounds.left + (
            source_snapshot_candidate.bounds.width / 2.0
        )
        assert intent.target.y == source_snapshot_candidate.bounds.top + (
            source_snapshot_candidate.bounds.height / 2.0
        )


def test_action_intent_scaffolding_handles_incomplete_candidate_metadata_safely() -> None:
    snapshot, exposure_view = _exposure_view()
    incomplete_candidate = replace(
        exposure_view.candidates[0],
        score=None,
        source_layout_region_id="missing-layout-region",
        completeness_status="partial",
        metadata={
            **dict(exposure_view.candidates[0].metadata),
            "candidate_exposure_completeness_status": "partial",
        },
    )
    partial_exposure_view = replace(
        exposure_view,
        candidates=(incomplete_candidate, *exposure_view.candidates[1:]),
        signal_status="partial",
    )

    result = ObserveOnlyActionIntentScaffolder().scaffold(
        snapshot,
        exposure_view=partial_exposure_view,
    )

    assert result.success is True
    assert result.scaffold_view is not None
    scaffold_view = result.scaffold_view
    incomplete_intent = next(
        intent for intent in scaffold_view.intents if intent.candidate_id == incomplete_candidate.candidate_id
    )
    assert scaffold_view.signal_status == "partial"
    assert scaffold_view.metadata["upstream_partial_input"] is True
    assert incomplete_candidate.candidate_id in scaffold_view.metadata["missing_layout_region_ids"]
    assert incomplete_candidate.candidate_id in scaffold_view.metadata["incomplete_candidate_ids"]
    assert incomplete_intent.status is ActionIntentStatus.incomplete
    assert incomplete_intent.reason_code is ActionIntentReasonCode.incomplete_candidate_metadata
    assert incomplete_intent.candidate_score is None
    assert any(
        requirement.requirement_id == "candidate_score_available"
        and requirement.status is ActionRequirementStatus.blocked
        for requirement in incomplete_intent.precondition_requirements
    )
    assert any(
        validation.validation_id == "source_layout_region_consistency"
        and validation.status is ActionRequirementStatus.blocked
        for validation in incomplete_intent.target_validation_requirements
    )


def test_action_intent_scaffolding_propagates_upstream_partial_signal_safely() -> None:
    snapshot, exposure_view = _exposure_view()
    partial_exposure_view = replace(
        exposure_view,
        signal_status="partial",
        metadata={
            **dict(exposure_view.metadata),
            "scoring_metadata_incomplete": True,
        },
    )

    result = ObserveOnlyActionIntentScaffolder().scaffold(
        snapshot,
        exposure_view=partial_exposure_view,
    )

    assert result.success is True
    assert result.scaffold_view is not None
    assert result.scaffold_view.signal_status == "partial"
    assert result.scaffold_view.metadata["upstream_signal_status"] == "partial"
    assert result.scaffold_view.metadata["upstream_partial_input"] is True
    assert all(
        intent.status is ActionIntentStatus.scaffolded
        for intent in result.scaffold_view.intents
    )


def test_action_intent_scaffolding_requires_matching_observe_only_exposure_view() -> None:
    snapshot, exposure_view = _exposure_view()
    unsafe_exposure_view = replace(
        exposure_view,
        metadata={
            **dict(exposure_view.metadata),
            "observe_only": False,
        },
    )

    unsafe_result = ObserveOnlyActionIntentScaffolder().scaffold(
        snapshot,
        exposure_view=unsafe_exposure_view,
    )

    assert unsafe_result.success is False
    assert unsafe_result.error_code == "candidate_exposure_unavailable"

    mismatched_snapshot_result = ObserveOnlyActionIntentScaffolder().scaffold(
        snapshot,
        exposure_view=replace(exposure_view, snapshot_id="different-snapshot"),
    )

    assert mismatched_snapshot_result.success is False
    assert mismatched_snapshot_result.error_code == "candidate_exposure_snapshot_mismatch"


def test_action_intent_scaffolding_preserves_observe_only_non_executing_semantics() -> None:
    snapshot, exposure_view = _exposure_view()

    result = ObserveOnlyActionIntentScaffolder().scaffold(snapshot, exposure_view=exposure_view)

    assert result.success is True
    assert result.scaffold_view is not None
    for intent in result.scaffold_view.intents:
        assert intent.dry_run_only is True
        assert intent.executable is False
        assert intent.observe_only_source is True
        assert intent.metadata["observe_only"] is True
        assert intent.metadata["analysis_only"] is True
        assert intent.metadata["non_executing"] is True
        assert intent.metadata["dry_run_only"] is True
        assert intent.metadata["live_execution_allowed"] is False
        assert any(
            gate.gate_id == "dry_run_only_enforced"
            and gate.status is ActionRequirementStatus.satisfied
            for gate in intent.safety_gating_requirements
        )
        assert any(
            gate.gate_id == "explicit_execution_enablement_required"
            and gate.status is ActionRequirementStatus.pending
            for gate in intent.safety_gating_requirements
        )


def test_action_intent_scaffolding_does_not_propagate_unhandled_exceptions() -> None:
    snapshot, exposure_view = _exposure_view()

    result = _ExplodingActionIntentScaffolder().scaffold(snapshot, exposure_view=exposure_view)

    assert result.success is False
    assert result.error_code == "action_intent_scaffolding_exception"
    assert result.error_message == "action intent scaffolder exploded"
