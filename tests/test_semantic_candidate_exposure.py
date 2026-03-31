from __future__ import annotations

from dataclasses import replace

from test_semantic_candidate_generation import _semantic_layout_snapshot

from universal_visual_os_agent.semantics import (
    CandidateExposureOptions,
    ObserveOnlyCandidateExposer,
    ObserveOnlyCandidateGenerator,
    ObserveOnlyCandidateScorer,
    SemanticCandidate,
    SemanticCandidateClass,
    SemanticStateSnapshot,
)


class _ExplodingCandidateExposer(ObserveOnlyCandidateExposer):
    def _build_exposure_view(self, snapshot, *, scored_generated_candidates, options):
        raise RuntimeError("candidate exposer exploded")


def _generated_candidates(snapshot: SemanticStateSnapshot) -> tuple[SemanticCandidate, ...]:
    return tuple(
        candidate
        for candidate in snapshot.candidates
        if candidate.metadata.get("semantic_origin") == "candidate_generation"
    )


def _scored_snapshot() -> SemanticStateSnapshot:
    semantic_snapshot = _semantic_layout_snapshot()
    generation_result = ObserveOnlyCandidateGenerator().generate(semantic_snapshot)
    assert generation_result.success is True
    assert generation_result.snapshot is not None
    scoring_result = ObserveOnlyCandidateScorer().score(generation_result.snapshot)
    assert scoring_result.success is True
    assert scoring_result.snapshot is not None
    return scoring_result.snapshot


def test_candidate_exposure_builds_filtered_sorted_observe_only_view() -> None:
    snapshot = _scored_snapshot()

    result = ObserveOnlyCandidateExposer().expose(
        snapshot,
        options=CandidateExposureOptions(
            minimum_score=0.95,
            candidate_classes=(
                SemanticCandidateClass.button_like,
                SemanticCandidateClass.tab_like,
            ),
            limit=5,
        ),
    )

    assert result.success is True
    assert result.exposure_view is not None
    exposure_view = result.exposure_view
    scores = tuple(candidate.score for candidate in exposure_view.candidates)
    assert exposure_view.exposed_candidate_count <= 5
    assert all(score is not None and score >= 0.95 for score in scores)
    assert scores == tuple(sorted(scores, reverse=True))
    assert all(
        candidate.candidate_class in {SemanticCandidateClass.button_like, SemanticCandidateClass.tab_like}
        for candidate in exposure_view.candidates
    )
    assert all(candidate.actionable is False for candidate in exposure_view.candidates)
    assert all(candidate.non_actionable is True for candidate in exposure_view.candidates)


def test_candidate_exposure_metadata_is_consistent() -> None:
    snapshot = _scored_snapshot()

    result = ObserveOnlyCandidateExposer().expose(snapshot)

    assert result.success is True
    assert result.exposure_view is not None
    exposure_view = result.exposure_view
    source_candidates_by_id = {
        candidate.candidate_id: candidate
        for candidate in _generated_candidates(snapshot)
    }
    assert exposure_view.metadata["sorted_candidate_ids"] == tuple(
        candidate.candidate_id for candidate in exposure_view.candidates
    )
    assert sum(len(group.candidates) for group in exposure_view.groups) == exposure_view.exposed_candidate_count
    for exposed_candidate in exposure_view.candidates:
        source_candidate = source_candidates_by_id[exposed_candidate.candidate_id]
        assert exposed_candidate.score == source_candidate.confidence
        assert exposed_candidate.candidate_class == source_candidate.candidate_class
        assert exposed_candidate.score_explanations == source_candidate.score_explanations
        assert exposed_candidate.score_factors == source_candidate.score_factors
        assert exposed_candidate.metadata["candidate_exposed"] is True
        assert exposed_candidate.metadata["candidate_rank"] == exposed_candidate.rank
        assert (
            exposed_candidate.metadata["candidate_exposure_completeness_status"]
            == exposed_candidate.completeness_status
        )
        assert exposed_candidate.source_layout_region_id == source_candidate.metadata["source_layout_region_id"]
        assert exposed_candidate.source_text_region_id == source_candidate.metadata["source_text_region_id"]
        assert exposed_candidate.source_text_block_id == source_candidate.metadata["source_text_block_id"]
        assert (
            exposed_candidate.metadata["visual_grounding_support_status"]
            == source_candidate.metadata["visual_grounding_support_status"]
        )
        assert (
            exposed_candidate.metadata["visual_grounding_cue_kinds"]
            == source_candidate.metadata["visual_grounding_cue_kinds"]
        )


def test_candidate_exposure_handles_incomplete_metadata_safely() -> None:
    snapshot = _scored_snapshot()
    broken_candidate = next(
        candidate
        for candidate in _generated_candidates(snapshot)
        if candidate.metadata["source_text_block_id"] is not None
    )
    incomplete_candidate = replace(
        broken_candidate,
        confidence=None,
        score_explanations=(),
        score_factors={},
        metadata={
            key: value
            for key, value in broken_candidate.metadata.items()
            if key
            not in {
                "candidate_scored",
                "source_layout_region_id",
                "candidate_score_explanations",
                "candidate_score_factors",
            }
        },
    )
    incomplete_snapshot = replace(
        snapshot,
        candidates=tuple(
            incomplete_candidate if candidate.candidate_id == broken_candidate.candidate_id else candidate
            for candidate in snapshot.candidates
        ),
        metadata={
            key: value
            for key, value in snapshot.metadata.items()
            if key != "scored_candidate_ids"
        },
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
    assert exposure_view.metadata["scoring_metadata_incomplete"] is True
    assert broken_candidate.candidate_id in exposure_view.metadata["missing_score_candidate_ids"]
    assert broken_candidate.candidate_id in exposure_view.metadata["missing_score_explanation_candidate_ids"]
    assert broken_candidate.candidate_id in exposure_view.metadata["missing_score_factor_candidate_ids"]
    assert broken_candidate.candidate_id in exposure_view.metadata["missing_source_layout_candidate_ids"]
    assert exposed_candidate.completeness_status == "partial"
    assert exposed_candidate.actionable is False


def test_candidate_exposure_requires_candidate_scoring_output() -> None:
    snapshot = _scored_snapshot()
    incomplete_snapshot = replace(
        snapshot,
        metadata={key: value for key, value in snapshot.metadata.items() if key != "candidate_scoring"},
    )

    result = ObserveOnlyCandidateExposer().expose(incomplete_snapshot)

    assert result.success is False
    assert result.error_code == "candidate_scoring_unavailable"


def test_candidate_exposure_preserves_observe_only_semantics() -> None:
    snapshot = _scored_snapshot()

    result = ObserveOnlyCandidateExposer().expose(snapshot)

    assert result.success is True
    assert result.exposure_view is not None
    for candidate in result.exposure_view.candidates:
        assert candidate.observe_only is True
        assert candidate.non_actionable is True
        assert candidate.enabled is False
        assert candidate.actionable is False
        assert candidate.metadata["observe_only"] is True
        assert candidate.metadata["analysis_only"] is True
        assert candidate.metadata["non_actionable_candidate"] is True


def test_candidate_exposure_does_not_propagate_unhandled_exceptions() -> None:
    snapshot = _scored_snapshot()

    result = _ExplodingCandidateExposer().expose(snapshot)

    assert result.success is False
    assert result.error_code == "candidate_exposure_exception"
    assert result.error_message == "candidate exposer exploded"
