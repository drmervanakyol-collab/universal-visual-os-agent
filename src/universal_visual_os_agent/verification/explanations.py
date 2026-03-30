"""Observe-only explanation and taxonomy enrichment for verification results."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace

from universal_visual_os_agent.semantics.semantic_delta import SemanticDeltaCategory
from .models import (
    CandidateScoreDeltaDirection,
    ExpectedSemanticOutcome,
    SemanticOutcomeVerification,
    SemanticStateTransition,
    SemanticTransitionExpectation,
    VerificationExplanation,
    VerificationExplanationSeverity,
    VerificationReasonCategory,
    VerificationResult,
    VerificationStatus,
    VerificationTaxonomy,
)

_CATEGORY_PRIORITY = {
    VerificationReasonCategory.missing_input: 0,
    VerificationReasonCategory.unexpected_change_detected: 1,
    VerificationReasonCategory.score_change_not_satisfied: 2,
    VerificationReasonCategory.metadata_expectation_not_met: 3,
    VerificationReasonCategory.expected_change_not_found: 4,
    VerificationReasonCategory.expected_change_observed: 5,
    VerificationReasonCategory.partial_input: 6,
    VerificationReasonCategory.ambiguous_result: 7,
}


class ObserveOnlyVerificationExplainer:
    """Add structured explanations and failure taxonomy to verification results."""

    explainer_name = "ObserveOnlyVerificationExplainer"

    def explain(
        self,
        result: VerificationResult,
        *,
        expectation: SemanticTransitionExpectation,
        transition: SemanticStateTransition,
    ) -> VerificationResult:
        outcome_expectations_by_id = {
            outcome.outcome_id: outcome
            for outcome in expectation.expected_outcomes
        }

        enriched_outcomes = tuple(
            self._enrich_outcome_verification(
                verification,
                outcome_expectation=outcome_expectations_by_id.get(verification.outcome_id),
                result=result,
                transition=transition,
            )
            for verification in result.outcome_verifications
        )
        explanations = self._build_result_explanations(
            result,
            transition=transition,
            enriched_outcomes=enriched_outcomes,
        )
        taxonomy = _build_taxonomy(result.status, explanations)

        return replace(
            result,
            outcome_verifications=enriched_outcomes,
            explanations=explanations,
            taxonomy=taxonomy,
            evidence={
                **dict(result.evidence),
                "verification_explainer_name": self.explainer_name,
                "verification_taxonomy_primary_category": (
                    None if taxonomy.primary_category is None else taxonomy.primary_category.value
                ),
                "verification_taxonomy_categories": tuple(
                    category.value for category in taxonomy.categories
                ),
                "verification_explanation_count": len(explanations),
            },
        )

    def _enrich_outcome_verification(
        self,
        verification: SemanticOutcomeVerification,
        *,
        outcome_expectation: ExpectedSemanticOutcome | None,
        result: VerificationResult,
        transition: SemanticStateTransition,
    ) -> SemanticOutcomeVerification:
        explanation = _build_outcome_explanation(
            verification,
            outcome_expectation=outcome_expectation,
            result=result,
            transition=transition,
        )
        return replace(
            verification,
            explanations=(explanation,),
            primary_reason_category=explanation.category,
            reason_categories=(explanation.category,),
            metadata={
                **dict(verification.metadata),
                "verification_explainer_name": self.explainer_name,
                "verification_primary_reason_category": explanation.category.value,
                "verification_reason_categories": (explanation.category.value,),
            },
        )

    def _build_result_explanations(
        self,
        result: VerificationResult,
        *,
        transition: SemanticStateTransition,
        enriched_outcomes: tuple[SemanticOutcomeVerification, ...],
    ) -> tuple[VerificationExplanation, ...]:
        explanations: list[VerificationExplanation] = []

        if transition.after is None:
            explanations.append(
                _result_explanation(
                    category=VerificationReasonCategory.missing_input,
                    severity=VerificationExplanationSeverity.warning,
                    summary="The after snapshot was unavailable, so verification stayed observe-only and incomplete.",
                )
            )
        elif transition.before is None and result.outcome_verifications:
            explanations.append(
                _result_explanation(
                    category=VerificationReasonCategory.missing_input,
                    severity=VerificationExplanationSeverity.warning,
                    summary="The before snapshot was unavailable for delta-based outcome verification.",
                )
            )
        elif result.semantic_delta is None and result.outcome_verifications:
            explanations.append(
                _result_explanation(
                    category=VerificationReasonCategory.ambiguous_result,
                    severity=VerificationExplanationSeverity.warning,
                    summary="The semantic delta was unavailable, so outcome verification could not be fully explained.",
                )
            )

        needs_result_level_partial_input = (
            result.semantic_delta is not None
            and result.semantic_delta.signal_status == "partial"
            and (
                not enriched_outcomes
                or result.status is VerificationStatus.unknown
                or any(
                    verification.primary_reason_category
                    in {
                        VerificationReasonCategory.missing_input,
                        VerificationReasonCategory.partial_input,
                        VerificationReasonCategory.ambiguous_result,
                    }
                    for verification in enriched_outcomes
                )
            )
        )
        if needs_result_level_partial_input:
            explanations.append(
                _result_explanation(
                    category=VerificationReasonCategory.partial_input,
                    severity=VerificationExplanationSeverity.warning,
                    summary="Verification used partial semantic input, so some conclusions remained conservative.",
                )
            )

        if result.missing_candidate_ids:
            explanations.append(
                _result_explanation(
                    category=VerificationReasonCategory.expected_change_not_found,
                    severity=VerificationExplanationSeverity.error,
                    summary=(
                        "Required candidate identifiers were missing from the after snapshot: "
                        f"{result.missing_candidate_ids}."
                    ),
                    metadata={"candidate_ids": result.missing_candidate_ids},
                )
            )
        if result.missing_node_ids:
            explanations.append(
                _result_explanation(
                    category=VerificationReasonCategory.expected_change_not_found,
                    severity=VerificationExplanationSeverity.error,
                    summary=(
                        "Required node identifiers were missing from the after semantic layout tree: "
                        f"{result.missing_node_ids}."
                    ),
                    metadata={"node_ids": result.missing_node_ids},
                )
            )
        if result.unexpected_candidate_ids:
            explanations.append(
                _result_explanation(
                    category=VerificationReasonCategory.unexpected_change_detected,
                    severity=VerificationExplanationSeverity.error,
                    summary=(
                        "Unexpected candidate identifiers were present in the after snapshot: "
                        f"{result.unexpected_candidate_ids}."
                    ),
                    metadata={"candidate_ids": result.unexpected_candidate_ids},
                )
            )

        if result.status is VerificationStatus.satisfied and not explanations:
            explanations.append(
                _result_explanation(
                    category=VerificationReasonCategory.expected_change_observed,
                    severity=VerificationExplanationSeverity.info,
                    summary="All requested verification checks were satisfied.",
                )
            )
        elif result.status is VerificationStatus.unknown and not explanations:
            explanations.append(
                _result_explanation(
                    category=VerificationReasonCategory.ambiguous_result,
                    severity=VerificationExplanationSeverity.warning,
                    summary="Verification remained inconclusive without a stronger classified cause.",
                )
            )

        for outcome_verification in enriched_outcomes:
            explanations.extend(outcome_verification.explanations)
        return tuple(explanations)


def build_explained_verification_result(
    result: VerificationResult,
    *,
    expectation: SemanticTransitionExpectation,
    transition: SemanticStateTransition,
) -> VerificationResult:
    """Return an explained verification result using the default observe-only explainer."""

    return ObserveOnlyVerificationExplainer().explain(
        result,
        expectation=expectation,
        transition=transition,
    )


def _build_outcome_explanation(
    verification: SemanticOutcomeVerification,
    *,
    outcome_expectation: ExpectedSemanticOutcome | None,
    result: VerificationResult,
    transition: SemanticStateTransition,
) -> VerificationExplanation:
    if verification.status is VerificationStatus.satisfied:
        return VerificationExplanation(
            category=VerificationReasonCategory.expected_change_observed,
            severity=VerificationExplanationSeverity.info,
            summary=verification.summary,
            related_outcome_id=verification.outcome_id,
            related_item_id=verification.item_id,
            related_semantic_category=verification.category,
            metadata={
                "matched_change_type": verification.matched_change_type,
            },
        )

    if transition.after is None or (transition.before is None and result.outcome_verifications):
        return VerificationExplanation(
            category=VerificationReasonCategory.missing_input,
            severity=VerificationExplanationSeverity.warning,
            summary=(
                f"Outcome '{verification.outcome_id}' could not be verified because a required input snapshot was unavailable."
            ),
            related_outcome_id=verification.outcome_id,
            related_item_id=verification.item_id,
            related_semantic_category=verification.category,
        )

    if _is_partial_outcome(verification, result):
        return VerificationExplanation(
            category=VerificationReasonCategory.partial_input,
            severity=VerificationExplanationSeverity.warning,
            summary=(
                f"Outcome '{verification.outcome_id}' remained conservative because the relevant semantic input was partial."
            ),
            related_outcome_id=verification.outcome_id,
            related_item_id=verification.item_id,
            related_semantic_category=verification.category,
        )

    if verification.status is VerificationStatus.unknown:
        return VerificationExplanation(
            category=VerificationReasonCategory.ambiguous_result,
            severity=VerificationExplanationSeverity.warning,
            summary=(
                f"Outcome '{verification.outcome_id}' remained inconclusive after observe-only verification."
            ),
            related_outcome_id=verification.outcome_id,
            related_item_id=verification.item_id,
            related_semantic_category=verification.category,
        )

    if _is_score_expectation(outcome_expectation):
        return VerificationExplanation(
            category=VerificationReasonCategory.score_change_not_satisfied,
            severity=VerificationExplanationSeverity.error,
            summary=(
                f"Outcome '{verification.outcome_id}' did not satisfy the expected candidate score change."
            ),
            related_outcome_id=verification.outcome_id,
            related_item_id=verification.item_id,
            related_semantic_category=verification.category,
            metadata={"score_delta": verification.metadata.get("score_delta")},
        )

    if (
        verification.category is SemanticDeltaCategory.snapshot_metadata
        and outcome_expectation is not None
        and (outcome_expectation.expected_before_state or outcome_expectation.expected_after_state)
    ):
        return VerificationExplanation(
            category=VerificationReasonCategory.metadata_expectation_not_met,
            severity=VerificationExplanationSeverity.error,
            summary=(
                f"Outcome '{verification.outcome_id}' did not satisfy the expected metadata change."
            ),
            related_outcome_id=verification.outcome_id,
            related_item_id=verification.item_id,
            related_semantic_category=verification.category,
        )

    expected_change_type = (
        None if outcome_expectation is None else _expected_change_type_name(outcome_expectation)
    )
    if verification.matched_change_type is not None and expected_change_type is not None:
        if verification.matched_change_type != expected_change_type:
            return VerificationExplanation(
                category=VerificationReasonCategory.unexpected_change_detected,
                severity=VerificationExplanationSeverity.error,
                summary=(
                    f"Outcome '{verification.outcome_id}' observed an unexpected semantic change type."
                ),
                related_outcome_id=verification.outcome_id,
                related_item_id=verification.item_id,
                related_semantic_category=verification.category,
                metadata={
                    "matched_change_type": verification.matched_change_type,
                    "expected_change_type": expected_change_type,
                },
            )

    return VerificationExplanation(
        category=VerificationReasonCategory.expected_change_not_found,
        severity=VerificationExplanationSeverity.error,
        summary=(
            f"Outcome '{verification.outcome_id}' did not observe the expected semantic change."
        ),
        related_outcome_id=verification.outcome_id,
        related_item_id=verification.item_id,
        related_semantic_category=verification.category,
        metadata={"matched_change_type": verification.matched_change_type},
    )


def _result_explanation(
    *,
    category: VerificationReasonCategory,
    severity: VerificationExplanationSeverity,
    summary: str,
    metadata: dict[str, object] | None = None,
) -> VerificationExplanation:
    return VerificationExplanation(
        category=category,
        severity=severity,
        summary=summary,
        metadata={} if metadata is None else metadata,
    )


def _build_taxonomy(
    status: VerificationStatus,
    explanations: tuple[VerificationExplanation, ...],
) -> VerificationTaxonomy:
    category_counts = Counter(explanation.category.value for explanation in explanations)
    severity_counts = Counter(explanation.severity.value for explanation in explanations)
    ordered_categories = tuple(
        sorted(
            {explanation.category for explanation in explanations},
            key=_category_sort_key,
        )
    )
    primary_category = None if not ordered_categories else ordered_categories[0]
    return VerificationTaxonomy(
        summary=_taxonomy_summary(status, primary_category=primary_category, explanation_count=len(explanations)),
        primary_category=primary_category,
        categories=ordered_categories,
        category_counts=dict(sorted(category_counts.items())),
        info_count=severity_counts.get(VerificationExplanationSeverity.info.value, 0),
        warning_count=severity_counts.get(VerificationExplanationSeverity.warning.value, 0),
        error_count=severity_counts.get(VerificationExplanationSeverity.error.value, 0),
    )


def _taxonomy_summary(
    status: VerificationStatus,
    *,
    primary_category: VerificationReasonCategory | None,
    explanation_count: int,
) -> str:
    if primary_category is None:
        return "Verification taxonomy has no explanation categories."
    return (
        f"Verification {status.value} with primary category '{primary_category.value}' "
        f"across {explanation_count} structured explanations."
    )


def _category_sort_key(category: VerificationReasonCategory) -> tuple[int, str]:
    return (_CATEGORY_PRIORITY[category], category.value)


def _expected_change_type_name(outcome_expectation: ExpectedSemanticOutcome) -> str:
    return {
        "appeared": "added",
        "disappeared": "removed",
        "changed": "changed",
    }[outcome_expectation.expected_change.value]


def _is_score_expectation(outcome_expectation: ExpectedSemanticOutcome | None) -> bool:
    if outcome_expectation is None:
        return False
    return (
        outcome_expectation.minimum_score_delta is not None
        or outcome_expectation.score_delta_direction is not CandidateScoreDeltaDirection.any_change
    )


def _is_partial_outcome(
    verification: SemanticOutcomeVerification,
    result: VerificationResult,
) -> bool:
    if result.semantic_delta is None:
        return False
    if result.semantic_delta.signal_status != "partial":
        return False
    if verification.category is SemanticDeltaCategory.layout_tree_node:
        return bool(
            result.semantic_delta.metadata.get("missing_before_layout_tree")
            or result.semantic_delta.metadata.get("missing_after_layout_tree")
        )
    metadata_key = {
        SemanticDeltaCategory.layout_region: "incomplete_layout_region_ids",
        SemanticDeltaCategory.text_region: "incomplete_text_region_ids",
        SemanticDeltaCategory.text_block: "incomplete_text_block_ids",
        SemanticDeltaCategory.candidate: "incomplete_candidate_ids",
    }.get(verification.category)
    if metadata_key is None:
        return False
    incomplete_ids = result.semantic_delta.metadata.get(metadata_key)
    return isinstance(incomplete_ids, tuple) and verification.item_id in incomplete_ids
