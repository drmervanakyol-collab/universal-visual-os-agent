"""Goal-oriented verification built on semantic delta comparison."""

from __future__ import annotations

from collections import Counter
from typing import Mapping

from universal_visual_os_agent.semantics import ObserveOnlySemanticDeltaComparator
from universal_visual_os_agent.semantics.interfaces import SemanticDeltaComparator
from universal_visual_os_agent.semantics.semantic_delta import (
    SemanticDelta,
    SemanticDeltaCategory,
    SemanticDeltaChange,
    SemanticDeltaChangeType,
)
from universal_visual_os_agent.verification.models import (
    CandidateScoreDeltaDirection,
    ExpectedSemanticChange,
    ExpectedSemanticOutcome,
    SemanticOutcomeVerification,
    SemanticStateTransition,
    SemanticTransitionExpectation,
    VerificationResult,
    VerificationStatus,
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


class GoalOrientedSemanticVerifier:
    """Evaluate expected semantic outcomes from an observe-only state transition."""

    verifier_name = "GoalOrientedSemanticVerifier"

    def __init__(
        self,
        *,
        delta_comparator: SemanticDeltaComparator | None = None,
    ) -> None:
        self._delta_comparator = (
            ObserveOnlySemanticDeltaComparator() if delta_comparator is None else delta_comparator
        )

    def verify(
        self,
        expectation: SemanticTransitionExpectation,
        transition: SemanticStateTransition,
    ) -> VerificationResult:
        if transition.after is None:
            return VerificationResult(
                status=VerificationStatus.unknown,
                summary=expectation.summary,
                reasons=("After snapshot is unavailable, so verification could not be completed.",),
                evidence={
                    "verifier_name": self.verifier_name,
                    "after_snapshot_available": False,
                    "delta_available": False,
                },
            )

        try:
            delta: SemanticDelta | None = None
            delta_reasons: list[str] = []
            delta_error_code: str | None = None
            if transition.before is None:
                if expectation.expected_outcomes:
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
            outcome_verifications = self._evaluate_expected_outcomes(
                expectation.expected_outcomes,
                transition=transition,
                delta=delta,
                delta_reasons=tuple(delta_reasons),
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
                    *(
                        reason
                        for verification in outcome_verifications
                        for reason in verification.reasons
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
                evidence=evidence,
            )
        except Exception as exc:  # noqa: BLE001 - verification must stay failure-safe
            return VerificationResult(
                status=VerificationStatus.unknown,
                summary=expectation.summary,
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
) -> VerificationStatus:
    if missing_candidate_ids or unexpected_candidate_ids or missing_node_ids:
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


def _dedupe_preserving_order(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))
