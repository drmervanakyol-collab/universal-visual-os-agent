"""Verification models for semantic-state transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from universal_visual_os_agent.semantics.state import SemanticStateSnapshot


class VerificationStatus(StrEnum):
    """The outcome of a semantic-state verification pass."""

    satisfied = "satisfied"
    unsatisfied = "unsatisfied"
    unknown = "unknown"


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticTransitionExpectation:
    """Expected semantic changes between snapshots."""

    summary: str
    required_candidate_ids: tuple[str, ...] = ()
    forbidden_candidate_ids: tuple[str, ...] = ()
    required_node_ids: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticStateTransition:
    """Before/after semantic state used for verification."""

    before: SemanticStateSnapshot | None
    after: SemanticStateSnapshot


@dataclass(slots=True, frozen=True, kw_only=True)
class VerificationResult:
    """Verification status for an expected semantic state transition."""

    status: VerificationStatus
    summary: str
    matched_candidate_ids: tuple[str, ...] = ()
    missing_candidate_ids: tuple[str, ...] = ()
    unexpected_candidate_ids: tuple[str, ...] = ()
    missing_node_ids: tuple[str, ...] = ()
    evidence: dict[str, object] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Preserve the Phase 1 success-style API."""

        return self.status is VerificationStatus.satisfied


def evaluate_semantic_transition(
    expectation: SemanticTransitionExpectation,
    transition: SemanticStateTransition,
) -> VerificationResult:
    """Evaluate a semantic transition against a pure expectation contract."""

    after_candidate_ids = {candidate.candidate_id for candidate in transition.after.candidates}
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

    after_node_ids = set()
    if transition.after.layout_tree is not None:
        after_node_ids = {node.node_id for node in transition.after.layout_tree.walk()}
    missing_node_ids = tuple(
        node_id for node_id in expectation.required_node_ids if node_id not in after_node_ids
    )

    status = VerificationStatus.satisfied
    if missing_candidate_ids or unexpected_candidate_ids or missing_node_ids:
        status = VerificationStatus.unsatisfied

    return VerificationResult(
        status=status,
        summary=expectation.summary,
        matched_candidate_ids=matched_candidate_ids,
        missing_candidate_ids=missing_candidate_ids,
        unexpected_candidate_ids=unexpected_candidate_ids,
        missing_node_ids=missing_node_ids,
        evidence={
            "after_candidate_count": len(transition.after.candidates),
            "after_node_count": len(after_node_ids),
        },
    )
