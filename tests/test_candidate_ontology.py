from __future__ import annotations

from dataclasses import replace

from test_semantic_candidate_generation import _semantic_layout_snapshot

from universal_visual_os_agent.semantics import (
    CandidateSelectionRiskLevel,
    ObserveOnlyCandidateExposer,
    ObserveOnlyCandidateGenerator,
    ObserveOnlyCandidateScorer,
    ObserveOnlySemanticDeltaComparator,
    SemanticCandidate,
    SemanticCandidateSourceType,
    SemanticStateSnapshot,
)
from universal_visual_os_agent.semantics.ontology import (
    CandidateProvenanceRecord,
    CandidateResolverReadinessStatus,
    evaluate_candidate_resolver_readiness,
    normalize_provenance,
)


def _generated_snapshot() -> SemanticStateSnapshot:
    generation_result = ObserveOnlyCandidateGenerator().generate(_semantic_layout_snapshot())
    assert generation_result.success is True
    assert generation_result.snapshot is not None
    return generation_result.snapshot


def _scored_snapshot() -> SemanticStateSnapshot:
    scoring_result = ObserveOnlyCandidateScorer().score(_generated_snapshot())
    assert scoring_result.success is True
    assert scoring_result.snapshot is not None
    return scoring_result.snapshot


def _generated_candidates(snapshot: SemanticStateSnapshot) -> tuple[SemanticCandidate, ...]:
    return tuple(
        candidate
        for candidate in snapshot.candidates
        if candidate.metadata.get("semantic_origin") == "candidate_generation"
    )


def test_generated_candidates_expose_deterministic_source_ontology() -> None:
    snapshot = _generated_snapshot()

    assert snapshot.metadata["generated_candidate_source_type_counts"]
    assert snapshot.metadata["generated_candidate_risk_level_counts"]
    assert snapshot.metadata["generated_candidate_resolver_readiness_status_counts"]
    for candidate in _generated_candidates(snapshot):
        assert candidate.source_type is not None
        assert candidate.selection_risk_level is not None
        assert candidate.source_of_truth_priority
        assert candidate.provenance
        assert candidate.metadata["candidate_source_type"] == candidate.source_type.value
        assert (
            candidate.metadata["candidate_selection_risk_level"]
            == candidate.selection_risk_level.value
        )
        assert candidate.metadata["candidate_disambiguation_needed"] is candidate.disambiguation_needed
        assert (
            candidate.metadata["candidate_requires_local_resolver"]
            is candidate.requires_local_resolver
        )
        assert (
            candidate.metadata["candidate_source_conflict_present"]
            is candidate.source_conflict_present
        )
        assert candidate.metadata["candidate_source_of_truth_priority"] == tuple(
            source_type.value for source_type in candidate.source_of_truth_priority
        )
        assert candidate.metadata["candidate_provenance"] == tuple(
            {
                "source_type": record.source_type.value,
                "source_id": record.source_id,
                "source_label": record.source_label,
                "confidence": record.confidence,
                "metadata": dict(record.metadata),
            }
            for record in candidate.provenance
        )
        readiness = evaluate_candidate_resolver_readiness(candidate)
        assert candidate.metadata["candidate_resolver_readiness_status"] == readiness.status.value
        assert candidate.metadata["candidate_resolver_readiness_reason_codes"] == tuple(
            reason.value for reason in readiness.reason_codes
        )
        assert candidate.metadata["candidate_ontology_completeness_status"] == "available"
        assert candidate.metadata["candidate_resolver_handoff_completeness_status"] == "available"
        assert candidate.metadata["candidate_provenance_source_types"] == tuple(
            source_type.value for source_type in dict.fromkeys(
                record.source_type for record in candidate.provenance
            )
        )
        if candidate.metadata["source_text_block_id"] is None:
            assert candidate.source_type is SemanticCandidateSourceType.layout
            assert candidate.selection_risk_level is CandidateSelectionRiskLevel.high
        else:
            assert candidate.source_type is SemanticCandidateSourceType.mixed


def test_candidate_exposure_preserves_source_and_risk_metadata() -> None:
    snapshot = _scored_snapshot()

    result = ObserveOnlyCandidateExposer().expose(snapshot)

    assert result.success is True
    assert result.exposure_view is not None
    exposure_view = result.exposure_view
    source_candidates_by_id = {
        candidate.candidate_id: candidate for candidate in _generated_candidates(snapshot)
    }
    assert exposure_view.metadata["source_type_counts"]
    assert exposure_view.metadata["selection_risk_level_counts"]
    for exposed_candidate in exposure_view.candidates:
        source_candidate = source_candidates_by_id[exposed_candidate.candidate_id]
        assert exposed_candidate.source_type is source_candidate.source_type
        assert exposed_candidate.selection_risk_level is source_candidate.selection_risk_level
        assert (
            exposed_candidate.disambiguation_needed
            is source_candidate.disambiguation_needed
        )
        assert (
            exposed_candidate.requires_local_resolver
            is source_candidate.requires_local_resolver
        )
        assert (
            exposed_candidate.source_conflict_present
            is source_candidate.source_conflict_present
        )
        assert exposed_candidate.source_of_truth_priority == source_candidate.source_of_truth_priority
        assert exposed_candidate.provenance == source_candidate.provenance
        assert exposed_candidate.metadata["candidate_source_type"] == source_candidate.source_type.value
        assert (
            exposed_candidate.metadata["candidate_selection_risk_level"]
            == source_candidate.selection_risk_level.value
        )
        assert exposed_candidate.completeness_status == "available"
        readiness = evaluate_candidate_resolver_readiness(
            exposed_candidate,
            handoff_completeness_status=exposed_candidate.completeness_status,
        )
        assert exposed_candidate.metadata["candidate_resolver_readiness_status"] == (
            readiness.status.value
        )
        assert exposed_candidate.metadata["candidate_resolver_readiness_reason_codes"] == tuple(
            reason.value for reason in readiness.reason_codes
        )
        assert exposed_candidate.metadata["candidate_provenance_source_types"] == tuple(
            source_type.value for source_type in dict.fromkeys(
                record.source_type for record in exposed_candidate.provenance
            )
        )
    assert exposure_view.metadata["resolver_readiness_status_counts"]


