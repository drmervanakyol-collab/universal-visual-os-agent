from __future__ import annotations

from test_goal_oriented_verification import _successful_transition
from test_semantic_delta import _after_snapshot, _scored_snapshot

from universal_visual_os_agent.semantics import SemanticDeltaCategory
from universal_visual_os_agent.verification import (
    CandidateScoreDeltaDirection,
    ExpectedSemanticChange,
    ExpectedSemanticOutcome,
    GoalOrientedSemanticVerifier,
    SemanticStateTransition,
    SemanticTransitionExpectation,
    VerificationOutcomeBranch,
    VerificationPollAttempt,
    VerificationStatus,
    VerificationTimingPolicy,
)


def test_time_aware_verification_succeeds_on_delayed_poll_attempt() -> None:
    before = _scored_snapshot()
    delayed_after = _after_snapshot(before)
    expectation = SemanticTransitionExpectation(
        summary="Verification should tolerate one delayed semantic update.",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id="metadata-marker-added",
                category=SemanticDeltaCategory.snapshot_metadata,
                item_id="delta_phase_marker",
                expected_change=ExpectedSemanticChange.appeared,
                expected_after_state={"value": "after"},
            ),
        ),
        timing=VerificationTimingPolicy(
            timeout_seconds=1.0,
            poll_interval_ms=100,
            max_poll_attempts=3,
        ),
    )

    result = GoalOrientedSemanticVerifier().verify(
        expectation,
        SemanticStateTransition(
            before=before,
            after=before,
            poll_attempts=(
                VerificationPollAttempt(
                    attempt_index=2,
                    before=before,
                    after=delayed_after,
                    elapsed_seconds=0.2,
                ),
            ),
        ),
    )

    assert result.status is VerificationStatus.satisfied
    assert result.success is True
    assert result.poll_attempt_count == 2
    assert result.selected_poll_attempt == 2
    assert result.selected_elapsed_seconds == 0.2
    assert result.evidence["verification_polling_used"] is True
    assert result.matched_outcome_ids == ("metadata-marker-added",)


def test_time_aware_verification_respects_timeout_window() -> None:
    before = _scored_snapshot()
    delayed_success = _after_snapshot(before)
    expectation = SemanticTransitionExpectation(
        summary="Verification should stop at the configured timeout window.",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id="metadata-marker-added",
                category=SemanticDeltaCategory.snapshot_metadata,
                item_id="delta_phase_marker",
                expected_change=ExpectedSemanticChange.appeared,
                expected_after_state={"value": "after"},
            ),
        ),
        timing=VerificationTimingPolicy(
            timeout_seconds=0.5,
            poll_interval_ms=100,
            max_poll_attempts=4,
        ),
    )

    result = GoalOrientedSemanticVerifier().verify(
        expectation,
        SemanticStateTransition(
            before=before,
            after=before,
            poll_attempts=(
                VerificationPollAttempt(
                    attempt_index=2,
                    before=before,
                    after=before,
                    elapsed_seconds=0.1,
                ),
                VerificationPollAttempt(
                    attempt_index=3,
                    before=before,
                    after=delayed_success,
                    elapsed_seconds=0.9,
                ),
            ),
        ),
    )

    assert result.status is VerificationStatus.unsatisfied
    assert result.success is False
    assert result.poll_attempt_count == 2
    assert result.selected_poll_attempt == 2
    assert result.selected_elapsed_seconds == 0.1
    assert result.evidence["verification_total_provided_attempt_count"] == 3
    assert result.unsatisfied_outcome_ids == ("metadata-marker-added",)


def test_time_aware_verification_accepts_alternate_outcome_branch() -> None:
    transition, _, changed_candidate_id = _successful_transition()
    expectation = SemanticTransitionExpectation(
        summary="Either the candidate score drops or the metadata marker appears.",
        alternate_outcome_branches=(
            VerificationOutcomeBranch(
                branch_id="candidate-score-increased",
                summary="Incorrect candidate branch",
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
                ),
            ),
            VerificationOutcomeBranch(
                branch_id="metadata-marker-appeared",
                summary="Metadata marker branch",
                expected_outcomes=(
                    ExpectedSemanticOutcome(
                        outcome_id="metadata-marker-added",
                        category=SemanticDeltaCategory.snapshot_metadata,
                        item_id="delta_phase_marker",
                        expected_change=ExpectedSemanticChange.appeared,
                        expected_after_state={"value": "after"},
                    ),
                ),
            ),
        ),
    )

    result = GoalOrientedSemanticVerifier().verify(expectation, transition)

    assert result.status is VerificationStatus.satisfied
    assert result.selected_branch_id == "metadata-marker-appeared"
    assert result.matched_outcome_ids == ("metadata-marker-added",)
    assert tuple(branch.branch_id for branch in result.outcome_branch_results) == (
        "candidate-score-increased",
        "metadata-marker-appeared",
    )
    assert result.outcome_branch_results[0].status is VerificationStatus.unsatisfied
    assert result.outcome_branch_results[1].status is VerificationStatus.satisfied


def test_time_aware_verification_handles_incomplete_timing_input_safely() -> None:
    before = _scored_snapshot()
    expectation = SemanticTransitionExpectation(
        summary="Incomplete polling timing should stay conservative.",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id="metadata-marker-added",
                category=SemanticDeltaCategory.snapshot_metadata,
                item_id="delta_phase_marker",
                expected_change=ExpectedSemanticChange.appeared,
                expected_after_state={"value": "after"},
            ),
        ),
        timing=VerificationTimingPolicy(
            timeout_seconds=1.0,
            poll_interval_ms=100,
            max_poll_attempts=2,
        ),
    )

    result = GoalOrientedSemanticVerifier().verify(
        expectation,
        SemanticStateTransition(
            before=before,
            after=before,
            poll_attempts=(
                VerificationPollAttempt(
                    attempt_index=2,
                    before=before,
                    after=before,
                    elapsed_seconds=None,
                ),
            ),
        ),
    )

    assert result.status is VerificationStatus.unknown
    assert result.success is False
    assert result.evidence["timing_input_incomplete"] is True
    assert any(
        "timing metadata was incomplete" in reason
        for reason in result.reasons
    )
