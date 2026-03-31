"""Goal-oriented verification built on semantic delta comparison."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from typing import Mapping

from universal_visual_os_agent.semantics.interfaces import SemanticDeltaComparator
from universal_visual_os_agent.semantics.semantic_delta import (
    ObserveOnlySemanticDeltaComparator,
    SemanticDelta,
    SemanticDeltaCategory,
    SemanticDeltaChange,
    SemanticDeltaChangeType,
)
from .explanations import ObserveOnlyVerificationExplainer
from .interfaces import VerificationExplainer
from .models import (
    CandidateScoreDeltaDirection,
    ExpectedSemanticChange,
    ExpectedSemanticOutcome,
    SemanticOutcomeVerification,
    SemanticStateTransition,
    SemanticTransitionExpectation,
    VerificationOutcomeBranch,
    VerificationOutcomeBranchResult,
    VerificationExplanation,
    VerificationExplanationSeverity,
    VerificationPollAttempt,
    VerificationReasonCategory,
    VerificationResult,
    VerificationStatus,
    VerificationTimingPolicy,
    VerificationTaxonomy,
)

_EXPECTED_CHANGE_TO_DELTA_CHANGE = {
    ExpectedSemanticChange.appeared: SemanticDeltaChangeType.added,
    ExpectedSemanticChange.disappeared: SemanticDeltaChangeType.removed,
    ExpectedSemanticChange.changed: SemanticDeltaChangeType.changed,
}
_INCOMPLETE_ITEM_KEYS = {
    SemanticDeltaCategory.layout_region: "incomplete_layout_region_ids",
    SemanticDeltaCategory.text_region: "incomplete_text_region_ids",
    SemanticDeltaCategory.text_block: "incomplete_text_block_ids",
    SemanticDeltaCategory.candidate: "incomplete_candidate_ids",
}
_PRIMARY_OUTCOME_BRANCH_ID = "primary_expected_outcomes"


@dataclass(slots=True, frozen=True, kw_only=True)
class _VerificationAttemptContext:
    attempt_index: int
    elapsed_seconds: float | None
    transition: SemanticStateTransition


class GoalOrientedSemanticVerifier:
    """Evaluate expected semantic outcomes from an observe-only state transition."""

    verifier_name = "GoalOrientedSemanticVerifier"

    def __init__(
        self,
        *,
        delta_comparator: SemanticDeltaComparator | None = None,
        explainer: VerificationExplainer | None = None,
    ) -> None:
        self._delta_comparator = (
            ObserveOnlySemanticDeltaComparator() if delta_comparator is None else delta_comparator
        )
        self._explainer = ObserveOnlyVerificationExplainer() if explainer is None else explainer

    def verify(
        self,
        expectation: SemanticTransitionExpectation,
        transition: SemanticStateTransition,
    ) -> VerificationResult:
        try:
            attempt_contexts = _build_attempt_contexts(expectation, transition)
            attempt_results: list[tuple[_VerificationAttemptContext, VerificationResult]] = []
            for attempt_context in attempt_contexts:
                attempt_result = self._verify_attempt(expectation, attempt_context.transition)
                attempt_results.append((attempt_context, attempt_result))
                if attempt_result.status is VerificationStatus.satisfied:
                    return self._finalize_result(
                        _finalize_attempt_selection(
                            attempt_result,
                            attempt_context=attempt_context,
                            expectation=expectation,
                            transition=transition,
                            attempt_results=attempt_results,
                        ),
                        expectation=expectation,
                        transition=transition,
                    )

            selected_attempt_context, selected_result = _select_final_attempt_result(
                expectation,
                transition=transition,
                attempt_results=tuple(attempt_results),
            )
            return self._finalize_result(
                _finalize_attempt_selection(
                    selected_result,
                    attempt_context=selected_attempt_context,
                    expectation=expectation,
                    transition=transition,
                    attempt_results=attempt_results,
                ),
                expectation=expectation,
                transition=transition,
            )
        except Exception as exc:  # noqa: BLE001 - verification must stay failure-safe
            return self._finalize_result(
                VerificationResult(
                    status=VerificationStatus.unknown,
                    summary=expectation.summary,
                    timing=expectation.timing,
                    reasons=(
                        "Verification encountered an internal exception and remained observe-only.",
                    ),
                    evidence={
                        "verifier_name": self.verifier_name,
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                        "delta_available": False,
                        "observe_only": True,
                        "read_only": True,
                        "non_actionable": True,
                    },
                ),
                expectation=expectation,
                transition=transition,
            )

    def _verify_attempt(
        self,
        expectation: SemanticTransitionExpectation,
        transition: SemanticStateTransition,
    ) -> VerificationResult:
        if transition.after is None:
            return VerificationResult(
                status=VerificationStatus.unknown,
                summary=expectation.summary,
                timing=expectation.timing,
                reasons=("After snapshot is unavailable, so verification could not be completed.",),
                evidence={
                    "verifier_name": self.verifier_name,
                    "after_snapshot_available": False,
                    "delta_available": False,
                    "observe_only": True,
                    "read_only": True,
                    "non_actionable": True,
                },
            )

        delta: SemanticDelta | None = None
        delta_reasons: list[str] = []
        delta_error_code: str | None = None
        if transition.before is None:
            if _has_delta_dependent_outcomes(expectation):
                delta_reasons.append(
                    "Before snapshot is unavailable, so delta-based outcome verification is incomplete."
                )
        else:
            delta_result = self._delta_comparator.compare(transition.before, transition.after)
            if delta_result.success:
                delta = delta_result.delta
            else:
                delta_error_code = delta_result.error_code
                delta_reasons.append(
                    "Semantic delta comparison was unavailable, so delta-based outcome verification is incomplete."
                )

        (
            matched_candidate_ids,
            missing_candidate_ids,
            unexpected_candidate_ids,
        ) = _evaluate_candidate_presence(expectation, transition)
        missing_node_ids, node_reasons = _evaluate_node_presence(expectation, transition)
        branch_results = self._evaluate_outcome_branches(
            expectation,
            transition=transition,
            delta=delta,
            delta_reasons=tuple(delta_reasons),
        )
        selected_branch = _select_branch_result(branch_results)
        outcome_verifications = (
            ()
            if selected_branch is None
            else selected_branch.outcome_verifications
        )
        matched_outcome_ids = (
            ()
            if selected_branch is None
            else selected_branch.matched_outcome_ids
        )
        unsatisfied_outcome_ids = (
            ()
            if selected_branch is None
            else selected_branch.unsatisfied_outcome_ids
        )
        unknown_outcome_ids = (
            ()
            if selected_branch is None
            else selected_branch.unknown_outcome_ids
        )
        reasons = _dedupe_preserving_order(
            (
                *delta_reasons,
                *node_reasons,
                *(
                    f"Required candidate '{candidate_id}' was not present in the after snapshot."
                    for candidate_id in missing_candidate_ids
                ),
                *(
                    f"Forbidden candidate '{candidate_id}' was present in the after snapshot."
                    for candidate_id in unexpected_candidate_ids
                ),
                *(
                    f"Required node '{node_id}' was not present in the after layout tree."
                    for node_id in missing_node_ids
                ),
                *(() if selected_branch is None else _branch_reasons(selected_branch)),
                *(
                    (
                        f"Verification satisfied via acceptable branch '{selected_branch.branch_id}'.",
                    )
                    if selected_branch is not None
                    and selected_branch.branch_id != _PRIMARY_OUTCOME_BRANCH_ID
                    and selected_branch.status is VerificationStatus.satisfied
                    else ()
                ),
            )
        )
        status = _aggregate_status(
            missing_candidate_ids=missing_candidate_ids,
            unexpected_candidate_ids=unexpected_candidate_ids,
            missing_node_ids=missing_node_ids,
            outcome_verifications=outcome_verifications,
            delta_reasons=tuple(delta_reasons),
            node_reasons=node_reasons,
            outcome_branch_results=branch_results,
        )
        evidence = {
            "verifier_name": self.verifier_name,
            "after_snapshot_available": True,
            "after_candidate_count": len(transition.after.candidates),
            "after_node_count": (
                0 if transition.after.layout_tree is None else len(transition.after.layout_tree.walk())
            ),
            "delta_available": delta is not None,
            "delta_error_code": delta_error_code,
            "delta_signal_status": None if delta is None else delta.signal_status,
            "delta_change_count": None if delta is None else delta.summary.total_change_count,
            "matched_outcome_ids": matched_outcome_ids,
            "unsatisfied_outcome_ids": unsatisfied_outcome_ids,
            "unknown_outcome_ids": unknown_outcome_ids,
            "selected_branch_id": None if selected_branch is None else selected_branch.branch_id,
            "outcome_branch_statuses": tuple(
                (branch.branch_id, branch.status.value)
                for branch in branch_results
            ),
            "outcome_status_counts": dict(
                sorted(
                    Counter(
                        verification.status.value for verification in outcome_verifications
                    ).items()
                )
            ),
            "observe_only": True,
            "read_only": True,
            "non_actionable": True,
        }
        return VerificationResult(
            status=status,
            summary=expectation.summary,
            matched_candidate_ids=matched_candidate_ids,
            missing_candidate_ids=missing_candidate_ids,
            unexpected_candidate_ids=unexpected_candidate_ids,
            missing_node_ids=missing_node_ids,
            outcome_verifications=outcome_verifications,
            matched_outcome_ids=matched_outcome_ids,
            unsatisfied_outcome_ids=unsatisfied_outcome_ids,
            unknown_outcome_ids=unknown_outcome_ids,
            reasons=reasons,
            semantic_delta=delta,
            timing=expectation.timing,
            selected_branch_id=None if selected_branch is None else selected_branch.branch_id,
            outcome_branch_results=branch_results,
            evidence=evidence,
        )

    def _finalize_result(
        self,
        result: VerificationResult,
        *,
        expectation: SemanticTransitionExpectation,
        transition: SemanticStateTransition,
    ) -> VerificationResult:
        try:
            return self._explainer.explain(
                result,
                expectation=expectation,
                transition=transition,
            )
        except Exception as exc:  # noqa: BLE001 - explanation layer must remain failure-safe
            fallback_explanation = VerificationExplanation(
                category=VerificationReasonCategory.ambiguous_result,
                severity=VerificationExplanationSeverity.warning,
                summary="Verification explanation enrichment failed; the raw observe-only verification result was preserved.",
                metadata={
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )
            fallback_taxonomy = VerificationTaxonomy(
                summary=(
                    "Verification taxonomy fell back to an ambiguous-result classification after explanation enrichment failed."
                ),
                primary_category=VerificationReasonCategory.ambiguous_result,
                categories=(VerificationReasonCategory.ambiguous_result,),
                category_counts={VerificationReasonCategory.ambiguous_result.value: 1},
                warning_count=1,
            )
            return replace(
                result,
                explanations=(fallback_explanation,),
                taxonomy=fallback_taxonomy,
                evidence={
                    **dict(result.evidence),
                    "verification_explainer_name": getattr(
                        self._explainer,
                        "explainer_name",
                        type(self._explainer).__name__,
                    ),
                    "verification_explainer_exception_type": type(exc).__name__,
                    "verification_explainer_exception_message": str(exc),
                },
            )

    def _evaluate_expected_outcomes(
        self,
        expected_outcomes: tuple[ExpectedSemanticOutcome, ...],
        *,
        transition: SemanticStateTransition,
        delta: SemanticDelta | None,
        delta_reasons: tuple[str, ...],
    ) -> tuple[SemanticOutcomeVerification, ...]:
        if not expected_outcomes:
            return ()
        delta_lookup = {} if delta is None else _delta_lookup(delta)
        return tuple(
            _evaluate_expected_outcome(
                outcome,
                transition=transition,
                delta=delta,
                delta_lookup=delta_lookup,
                delta_reasons=delta_reasons,
            )
            for outcome in expected_outcomes
        )

    def _evaluate_outcome_branches(
        self,
        expectation: SemanticTransitionExpectation,
        *,
        transition: SemanticStateTransition,
        delta: SemanticDelta | None,
        delta_reasons: tuple[str, ...],
    ) -> tuple[VerificationOutcomeBranchResult, ...]:
        branch_definitions = _branch_definitions(expectation)
        if not branch_definitions:
            return ()
        results: list[VerificationOutcomeBranchResult] = []
        for branch in branch_definitions:
            outcome_verifications = self._evaluate_expected_outcomes(
                branch.expected_outcomes,
                transition=transition,
                delta=delta,
                delta_reasons=delta_reasons,
            )
            matched_outcome_ids = tuple(
                verification.outcome_id
                for verification in outcome_verifications
                if verification.status is VerificationStatus.satisfied
            )
            unsatisfied_outcome_ids = tuple(
                verification.outcome_id
                for verification in outcome_verifications
                if verification.status is VerificationStatus.unsatisfied
            )
            unknown_outcome_ids = tuple(
                verification.outcome_id
                for verification in outcome_verifications
                if verification.status is VerificationStatus.unknown
            )
            results.append(
                VerificationOutcomeBranchResult(
                    branch_id=branch.branch_id,
                    summary=branch.summary,
                    status=_aggregate_branch_status(
                        outcome_verifications,
                        delta_reasons=delta_reasons,
                    ),
                    outcome_verifications=outcome_verifications,
                    matched_outcome_ids=matched_outcome_ids,
                    unsatisfied_outcome_ids=unsatisfied_outcome_ids,
                    unknown_outcome_ids=unknown_outcome_ids,
                    metadata={
                        "observe_only": True,
                        "read_only": True,
                        "non_actionable": True,
                    },
                )
            )
        return tuple(results)


def _evaluate_candidate_presence(
    expectation: SemanticTransitionExpectation,
    transition: SemanticStateTransition,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    after = transition.after
    if after is None:
        return (), expectation.required_candidate_ids, ()
    after_candidate_ids = {candidate.candidate_id for candidate in after.candidates}
    matched_candidate_ids = tuple(
        candidate_id
        for candidate_id in expectation.required_candidate_ids
        if candidate_id in after_candidate_ids
    )
    missing_candidate_ids = tuple(
        candidate_id
        for candidate_id in expectation.required_candidate_ids
        if candidate_id not in after_candidate_ids
    )
    unexpected_candidate_ids = tuple(
        candidate_id
        for candidate_id in expectation.forbidden_candidate_ids
        if candidate_id in after_candidate_ids
    )
    return matched_candidate_ids, missing_candidate_ids, unexpected_candidate_ids


def _evaluate_node_presence(
    expectation: SemanticTransitionExpectation,
    transition: SemanticStateTransition,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    after = transition.after
    if after is None:
        return expectation.required_node_ids, (
            "After snapshot is unavailable, so required nodes were treated as missing.",
        )
    if not expectation.required_node_ids:
        return (), ()
    if after.layout_tree is None:
        return expectation.required_node_ids, (
            "After layout tree is unavailable, so required nodes were treated as missing.",
        )
    after_node_ids = {node.node_id for node in after.layout_tree.walk()}
    missing_node_ids = tuple(
        node_id
        for node_id in expectation.required_node_ids
        if node_id not in after_node_ids
    )
    return missing_node_ids, ()


def _evaluate_expected_outcome(
    outcome: ExpectedSemanticOutcome,
    *,
    transition: SemanticStateTransition,
    delta: SemanticDelta | None,
    delta_lookup: Mapping[tuple[SemanticDeltaCategory, str], SemanticDeltaChange],
    delta_reasons: tuple[str, ...],
) -> SemanticOutcomeVerification:
    summary = outcome.summary or _default_outcome_summary(outcome)
    if transition.before is None:
        return SemanticOutcomeVerification(
            outcome_id=outcome.outcome_id,
            status=VerificationStatus.unknown,
            category=outcome.category,
            item_id=outcome.item_id,
            expected_change=outcome.expected_change,
            summary=summary,
            reasons=("Before snapshot is unavailable for delta-based outcome verification.",),
            metadata={"observe_only": True, "read_only": True, "non_actionable": True},
        )
    if delta is None:
        return SemanticOutcomeVerification(
            outcome_id=outcome.outcome_id,
            status=VerificationStatus.unknown,
            category=outcome.category,
            item_id=outcome.item_id,
            expected_change=outcome.expected_change,
            summary=summary,
            reasons=delta_reasons or ("Semantic delta is unavailable for this outcome.",),
            metadata={"observe_only": True, "read_only": True, "non_actionable": True},
        )

    change = delta_lookup.get((outcome.category, outcome.item_id))
    item_incomplete = _item_is_incomplete(outcome, delta)
    if change is None:
        if item_incomplete:
            return SemanticOutcomeVerification(
                outcome_id=outcome.outcome_id,
                status=VerificationStatus.unknown,
                category=outcome.category,
                item_id=outcome.item_id,
                expected_change=outcome.expected_change,
                summary=summary,
                reasons=("The semantic input for this outcome was incomplete, so no safe conclusion was made.",),
                metadata={
                    "delta_signal_status": delta.signal_status,
                    "observe_only": True,
                    "read_only": True,
                    "non_actionable": True,
                },
            )
        return SemanticOutcomeVerification(
            outcome_id=outcome.outcome_id,
            status=VerificationStatus.unsatisfied,
            category=outcome.category,
            item_id=outcome.item_id,
            expected_change=outcome.expected_change,
            summary=summary,
            reasons=(f"Expected semantic change '{outcome.expected_change.value}' was not observed.",),
            metadata={
                "delta_signal_status": delta.signal_status,
                "observe_only": True,
                "read_only": True,
                "non_actionable": True,
            },
        )

    reasons: list[str] = []
    status = VerificationStatus.satisfied
    expected_delta_change = _EXPECTED_CHANGE_TO_DELTA_CHANGE[outcome.expected_change]
    if change.change_type is not expected_delta_change:
        reasons.append(
            f"Observed change type was '{change.change_type.value}' instead of the expected '{expected_delta_change.value}'."
        )
        status = VerificationStatus.unsatisfied

    missing_fields = tuple(
        field_name
        for field_name in outcome.required_changed_fields
        if field_name not in change.changed_fields
    )
    if missing_fields:
        status = _status_for_mismatch(item_incomplete=item_incomplete, current_status=status)
        reasons.append(f"Required changed fields were not observed: {missing_fields}.")

    before_state_match = _state_subset_matches(outcome.expected_before_state, change.before_state)
    if not before_state_match:
        status = _status_for_state_mismatch(
            expected_state=outcome.expected_before_state,
            actual_state=change.before_state,
            item_incomplete=item_incomplete,
            current_status=status,
        )
        reasons.append("Expected before-state values were not observed.")

    after_state_match = _state_subset_matches(outcome.expected_after_state, change.after_state)
    if not after_state_match:
        status = _status_for_state_mismatch(
            expected_state=outcome.expected_after_state,
            actual_state=change.after_state,
            item_incomplete=item_incomplete,
            current_status=status,
        )
        reasons.append("Expected after-state values were not observed.")

    score_delta = _score_delta_for_change(change)
    if outcome.minimum_score_delta is not None:
        if score_delta is None:
            status = _status_for_mismatch(item_incomplete=item_incomplete, current_status=status)
            reasons.append("Candidate score delta could not be computed safely.")
        elif abs(score_delta) < outcome.minimum_score_delta:
            status = VerificationStatus.unsatisfied
            reasons.append(
                f"Candidate score delta {score_delta:.4f} was smaller than the expected minimum {outcome.minimum_score_delta:.4f}."
            )
    if outcome.score_delta_direction is CandidateScoreDeltaDirection.increased:
        if score_delta is None:
            status = _status_for_mismatch(item_incomplete=item_incomplete, current_status=status)
            reasons.append("Candidate score delta direction could not be computed safely.")
        elif score_delta <= 0.0:
            status = VerificationStatus.unsatisfied
            reasons.append("Candidate score did not increase as expected.")
    elif outcome.score_delta_direction is CandidateScoreDeltaDirection.decreased:
        if score_delta is None:
            status = _status_for_mismatch(item_incomplete=item_incomplete, current_status=status)
            reasons.append("Candidate score delta direction could not be computed safely.")
        elif score_delta >= 0.0:
            status = VerificationStatus.unsatisfied
            reasons.append("Candidate score did not decrease as expected.")

    if status is VerificationStatus.satisfied:
        reasons.append("Expected semantic outcome was observed.")

    return SemanticOutcomeVerification(
        outcome_id=outcome.outcome_id,
        status=status,
        category=outcome.category,
        item_id=outcome.item_id,
        expected_change=outcome.expected_change,
        summary=summary,
        reasons=tuple(reasons),
        matched_change_type=change.change_type.value,
        matched_changed_fields=change.changed_fields,
        metadata={
            "delta_signal_status": delta.signal_status,
            "score_delta": score_delta,
            "observe_only": True,
            "read_only": True,
            "non_actionable": True,
        },
    )


def _aggregate_status(
    *,
    missing_candidate_ids: tuple[str, ...],
    unexpected_candidate_ids: tuple[str, ...],
    missing_node_ids: tuple[str, ...],
    outcome_verifications: tuple[SemanticOutcomeVerification, ...],
    delta_reasons: tuple[str, ...],
    node_reasons: tuple[str, ...],
    outcome_branch_results: tuple[VerificationOutcomeBranchResult, ...] = (),
) -> VerificationStatus:
    if missing_candidate_ids or unexpected_candidate_ids or missing_node_ids:
        return VerificationStatus.unsatisfied
    if any(
        branch.status is VerificationStatus.satisfied
        for branch in outcome_branch_results
    ):
        return VerificationStatus.satisfied
    if outcome_branch_results:
        if delta_reasons or node_reasons:
            return VerificationStatus.unknown
        if any(
            branch.status is VerificationStatus.unknown
            for branch in outcome_branch_results
        ):
            return VerificationStatus.unknown
        return VerificationStatus.unsatisfied
    if any(
        verification.status is VerificationStatus.unsatisfied
        for verification in outcome_verifications
    ):
        return VerificationStatus.unsatisfied
    if delta_reasons or node_reasons:
        return VerificationStatus.unknown
    if any(
        verification.status is VerificationStatus.unknown
        for verification in outcome_verifications
    ):
        return VerificationStatus.unknown
    return VerificationStatus.satisfied


def _default_outcome_summary(outcome: ExpectedSemanticOutcome) -> str:
    return (
        f"Verify that {outcome.category.value.replace('_', ' ')} '{outcome.item_id}' "
        f"{outcome.expected_change.value}."
    )


def _branch_definitions(
    expectation: SemanticTransitionExpectation,
) -> tuple[VerificationOutcomeBranch, ...]:
    primary_branch = (
        VerificationOutcomeBranch(
            branch_id=_PRIMARY_OUTCOME_BRANCH_ID,
            summary=expectation.summary,
            expected_outcomes=expectation.expected_outcomes,
        ),
    ) if expectation.expected_outcomes else ()
    return primary_branch + expectation.alternate_outcome_branches


def _aggregate_branch_status(
    outcome_verifications: tuple[SemanticOutcomeVerification, ...],
    *,
    delta_reasons: tuple[str, ...],
) -> VerificationStatus:
    if any(
        verification.status is VerificationStatus.unsatisfied
        for verification in outcome_verifications
    ):
        return VerificationStatus.unsatisfied
    if delta_reasons:
        return VerificationStatus.unknown
    if any(
        verification.status is VerificationStatus.unknown
        for verification in outcome_verifications
    ):
        return VerificationStatus.unknown
    return VerificationStatus.satisfied


def _select_branch_result(
    branch_results: tuple[VerificationOutcomeBranchResult, ...],
) -> VerificationOutcomeBranchResult | None:
    for branch in branch_results:
        if branch.status is VerificationStatus.satisfied:
            return branch
    for branch in branch_results:
        if branch.status is VerificationStatus.unknown:
            return branch
    return None if not branch_results else branch_results[0]


def _branch_reasons(
    branch_result: VerificationOutcomeBranchResult,
) -> tuple[str, ...]:
    return tuple(
        reason
        for verification in branch_result.outcome_verifications
        for reason in verification.reasons
    )


def _has_delta_dependent_outcomes(expectation: SemanticTransitionExpectation) -> bool:
    if expectation.expected_outcomes:
        return True
    return any(branch.expected_outcomes for branch in expectation.alternate_outcome_branches)


def _delta_lookup(delta: SemanticDelta) -> Mapping[tuple[SemanticDeltaCategory, str], SemanticDeltaChange]:
    return {
        (change.category, change.item_id): change
        for change in delta.all_changes
    }


def _item_is_incomplete(
    outcome: ExpectedSemanticOutcome,
    delta: SemanticDelta,
) -> bool:
    if outcome.category is SemanticDeltaCategory.layout_tree_node:
        return bool(
            delta.metadata.get("missing_before_layout_tree") or delta.metadata.get("missing_after_layout_tree")
        )
    metadata_key = _INCOMPLETE_ITEM_KEYS.get(outcome.category)
    if metadata_key is None:
        return False
    incomplete_ids = delta.metadata.get(metadata_key)
    return isinstance(incomplete_ids, tuple) and outcome.item_id in incomplete_ids


def _state_subset_matches(
    expected_state: Mapping[str, object],
    actual_state: Mapping[str, object],
) -> bool:
    for key, expected_value in expected_state.items():
        if key not in actual_state:
            return False
        actual_value = actual_state[key]
        if isinstance(expected_value, Mapping):
            if not isinstance(actual_value, Mapping):
                return False
            if not _state_subset_matches(expected_value, actual_value):
                return False
            continue
        if actual_value != expected_value:
            return False
    return True


def _state_has_missing_expected_values(
    expected_state: Mapping[str, object],
    actual_state: Mapping[str, object],
) -> bool:
    for key, expected_value in expected_state.items():
        if key not in actual_state:
            return True
        actual_value = actual_state[key]
        if isinstance(expected_value, Mapping):
            if not isinstance(actual_value, Mapping):
                return True
            if _state_has_missing_expected_values(expected_value, actual_value):
                return True
            continue
        if actual_value is None and expected_value is not None:
            return True
    return False


def _status_for_state_mismatch(
    *,
    expected_state: Mapping[str, object],
    actual_state: Mapping[str, object],
    item_incomplete: bool,
    current_status: VerificationStatus,
) -> VerificationStatus:
    if current_status is VerificationStatus.unsatisfied:
        return current_status
    if item_incomplete and _state_has_missing_expected_values(expected_state, actual_state):
        return VerificationStatus.unknown
    return VerificationStatus.unsatisfied


def _status_for_mismatch(
    *,
    item_incomplete: bool,
    current_status: VerificationStatus,
) -> VerificationStatus:
    if current_status is VerificationStatus.unsatisfied:
        return current_status
    if item_incomplete:
        return VerificationStatus.unknown
    return VerificationStatus.unsatisfied


def _score_delta_for_change(change: SemanticDeltaChange) -> float | None:
    metadata_value = change.metadata.get("score_delta")
    if isinstance(metadata_value, float):
        return metadata_value
    before_confidence = change.before_state.get("confidence")
    after_confidence = change.after_state.get("confidence")
    if isinstance(before_confidence, float) and isinstance(after_confidence, float):
        return round(after_confidence - before_confidence, 4)
    return None


def _build_attempt_contexts(
    expectation: SemanticTransitionExpectation,
    transition: SemanticStateTransition,
) -> tuple[_VerificationAttemptContext, ...]:
    timing = expectation.timing
    attempts = [
        _VerificationAttemptContext(
            attempt_index=1,
            elapsed_seconds=0.0,
            transition=SemanticStateTransition(
                before=transition.before,
                after=transition.after,
            ),
        )
    ]
    attempts.extend(
        _VerificationAttemptContext(
            attempt_index=attempt.attempt_index,
            elapsed_seconds=attempt.elapsed_seconds,
            transition=SemanticStateTransition(
                before=attempt.before,
                after=attempt.after,
            ),
        )
        for attempt in sorted(transition.poll_attempts, key=lambda item: item.attempt_index)
    )
    if timing is not None and timing.timeout_seconds is not None:
        attempts = [
            attempt
            for attempt in attempts
            if attempt.elapsed_seconds is None or attempt.elapsed_seconds <= timing.timeout_seconds
        ]
    if timing is not None and timing.max_poll_attempts is not None:
        attempts = attempts[: timing.max_poll_attempts]
    return tuple(attempts)


def _select_final_attempt_result(
    expectation: SemanticTransitionExpectation,
    *,
    transition: SemanticStateTransition,
    attempt_results: tuple[tuple[_VerificationAttemptContext, VerificationResult], ...],
) -> tuple[_VerificationAttemptContext, VerificationResult]:
    if not attempt_results:
        fallback_result = VerificationResult(
            status=VerificationStatus.unknown,
            summary=expectation.summary,
            timing=expectation.timing,
            reasons=("No verification attempts were available within the configured polling window.",),
            evidence={
                "verifier_name": GoalOrientedSemanticVerifier.verifier_name,
                "after_snapshot_available": False,
                "delta_available": False,
                "observe_only": True,
                "read_only": True,
                "non_actionable": True,
            },
        )
        return (
            _VerificationAttemptContext(
                attempt_index=1,
                elapsed_seconds=0.0,
                transition=SemanticStateTransition(before=transition.before, after=transition.after),
            ),
            fallback_result,
        )

    timing_input_incomplete = _timing_input_incomplete(expectation.timing, transition.poll_attempts)
    for attempt_context, result in reversed(attempt_results):
        if result.status is VerificationStatus.unknown:
            return attempt_context, _with_timing_incomplete_guard(result, timing_input_incomplete)
    last_attempt_context, last_result = attempt_results[-1]
    return last_attempt_context, _with_timing_incomplete_guard(last_result, timing_input_incomplete)


def _with_timing_incomplete_guard(
    result: VerificationResult,
    timing_input_incomplete: bool,
) -> VerificationResult:
    if not timing_input_incomplete or result.status is not VerificationStatus.unsatisfied:
        return result
    return replace(
        result,
        status=VerificationStatus.unknown,
        reasons=_dedupe_preserving_order(
            result.reasons
            + (
                "Polling timing metadata was incomplete, so the final verification result stayed conservative.",
            )
        ),
        evidence={
            **dict(result.evidence),
            "timing_input_incomplete": True,
        },
    )


def _finalize_attempt_selection(
    result: VerificationResult,
    *,
    attempt_context: _VerificationAttemptContext,
    expectation: SemanticTransitionExpectation,
    transition: SemanticStateTransition,
    attempt_results: list[tuple[_VerificationAttemptContext, VerificationResult]],
) -> VerificationResult:
    timing = expectation.timing
    considered_attempt_count = len(attempt_results)
    provided_attempt_count = 1 + len(transition.poll_attempts)
    polling_used = provided_attempt_count > 1
    polling_exhausted = (
        polling_used
        and result.status is not VerificationStatus.satisfied
        and considered_attempt_count == min(
            provided_attempt_count,
            timing.max_poll_attempts if timing is not None and timing.max_poll_attempts is not None else provided_attempt_count,
        )
    )
    return replace(
        result,
        timing=timing,
        poll_attempt_count=considered_attempt_count,
        selected_poll_attempt=attempt_context.attempt_index,
        selected_elapsed_seconds=attempt_context.elapsed_seconds,
        evidence={
            **dict(result.evidence),
            "verification_timeout_seconds": None if timing is None else timing.timeout_seconds,
            "verification_poll_interval_ms": None if timing is None else timing.poll_interval_ms,
            "verification_max_poll_attempts": None if timing is None else timing.max_poll_attempts,
            "verification_poll_attempt_count": considered_attempt_count,
            "verification_selected_poll_attempt": attempt_context.attempt_index,
            "verification_selected_elapsed_seconds": attempt_context.elapsed_seconds,
            "verification_polling_used": polling_used,
            "verification_polling_exhausted": polling_exhausted,
            "verification_total_provided_attempt_count": provided_attempt_count,
            "timing_input_incomplete": _timing_input_incomplete(
                timing,
                transition.poll_attempts,
            ),
        },
    )


def _timing_input_incomplete(
    timing: VerificationTimingPolicy | None,
    poll_attempts: tuple[VerificationPollAttempt, ...],
) -> bool:
    return (
        timing is not None
        and any(attempt.elapsed_seconds is None for attempt in poll_attempts)
    )


def _dedupe_preserving_order(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))