def test_candidate_exposure_handles_incomplete_source_metadata_safely() -> None:
    snapshot = _scored_snapshot()
    broken_candidate = next(
        candidate
        for candidate in _generated_candidates(snapshot)
        if candidate.metadata["source_text_block_id"] is not None
    )
    incomplete_candidate = replace(
        broken_candidate,
        source_type=None,
        selection_risk_level=None,
        source_of_truth_priority=(),
        provenance=(),
        metadata={
            key: value
            for key, value in broken_candidate.metadata.items()
            if key
            not in {
                "candidate_source_type",
                "candidate_selection_risk_level",
                "candidate_source_of_truth_priority",
                "candidate_provenance",
            }
        },
    )
    incomplete_snapshot = replace(
        snapshot,
        candidates=tuple(
            incomplete_candidate
            if candidate.candidate_id == broken_candidate.candidate_id
            else candidate
            for candidate in snapshot.candidates
        ),
    )

    result = ObserveOnlyCandidateExposer().expose(incomplete_snapshot)

    assert result.success is True
    assert result.exposure_view is not None
    exposure_view = result.exposure_view
    exposed_candidate = next(
        candidate
        for candidate in exposure_view.candidates
        if candidate.candidate_id == broken_candidate.candidate_id
    )
    assert exposure_view.signal_status == "partial"
    assert broken_candidate.candidate_id in exposure_view.metadata["missing_source_type_candidate_ids"]
    assert broken_candidate.candidate_id in exposure_view.metadata["missing_selection_risk_candidate_ids"]
    assert broken_candidate.candidate_id in exposure_view.metadata["missing_source_priority_candidate_ids"]
    assert broken_candidate.candidate_id in exposure_view.metadata["missing_provenance_candidate_ids"]
    assert broken_candidate.candidate_id in exposure_view.metadata["resolver_partial_candidate_ids"]
    assert exposed_candidate.completeness_status == "partial"
    assert exposed_candidate.metadata["candidate_resolver_readiness_status"] == "partial"
    assert "missing_source_type" in exposed_candidate.metadata["candidate_resolver_readiness_reason_codes"]
    assert "missing_provenance" in exposed_candidate.metadata["candidate_resolver_readiness_reason_codes"]
    assert exposed_candidate.actionable is False


def test_candidate_resolver_readiness_distinguishes_conflicted_and_partial_states() -> None:
    snapshot = _generated_snapshot()
    conflicted_candidate = next(
        candidate for candidate in _generated_candidates(snapshot) if candidate.source_conflict_present
    )

    conflicted_readiness = evaluate_candidate_resolver_readiness(conflicted_candidate)
    partial_readiness = evaluate_candidate_resolver_readiness(
        replace(
            conflicted_candidate,
            source_type=None,
            source_of_truth_priority=(),
            provenance=(),
        )
    )

    assert conflicted_readiness.status is CandidateResolverReadinessStatus.conflicted
    assert "source_conflict_present" in tuple(
        reason.value for reason in conflicted_readiness.reason_codes
    )
    assert partial_readiness.status is CandidateResolverReadinessStatus.partial
    assert "missing_source_type" in tuple(
        reason.value for reason in partial_readiness.reason_codes
    )


def test_semantic_delta_freezes_candidate_provenance_as_structured_mappings() -> None:
    before = _scored_snapshot()
    target_candidate = next(candidate for candidate in _generated_candidates(before) if candidate.provenance)
    after_candidate = replace(
        target_candidate,
        provenance=normalize_provenance(
            target_candidate.provenance
            + (
                CandidateProvenanceRecord(
                    source_type=SemanticCandidateSourceType.heuristic,
                    source_id=f"{target_candidate.candidate_id}:manual_provenance",
                    source_label="manual_provenance",
                    metadata={"note": "delta test"},
                ),
            )
        ),
    )
    after = replace(
        before,
        candidates=tuple(
            after_candidate
            if candidate.candidate_id == target_candidate.candidate_id
            else candidate
            for candidate in before.candidates
        ),
    )

    result = ObserveOnlySemanticDeltaComparator().compare(before, after)

    assert result.success is True
    assert result.delta is not None
    change = next(
        candidate_change
        for candidate_change in result.delta.candidate_changes
        if candidate_change.item_id == target_candidate.candidate_id
    )
    assert "provenance" in change.changed_fields
    assert isinstance(change.before_state["provenance"], tuple)
    assert isinstance(change.before_state["provenance"][0], dict)
    assert {
        record["source_id"] for record in change.after_state["provenance"]
    } >= {
        f"{target_candidate.candidate_id}:manual_provenance"
    }
    assert {
        record["source_type"] for record in change.after_state["provenance"]
    } >= {
        SemanticCandidateSourceType.heuristic.value
    }
