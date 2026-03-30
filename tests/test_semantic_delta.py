from __future__ import annotations

from dataclasses import replace

from test_semantic_candidate_generation import _semantic_layout_snapshot

from universal_visual_os_agent.geometry import NormalizedBBox
from universal_visual_os_agent.semantics import (
    ObserveOnlyCandidateGenerator,
    ObserveOnlyCandidateScorer,
    ObserveOnlySemanticDeltaComparator,
    SemanticCandidate,
    SemanticCandidateClass,
    SemanticDeltaCategory,
    SemanticDeltaChangeType,
    SemanticLayoutRegion,
    SemanticLayoutRegionKind,
    SemanticLayoutRole,
    SemanticStateSnapshot,
    SemanticTextStatus,
)


class _ExplodingSemanticDeltaComparator(ObserveOnlySemanticDeltaComparator):
    def _build_delta(self, before, after):
        raise RuntimeError("semantic delta comparator exploded")


def _scored_snapshot() -> SemanticStateSnapshot:
    semantic_snapshot = _semantic_layout_snapshot()
    generation_result = ObserveOnlyCandidateGenerator().generate(semantic_snapshot)
    assert generation_result.success is True
    assert generation_result.snapshot is not None
    scoring_result = ObserveOnlyCandidateScorer().score(generation_result.snapshot)
    assert scoring_result.success is True
    assert scoring_result.snapshot is not None
    return scoring_result.snapshot


def _generated_candidate_ids(snapshot: SemanticStateSnapshot) -> tuple[str, ...]:
    return tuple(
        candidate.candidate_id
        for candidate in snapshot.candidates
        if candidate.metadata.get("semantic_origin") == "candidate_generation"
    )


def _candidate_score_map(snapshot: SemanticStateSnapshot) -> tuple[tuple[str, float | None], ...]:
    return tuple(
        (candidate.candidate_id, candidate.confidence)
        for candidate in snapshot.candidates
        if candidate.metadata.get("semantic_origin") == "candidate_generation"
    )


def _average_candidate_score(snapshot: SemanticStateSnapshot) -> float | None:
    scores = tuple(
        candidate.confidence
        for candidate in snapshot.candidates
        if candidate.metadata.get("semantic_origin") == "candidate_generation"
        and candidate.confidence is not None
    )
    if not scores:
        return None
    return round(sum(scores) / len(scores), 4)


