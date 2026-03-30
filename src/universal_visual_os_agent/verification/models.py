"""Verification models for semantic-state transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping

from universal_visual_os_agent.semantics.semantic_delta import (
    SemanticDelta,
    SemanticDeltaCategory,
)
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot


class VerificationStatus(StrEnum):
    """The outcome of a semantic-state verification pass."""

    satisfied = "satisfied"
    unsatisfied = "unsatisfied"
    unknown = "unknown"


class VerificationExplanationSeverity(StrEnum):
    """Severity of a structured verification explanation."""

    info = "info"
    warning = "warning"
    error = "error"


class VerificationReasonCategory(StrEnum):
    """Stable explanation and failure-taxonomy categories for verification."""

    expected_change_observed = "expected_change_observed"
    missing_input = "missing_input"
    partial_input = "partial_input"
    expected_change_not_found = "expected_change_not_found"
    unexpected_change_detected = "unexpected_change_detected"
    score_change_not_satisfied = "score_change_not_satisfied"
    metadata_expectation_not_met = "metadata_expectation_not_met"
    ambiguous_result = "ambiguous_result"


class ExpectedSemanticChange(StrEnum):
    """High-level expected semantic outcome types."""

    appeared = "appeared"
    disappeared = "disappeared"
    changed = "changed"


class CandidateScoreDeltaDirection(StrEnum):
    """Expected score-delta direction for candidate verification."""

    any_change = "any_change"
    increased = "increased"
    decreased = "decreased"


@dataclass(slots=True, frozen=True, kw_only=True)
class ExpectedSemanticOutcome:
    """A structured semantic outcome to verify from the delta layer."""

    outcome_id: str
    category: SemanticDeltaCategory
    item_id: str
    expected_change: ExpectedSemanticChange
    required_changed_fields: tuple[str, ...] = ()
    expected_before_state: Mapping[str, object] = field(default_factory=dict)
    expected_after_state: Mapping[str, object] = field(default_factory=dict)
    minimum_score_delta: float | None = None
    score_delta_direction: CandidateScoreDeltaDirection = CandidateScoreDeltaDirection.any_change
    summary: str | None = None

    def __post_init__(self) -> None:
        if not self.outcome_id:
            raise ValueError("outcome_id must not be empty.")
        if not self.item_id:
            raise ValueError("item_id must not be empty.")
        if self.minimum_score_delta is not None and self.minimum_score_delta < 0.0:
            raise ValueError("minimum_score_delta must be non-negative when provided.")
        if (
            self.minimum_score_delta is not None
            or self.score_delta_direction is not CandidateScoreDeltaDirection.any_change
        ):
            if self.category is not SemanticDeltaCategory.candidate:
                raise ValueError("Candidate score expectations only apply to candidate outcomes.")
            if self.expected_change is not ExpectedSemanticChange.changed:
                raise ValueError("Candidate score expectations require a changed outcome.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticTransitionExpectation:
    """Expected semantic changes between snapshots."""

    summary: str
    required_candidate_ids: tuple[str, ...] = ()
    forbidden_candidate_ids: tuple[str, ...] = ()
    required_node_ids: tuple[str, ...] = ()
    expected_outcomes: tuple[ExpectedSemanticOutcome, ...] = ()

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        outcome_ids = {outcome.outcome_id for outcome in self.expected_outcomes}
        if len(outcome_ids) != len(self.expected_outcomes):
            raise ValueError("expected outcome identifiers must be unique.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticStateTransition:
    """Before/after semantic state used for verification."""

    before: SemanticStateSnapshot | None
    after: SemanticStateSnapshot | None


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticOutcomeVerification:
    """Verification record for one expected semantic outcome."""

    outcome_id: str
    status: VerificationStatus
    category: SemanticDeltaCategory
    item_id: str
    expected_change: ExpectedSemanticChange
    summary: str
    reasons: tuple[str, ...] = ()
    matched_change_type: str | None = None
    matched_changed_fields: tuple[str, ...] = ()
    explanations: tuple["VerificationExplanation", ...] = ()
    primary_reason_category: VerificationReasonCategory | None = None
    reason_categories: tuple[VerificationReasonCategory, ...] = ()
    observe_only: bool = True
    read_only: bool = True
    non_actionable: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.outcome_id:
            raise ValueError("outcome_id must not be empty.")
        if not self.item_id:
            raise ValueError("item_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_actionable:
            raise ValueError("Outcome verification records must remain observe-only and non-actionable.")


@dataclass(slots=True, frozen=True, kw_only=True)
class VerificationExplanation:
    """A structured, downstream-friendly explanation for verification behavior."""

    category: VerificationReasonCategory
    severity: VerificationExplanationSeverity
    summary: str
    related_outcome_id: str | None = None
    related_item_id: str | None = None
    related_semantic_category: SemanticDeltaCategory | None = None
    observe_only: bool = True
    read_only: bool = True
    non_actionable: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_actionable:
            raise ValueError("Verification explanations must remain observe-only and non-actionable.")


@dataclass(slots=True, frozen=True, kw_only=True)
class VerificationTaxonomy:
    """Structured taxonomy summary for one verification result."""

    summary: str
    primary_category: VerificationReasonCategory | None = None
    categories: tuple[VerificationReasonCategory, ...] = ()
    category_counts: Mapping[str, int] = field(default_factory=dict)
    info_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    observe_only: bool = True
    read_only: bool = True
    non_actionable: bool = True

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.info_count < 0 or self.warning_count < 0 or self.error_count < 0:
            raise ValueError("Taxonomy severity counts must not be negative.")
        if not self.observe_only or not self.read_only or not self.non_actionable:
            raise ValueError("Verification taxonomy must remain observe-only and non-actionable.")


@dataclass(slots=True, frozen=True, kw_only=True)
class VerificationResult:
    """Verification status for an expected semantic state transition."""

    status: VerificationStatus
    summary: str
    matched_candidate_ids: tuple[str, ...] = ()
    missing_candidate_ids: tuple[str, ...] = ()
    unexpected_candidate_ids: tuple[str, ...] = ()
    missing_node_ids: tuple[str, ...] = ()
    outcome_verifications: tuple[SemanticOutcomeVerification, ...] = ()
    matched_outcome_ids: tuple[str, ...] = ()
    unsatisfied_outcome_ids: tuple[str, ...] = ()
    unknown_outcome_ids: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    explanations: tuple[VerificationExplanation, ...] = ()
    taxonomy: VerificationTaxonomy | None = None
    semantic_delta: SemanticDelta | None = None
    observe_only: bool = True
    read_only: bool = True
    non_actionable: bool = True
    evidence: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_actionable:
            raise ValueError("Verification results must remain observe-only and non-actionable.")

    @property
    def success(self) -> bool:
        """Preserve the Phase 1 success-style API."""

        return self.status is VerificationStatus.satisfied


def evaluate_semantic_transition(
    expectation: SemanticTransitionExpectation,
    transition: SemanticStateTransition,
) -> VerificationResult:
    """Evaluate a semantic transition against the goal-oriented verification contract."""

    from universal_visual_os_agent.verification.goal_oriented import (
        GoalOrientedSemanticVerifier,
    )

    return GoalOrientedSemanticVerifier().verify(expectation, transition)
