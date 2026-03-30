from __future__ import annotations

from dataclasses import replace

from test_goal_oriented_verification import _successful_transition
from test_semantic_delta import _scored_snapshot

from universal_visual_os_agent.semantics import SemanticDeltaCategory, SemanticTextStatus
from universal_visual_os_agent.verification import (
    CandidateScoreDeltaDirection,
    ExpectedSemanticChange,
    ExpectedSemanticOutcome,
    GoalOrientedSemanticVerifier,
    SemanticStateTransition,
    SemanticTransitionExpectation,
    VerificationExplanationSeverity,
    VerificationReasonCategory,
    VerificationStatus,
)


class _ExplodingExplainer:
    explainer_name = "ExplodingExplainer"

    def explain(self, result, *, expectation, transition):
        del result, expectation, transition
        raise RuntimeError("verification explainer exploded")


def test_verification_explanations_cover_successful_outcomes() -> None:
    transition, changed_text_region_id, _ = _successful_transition()
    expectation = SemanticTransitionExpectation(
        summary="Successful explanation path",
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
            ),
        ),
    )

    result = GoalOrientedSemanticVerifier().verify(expectation, transition)

    assert result.status is VerificationStatus.satisfied
    assert result.taxonomy is not None
    assert result.taxonomy.primary_category is VerificationReasonCategory.expected_change_observed
    assert result.taxonomy.categories == (VerificationReasonCategory.expected_change_observed,)
    assert result.taxonomy.error_count == 0
    assert result.taxonomy.warning_count == 0
    assert result.explanations[0].category is VerificationReasonCategory.expected_change_observed
    assert result.explanations[0].severity is VerificationExplanationSeverity.info
    assert all(
        verification.primary_reason_category is VerificationReasonCategory.expected_change_observed
        for verification in result.outcome_verifications
    )


def test_verification_explanations_classify_failures_with_stable_taxonomy() -> None:
    transition, _, changed_candidate_id = _successful_transition()
    expectation = SemanticTransitionExpectation(
        summary="Failure taxonomy path",
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
                outcome_id="metadata-mismatch",
                category=SemanticDeltaCategory.snapshot_metadata,
                item_id="delta_phase_marker",
                expected_change=ExpectedSemanticChange.appeared,
                expected_after_state={"value": "wrong"},
            ),
        ),
    )

    result = GoalOrientedSemanticVerifier().verify(expectation, transition)

    assert result.status is VerificationStatus.unsatisfied
    assert result.taxonomy is not None
    assert result.taxonomy.primary_category is VerificationReasonCategory.score_change_not_satisfied
    assert result.taxonomy.categories == (
        VerificationReasonCategory.score_change_not_satisfied,
        VerificationReasonCategory.metadata_expectation_not_met,
    )
    assert result.taxonomy.category_counts == {
        "metadata_expectation_not_met": 1,
        "score_change_not_satisfied": 1,
    }
    assert result.outcome_verifications[0].primary_reason_category is VerificationReasonCategory.score_change_not_satisfied
    assert result.outcome_verifications[1].primary_reason_category is VerificationReasonCategory.metadata_expectation_not_met


def test_verification_explanations_classify_partial_unknown_results() -> None:
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
        summary="Partial-input explanation path",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id="partial-text-change",
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
    assert result.taxonomy is not None
    assert result.taxonomy.primary_category is VerificationReasonCategory.partial_input
    assert result.taxonomy.categories == (VerificationReasonCategory.partial_input,)
    assert result.outcome_verifications[0].primary_reason_category is VerificationReasonCategory.partial_input


def test_verification_explanations_classify_missing_input_results() -> None:
    snapshot = _scored_snapshot()
    expectation = SemanticTransitionExpectation(
        summary="Missing-input explanation path",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id="candidate-change",
                category=SemanticDeltaCategory.candidate,
                item_id="missing-candidate",
                expected_change=ExpectedSemanticChange.changed,
            ),
        ),
    )

    result = GoalOrientedSemanticVerifier().verify(
        expectation,
        SemanticStateTransition(before=None, after=snapshot),
    )

    assert result.status is VerificationStatus.unknown
    assert result.taxonomy is not None
    assert result.taxonomy.primary_category is VerificationReasonCategory.missing_input
    assert result.taxonomy.categories == (VerificationReasonCategory.missing_input,)
    assert result.outcome_verifications[0].primary_reason_category is VerificationReasonCategory.missing_input


def test_verification_explanations_preserve_observe_only_semantics() -> None:
    transition, changed_text_region_id, _ = _successful_transition()
    expectation = SemanticTransitionExpectation(
        summary="Observe-only explanation semantics",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id="text-changed",
                category=SemanticDeltaCategory.text_region,
                item_id=changed_text_region_id,
                expected_change=ExpectedSemanticChange.changed,
            ),
        ),
    )

    result = GoalOrientedSemanticVerifier().verify(expectation, transition)

    assert result.taxonomy is not None
    assert result.observe_only is True
    assert result.read_only is True
    assert result.non_actionable is True
    assert result.taxonomy.observe_only is True
    assert all(explanation.observe_only is True for explanation in result.explanations)
    assert all(verification.observe_only is True for verification in result.outcome_verifications)


def test_verification_explanations_do_not_propagate_unhandled_exceptions() -> None:
    transition, changed_text_region_id, _ = _successful_transition()
    expectation = SemanticTransitionExpectation(
        summary="Explanation failure fallback",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id="text-changed",
                category=SemanticDeltaCategory.text_region,
                item_id=changed_text_region_id,
                expected_change=ExpectedSemanticChange.changed,
            ),
        ),
    )

    result = GoalOrientedSemanticVerifier(
        explainer=_ExplodingExplainer()
    ).verify(expectation, transition)

    assert result.status is VerificationStatus.satisfied
    assert result.taxonomy is not None
    assert result.taxonomy.primary_category is VerificationReasonCategory.ambiguous_result
    assert result.explanations[0].category is VerificationReasonCategory.ambiguous_result
    assert result.evidence["verification_explainer_exception_type"] == "RuntimeError"
    assert result.evidence["verification_explainer_exception_message"] == "verification explainer exploded"
