from __future__ import annotations

from dataclasses import replace

from test_semantic_delta import _after_snapshot, _scored_snapshot

from universal_visual_os_agent.semantics import SemanticDeltaCategory, SemanticTextStatus
from universal_visual_os_agent.verification import (
    CandidateScoreDeltaDirection,
    ExpectedSemanticChange,
    ExpectedSemanticOutcome,
    GoalOrientedSemanticVerifier,
    SemanticStateTransition,
    SemanticTransitionExpectation,
    VerificationStatus,
    evaluate_semantic_transition,
)


class _ExplodingComparator:
    def compare(self, before, after):
        raise RuntimeError("goal-oriented comparator exploded")


def _successful_transition() -> tuple[SemanticStateTransition, str, str]:
    before = _scored_snapshot()
    after = _after_snapshot(before)
    changed_text_region_id = next(
        region.region_id
        for region in before.text_regions
        if region.label == "Top Analysis Band"
    )
    changed_candidate_id = next(
        candidate.candidate_id
        for candidate in before.candidates
        if candidate.candidate_class is not None and candidate.candidate_class.value == "button_like"
    )
    return SemanticStateTransition(before=before, after=after), changed_text_region_id, changed_candidate_id


def test_goal_oriented_verification_succeeds_for_expected_semantic_outcomes() -> None:
    transition, changed_text_region_id, changed_candidate_id = _successful_transition()
    expectation = SemanticTransitionExpectation(
        summary="Expected semantic outcomes occurred",
        required_candidate_ids=(changed_candidate_id,),
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id="region-appeared",
                category=SemanticDeltaCategory.layout_region,
                item_id="layout-region-added",
                expected_change=ExpectedSemanticChange.appeared,
            ),
            ExpectedSemanticOutcome(
                outcome_id="text-changed",
                category=SemanticDeltaCategory.text_region,
                item_id=changed_text_region_id,
                expected_change=ExpectedSemanticChange.changed,
                required_changed_fields=("extracted_text",),
                expected_after_state={"extracted_text": "Home Projects Settings Help"},
            ),
            ExpectedSemanticOutcome(
                outcome_id="candidate-score-decreased",
                category=SemanticDeltaCategory.candidate,
                item_id=changed_candidate_id,
                expected_change=ExpectedSemanticChange.changed,
                required_changed_fields=("confidence",),
                minimum_score_delta=0.01,
                score_delta_direction=CandidateScoreDeltaDirection.decreased,
            ),
            ExpectedSemanticOutcome(
                outcome_id="metadata-marker-added",
                category=SemanticDeltaCategory.snapshot_metadata,
                item_id="delta_phase_marker",
                expected_change=ExpectedSemanticChange.appeared,
                expected_after_state={"value": "after"},
            ),
        ),
    )

    result = evaluate_semantic_transition(expectation, transition)

    assert result.status is VerificationStatus.satisfied
    assert result.success is True
    assert result.semantic_delta is not None
    assert result.matched_candidate_ids == (changed_candidate_id,)
    assert result.matched_outcome_ids == (
        "region-appeared",
        "text-changed",
        "candidate-score-decreased",
        "metadata-marker-added",
    )
    assert result.unsatisfied_outcome_ids == ()
    assert result.unknown_outcome_ids == ()
    assert all(
        verification.status is VerificationStatus.satisfied
        for verification in result.outcome_verifications
    )


def test_goal_oriented_verification_fails_when_expected_outcomes_do_not_occur() -> None:
    transition, changed_text_region_id, changed_candidate_id = _successful_transition()
    expectation = SemanticTransitionExpectation(
        summary="Incorrect semantic outcomes should fail",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id="candidate-score-increased",
                category=SemanticDeltaCategory.candidate,
                item_id=changed_candidate_id,
                expected_change=ExpectedSemanticChange.changed,
                required_changed_fields=("confidence",),
                minimum_score_delta=0.01,
                score_delta_direction=CandidateScoreDeltaDirection.increased,
            ),
            ExpectedSemanticOutcome(
                outcome_id="text-changed-to-wrong-value",
                category=SemanticDeltaCategory.text_region,
                item_id=changed_text_region_id,
                expected_change=ExpectedSemanticChange.changed,
                expected_after_state={"extracted_text": "Completely different text"},
            ),
        ),
    )

    result = GoalOrientedSemanticVerifier().verify(expectation, transition)

    assert result.status is VerificationStatus.unsatisfied
    assert result.success is False
    assert result.unsatisfied_outcome_ids == (
        "candidate-score-increased",
        "text-changed-to-wrong-value",
    )
    assert result.matched_outcome_ids == ()
    assert all(
        verification.status is VerificationStatus.unsatisfied
        for verification in result.outcome_verifications
    )


