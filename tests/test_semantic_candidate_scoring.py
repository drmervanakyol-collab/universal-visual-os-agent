from __future__ import annotations

from dataclasses import replace

from test_semantic_candidate_generation import _generated_candidates, _semantic_layout_snapshot

from universal_visual_os_agent.semantics import (
    ObserveOnlyCandidateGenerator,
    ObserveOnlyCandidateScorer,
    SemanticCandidate,
    SemanticStateSnapshot,
)


class _ExplodingCandidateScorer(ObserveOnlyCandidateScorer):
    def _score_generated_candidates(self, snapshot, *, generated_candidates):
        raise RuntimeError("candidate scorer exploded")


def _generated_snapshot() -> SemanticStateSnapshot:
    snapshot = _semantic_layout_snapshot()
    result = ObserveOnlyCandidateGenerator().generate(snapshot)
    assert result.success is True
    assert result.snapshot is not None
    return result.snapshot


def _scored_generated_candidates(snapshot: SemanticStateSnapshot) -> tuple[SemanticCandidate, ...]:
    return tuple(
        candidate
        for candidate in snapshot.candidates
        if candidate.metadata.get("semantic_origin") == "candidate_generation"
    )


def test_candidate_scoring_scores_generated_candidates_non_actionably() -> None:
    snapshot = _generated_snapshot()

    result = ObserveOnlyCandidateScorer().score(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    scored_snapshot = result.snapshot
    scored_candidates = _scored_generated_candidates(scored_snapshot)
    assert scored_snapshot.metadata["candidate_scoring"] is True
    assert scored_snapshot.metadata["scored_candidate_ids"]
    assert all(candidate.confidence is not None for candidate in scored_candidates)
    assert all(candidate.score_explanations for candidate in scored_candidates)
    assert all(candidate.score_factors for candidate in scored_candidates)
    assert all(candidate.enabled is False for candidate in scored_candidates)
    assert all(candidate.actionable is False for candidate in scored_candidates)
    assert any(
        candidate.metadata["candidate_score"] != candidate.metadata["candidate_generation_confidence"]
        for candidate in scored_candidates
    )


def test_candidate_scoring_metadata_is_consistent() -> None:
    snapshot = _generated_snapshot()

    result = ObserveOnlyCandidateScorer().score(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    scored_snapshot = result.snapshot
    layout_region_ids = {region.region_id for region in scored_snapshot.layout_regions}
    text_region_ids = {region.region_id for region in scored_snapshot.text_regions}
    text_block_ids = {block.text_block_id for block in scored_snapshot.text_blocks}
    for candidate in _scored_generated_candidates(scored_snapshot):
        assert candidate.confidence == candidate.metadata["candidate_score"]
        assert candidate.score_explanations == candidate.metadata["candidate_score_explanations"]
        assert candidate.score_factors == candidate.metadata["candidate_score_factors"]
        assert candidate.metadata["candidate_scored"] is True
        assert candidate.metadata["candidate_score_contributing_factors"]
        assert isinstance(candidate.metadata["candidate_generation_confidence"], float)
        source_layout_region_id = candidate.metadata["source_layout_region_id"]
        assert source_layout_region_id in layout_region_ids
        source_text_region_id = candidate.metadata["source_text_region_id"]
        if source_text_region_id is not None:
            assert source_text_region_id in text_region_ids
        source_text_block_id = candidate.metadata["source_text_block_id"]
        if source_text_block_id is not None:
            assert source_text_block_id in text_block_ids


def test_candidate_scoring_handles_incomplete_metadata_safely() -> None:
    snapshot = _generated_snapshot()
    candidate_with_text_sources = next(
        candidate
        for candidate in _generated_candidates(snapshot)
        if candidate.metadata["source_text_region_id"] is not None
        and candidate.metadata["source_text_block_id"] is not None
    )
    source_layout_region_id = candidate_with_text_sources.metadata["source_layout_region_id"]
    source_text_region_id = candidate_with_text_sources.metadata["source_text_region_id"]
    source_text_block_id = candidate_with_text_sources.metadata["source_text_block_id"]
    partial_snapshot = replace(
        snapshot,
        layout_regions=tuple(
            region
            for region in snapshot.layout_regions
            if region.region_id != source_layout_region_id
        ),
        text_regions=tuple(
            region
            for region in snapshot.text_regions
            if region.region_id != source_text_region_id
        ),
        text_blocks=tuple(
            block
            for block in snapshot.text_blocks
            if block.text_block_id != source_text_block_id
        ),
        metadata={
            key: value
            for key, value in snapshot.metadata.items()
            if key != "generated_candidate_ids"
        },
    )

    result = ObserveOnlyCandidateScorer().score(partial_snapshot)

    assert result.success is True
    assert result.snapshot is not None
    scored_snapshot = result.snapshot
    assert scored_snapshot.metadata["candidate_scoring_signal_status"] == "partial"
    assert scored_snapshot.metadata["candidate_scoring_generation_metadata_incomplete"] is True
    assert source_layout_region_id in scored_snapshot.metadata["candidate_scoring_missing_layout_region_ids"]
    assert source_text_region_id in scored_snapshot.metadata["candidate_scoring_missing_text_region_ids"]
    assert source_text_block_id in scored_snapshot.metadata["candidate_scoring_missing_text_block_ids"]
    assert all(candidate.actionable is False for candidate in _scored_generated_candidates(scored_snapshot))


def test_candidate_scoring_requires_candidate_generation_output() -> None:
    snapshot = _generated_snapshot()
    incomplete_snapshot = replace(
        snapshot,
        metadata={
            key: value
            for key, value in snapshot.metadata.items()
            if key != "candidate_generation"
        },
    )

    result = ObserveOnlyCandidateScorer().score(incomplete_snapshot)

    assert result.success is False
    assert result.error_code == "candidate_generation_unavailable"


def test_candidate_scoring_preserves_observe_only_semantics() -> None:
    snapshot = _generated_snapshot()

    result = ObserveOnlyCandidateScorer().score(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    for candidate in _scored_generated_candidates(result.snapshot):
        assert candidate.metadata["observe_only"] is True
        assert candidate.metadata["analysis_only"] is True
        assert candidate.metadata["non_actionable_candidate"] is True
        assert candidate.enabled is False
        assert candidate.actionable is False


def test_candidate_scoring_does_not_propagate_unhandled_exceptions() -> None:
    snapshot = _generated_snapshot()

    result = _ExplodingCandidateScorer().score(snapshot)

    assert result.success is False
    assert result.error_code == "candidate_scoring_exception"
    assert result.error_message == "candidate scorer exploded"