def _after_snapshot(before: SemanticStateSnapshot) -> SemanticStateSnapshot:
    changed_text_region = next(region for region in before.text_regions if region.label == "Top Analysis Band")
    removed_text_block = next(block for block in before.text_blocks if block.label == "Status Footer")
    changed_candidate = next(
        candidate for candidate in before.candidates if candidate.candidate_class is SemanticCandidateClass.button_like
    )
    removed_candidate = next(
        candidate for candidate in before.candidates if candidate.candidate_class is SemanticCandidateClass.close_like
    )

    updated_candidate = replace(
        changed_candidate,
        confidence=0.88,
        score_explanations=(
            *changed_candidate.score_explanations,
            "manual delta test lowered the observe-only score",
        ),
        score_factors={
            **dict(changed_candidate.score_factors),
            "manual_delta_adjustment": -0.05,
        },
        metadata={
            **dict(changed_candidate.metadata),
            "candidate_score": 0.88,
            "candidate_score_explanations": (
                *changed_candidate.score_explanations,
                "manual delta test lowered the observe-only score",
            ),
            "candidate_score_factors": {
                **dict(changed_candidate.score_factors),
                "manual_delta_adjustment": -0.05,
            },
        },
    )
    added_layout_region = SemanticLayoutRegion(
        region_id="layout-region-added",
        kind=SemanticLayoutRegionKind.content,
        label="Support Panel",
        bounds=NormalizedBBox(left=0.66, top=0.2, width=0.18, height=0.22),
        semantic_role=SemanticLayoutRole.primary_content,
        parent_region_id=None,
        visible=True,
        enabled=False,
        confidence=0.81,
        metadata={
            "observe_only": True,
            "analysis_only": True,
            "semantic_layout_signal_status": "available",
        },
    )
    added_candidate = SemanticCandidate(
        candidate_id="candidate-added",
        label="Apply",
        bounds=NormalizedBBox(left=0.69, top=0.27, width=0.08, height=0.06),
        role=SemanticCandidateClass.button_like.value,
        candidate_class=SemanticCandidateClass.button_like,
        confidence=0.93,
        visible=True,
        enabled=False,
        heuristic_explanations=("manual delta test candidate",),
        score_explanations=("manual delta test score",),
        score_factors={"class_prior": 0.72, "manual_delta_adjustment": 0.21},
        metadata={
            "semantic_origin": "candidate_generation",
            "candidate_scored": True,
            "candidate_class": SemanticCandidateClass.button_like.value,
            "source_layout_region_id": added_layout_region.region_id,
            "source_text_region_id": None,
            "source_text_block_id": None,
            "observe_only": True,
            "analysis_only": True,
            "non_actionable_candidate": True,
            "candidate_score": 0.93,
            "candidate_score_explanations": ("manual delta test score",),
            "candidate_score_factors": {"class_prior": 0.72, "manual_delta_adjustment": 0.21},
        },
    )

    after_candidates = tuple(
        updated_candidate if candidate.candidate_id == changed_candidate.candidate_id else candidate
        for candidate in before.candidates
        if candidate.candidate_id != removed_candidate.candidate_id
    ) + (added_candidate,)
    return replace(
        before,
        layout_regions=before.layout_regions + (added_layout_region,),
        text_regions=tuple(
            replace(region, extracted_text="Home Projects Settings Help")
            if region.region_id == changed_text_region.region_id
            else region
            for region in before.text_regions
        ),
        text_blocks=tuple(
            block for block in before.text_blocks if block.text_block_id != removed_text_block.text_block_id
        ),
        candidates=after_candidates,
        metadata={
            **dict(before.metadata),
            "generated_candidate_ids": _generated_candidate_ids(
                replace(before, candidates=after_candidates)
            ),
            "scored_candidate_ids": _generated_candidate_ids(
                replace(before, candidates=after_candidates)
            ),
            "candidate_ids": tuple(candidate.candidate_id for candidate in after_candidates),
            "candidate_score_map": _candidate_score_map(replace(before, candidates=after_candidates)),
            "candidate_scoring_average_score": _average_candidate_score(
                replace(before, candidates=after_candidates)
            ),
            "delta_phase_marker": "after",
        },
    )


def test_semantic_delta_compares_scored_snapshots_and_detects_changes() -> None:
    before = _scored_snapshot()
    after = _after_snapshot(before)

    result = ObserveOnlySemanticDeltaComparator().compare(before, after)

    assert result.success is True
    assert result.delta is not None
    delta = result.delta
    assert delta.summary.total_change_count == len(delta.all_changes)
    assert delta.summary.candidate_score_change_count == 1
    assert any(
        change.change_type is SemanticDeltaChangeType.added
        for change in delta.layout_region_changes
    )
    assert any(
        change.change_type is SemanticDeltaChangeType.changed
        for change in delta.text_region_changes
    )
    assert any(
        change.change_type is SemanticDeltaChangeType.removed
        for change in delta.text_block_changes
    )
    assert any(
        change.change_type is SemanticDeltaChangeType.added
        for change in delta.candidate_changes
    )
    assert any(
        change.change_type is SemanticDeltaChangeType.removed
        for change in delta.candidate_changes
    )
    score_change = delta.candidate_score_changes[0]
    assert score_change.item_id != "candidate-added"
    assert score_change.metadata["score_delta"] < 0.0
    assert "delta_phase_marker" in {
        change.item_id for change in delta.snapshot_metadata_changes
    }