def test_goal_oriented_verification_handles_partial_inputs_safely() -> None:
    before = _scored_snapshot()
    target_region = next(region for region in before.text_regions if region.label == "Top Analysis Band")
    partial_after = replace(
        before,
        text_regions=tuple(
            replace(region, extracted_text=None, status=SemanticTextStatus.extracted)
            if region.region_id == target_region.region_id
            else region
            for region in before.text_regions
        ),
    )
    expectation = SemanticTransitionExpectation(
        summary="Partial text verification should remain safe",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id="top-text-changed",
                category=SemanticDeltaCategory.text_region,
                item_id=target_region.region_id,
                expected_change=ExpectedSemanticChange.changed,
                required_changed_fields=("extracted_text",),
                expected_after_state={"extracted_text": "Home Projects Settings Help"},
            ),
        ),
    )

    result = GoalOrientedSemanticVerifier().verify(
        expectation,
        SemanticStateTransition(before=before, after=partial_after),
    )

    assert result.status is VerificationStatus.unknown
    assert result.success is False
    assert result.unknown_outcome_ids == ("top-text-changed",)
    assert result.outcome_verifications[0].status is VerificationStatus.unknown
    assert result.semantic_delta is not None
    assert result.semantic_delta.signal_status == "partial"


def test_goal_oriented_verification_output_is_deterministic() -> None:
    transition, changed_text_region_id, changed_candidate_id = _successful_transition()
    expectation = SemanticTransitionExpectation(
        summary="Verification output order should be stable",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id="text-check",
                category=SemanticDeltaCategory.text_region,
                item_id=changed_text_region_id,
                expected_change=ExpectedSemanticChange.changed,
                required_changed_fields=("extracted_text",),
            ),
            ExpectedSemanticOutcome(
                outcome_id="candidate-check",
                category=SemanticDeltaCategory.candidate,
                item_id=changed_candidate_id,
                expected_change=ExpectedSemanticChange.changed,
                required_changed_fields=("confidence",),
                minimum_score_delta=0.01,
                score_delta_direction=CandidateScoreDeltaDirection.decreased,
            ),
            ExpectedSemanticOutcome(
                outcome_id="metadata-check",
                category=SemanticDeltaCategory.snapshot_metadata,
                item_id="delta_phase_marker",
                expected_change=ExpectedSemanticChange.appeared,
            ),
        ),
    )

    result = GoalOrientedSemanticVerifier().verify(expectation, transition)

    assert result.status is VerificationStatus.satisfied
    assert tuple(verification.outcome_id for verification in result.outcome_verifications) == (
        "text-check",
        "candidate-check",
        "metadata-check",
    )
    assert result.matched_outcome_ids == (
        "text-check",
        "candidate-check",
        "metadata-check",
    )


def test_goal_oriented_verification_preserves_observe_only_semantics() -> None:
    transition, changed_text_region_id, _ = _successful_transition()
    expectation = SemanticTransitionExpectation(
        summary="Observe-only verification should remain non-actionable",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id="text-check",
                category=SemanticDeltaCategory.text_region,
                item_id=changed_text_region_id,
                expected_change=ExpectedSemanticChange.changed,
                required_changed_fields=("extracted_text",),
            ),
        ),
    )

    result = GoalOrientedSemanticVerifier().verify(expectation, transition)

    assert result.observe_only is True
    assert result.read_only is True
    assert result.non_actionable is True
    assert result.evidence["observe_only"] is True
    assert result.semantic_delta is not None
    assert result.semantic_delta.observe_only is True
    for verification in result.outcome_verifications:
        assert verification.observe_only is True
        assert verification.read_only is True
        assert verification.non_actionable is True


def test_goal_oriented_verification_does_not_propagate_unhandled_exceptions() -> None:
    transition, changed_text_region_id, _ = _successful_transition()
    expectation = SemanticTransitionExpectation(
        summary="Exception handling should stay safe",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id="text-check",
                category=SemanticDeltaCategory.text_region,
                item_id=changed_text_region_id,
                expected_change=ExpectedSemanticChange.changed,
            ),
        ),
    )

    result = GoalOrientedSemanticVerifier(
        delta_comparator=_ExplodingComparator()
    ).verify(expectation, transition)

    assert result.status is VerificationStatus.unknown
    assert result.success is False
    assert result.evidence["exception_type"] == "RuntimeError"
    assert result.evidence["exception_message"] == "goal-oriented comparator exploded"