def test_semantic_delta_metadata_and_ordering_are_deterministic() -> None:
    before = _scored_snapshot()
    after = _after_snapshot(before)

    result = ObserveOnlySemanticDeltaComparator().compare(before, after)

    assert result.success is True
    assert result.delta is not None
    delta = result.delta
    assert delta.metadata["sort_order"] == "category_then_item_id"
    assert delta.summary.changed_categories == tuple(sorted(delta.summary.changed_categories))
    assert tuple(change.item_id for change in delta.candidate_changes) == tuple(
        sorted(change.item_id for change in delta.candidate_changes)
    )
    assert delta.summary.before_counts[SemanticDeltaCategory.candidate.value] == len(before.candidates)
    assert delta.summary.after_counts[SemanticDeltaCategory.candidate.value] == len(after.candidates)
    assert delta.metadata["candidate_score_change_ids"] == tuple(
        change.item_id for change in delta.candidate_score_changes
    )


def test_semantic_delta_handles_partial_inputs_safely() -> None:
    before = _scored_snapshot()
    generated_candidate = next(
        candidate
        for candidate in before.candidates
        if candidate.metadata.get("semantic_origin") == "candidate_generation"
    )
    partial_after = replace(
        before,
        layout_tree=None,
        text_regions=(
            replace(before.text_regions[0], extracted_text=None, status=SemanticTextStatus.extracted),
            *before.text_regions[1:],
        ),
        text_blocks=(
            replace(before.text_blocks[0], extracted_text=None),
            *before.text_blocks[1:],
        ),
        candidates=tuple(
            replace(
                generated_candidate,
                candidate_class=None,
                confidence=None,
                metadata={
                    key: value
                    for key, value in generated_candidate.metadata.items()
                    if key != "source_layout_region_id"
                },
            )
            if candidate.candidate_id == generated_candidate.candidate_id
            else candidate
            for candidate in before.candidates
        ),
    )

    result = ObserveOnlySemanticDeltaComparator().compare(before, partial_after)

    assert result.success is True
    assert result.delta is not None
    delta = result.delta
    assert delta.signal_status == "partial"
    assert delta.metadata["missing_after_layout_tree"] is True
    assert before.text_regions[0].region_id in delta.metadata["incomplete_text_region_ids"]
    assert before.text_blocks[0].text_block_id in delta.metadata["incomplete_text_block_ids"]
    assert generated_candidate.candidate_id in delta.metadata["incomplete_candidate_ids"]


def test_semantic_delta_requires_before_and_after_snapshots() -> None:
    snapshot = _scored_snapshot()

    before_missing = ObserveOnlySemanticDeltaComparator().compare(None, snapshot)
    after_missing = ObserveOnlySemanticDeltaComparator().compare(snapshot, None)

    assert before_missing.success is False
    assert before_missing.error_code == "before_snapshot_unavailable"
    assert after_missing.success is False
    assert after_missing.error_code == "after_snapshot_unavailable"


def test_semantic_delta_preserves_observe_only_semantics() -> None:
    before = _scored_snapshot()
    after = _after_snapshot(before)

    result = ObserveOnlySemanticDeltaComparator().compare(before, after)

    assert result.success is True
    assert result.delta is not None
    delta = result.delta
    assert delta.observe_only is True
    assert delta.read_only is True
    assert delta.non_actionable is True
    assert delta.metadata["observe_only"] is True
    assert delta.metadata["read_only"] is True
    for change in delta.all_changes:
        assert change.observe_only is True
        assert change.read_only is True
        assert change.non_actionable is True


def test_semantic_delta_does_not_propagate_unhandled_exceptions() -> None:
    snapshot = _scored_snapshot()

    result = _ExplodingSemanticDeltaComparator().compare(snapshot, snapshot)

    assert result.success is False
    assert result.error_code == "semantic_delta_exception"
    assert result.error_message == "semantic delta comparator exploded"
