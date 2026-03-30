from __future__ import annotations

import pytest

from universal_visual_os_agent.geometry import NormalizedBBox
from universal_visual_os_agent.semantics import (
    SemanticCandidate,
    SemanticLayoutTree,
    SemanticNode,
    SemanticRegionBlock,
    SemanticStateSnapshot,
    SemanticTextRegion,
)
from universal_visual_os_agent.verification import (
    SemanticStateTransition,
    SemanticTransitionExpectation,
    VerificationStatus,
    evaluate_semantic_transition,
)


def _button_bounds() -> NormalizedBBox:
    return NormalizedBBox(left=0.1, top=0.2, width=0.3, height=0.1)


def test_layout_tree_walk_and_find_node() -> None:
    child = SemanticNode(node_id="button-1", role="button", name="Submit", bounds=_button_bounds())
    root = SemanticNode(node_id="root", role="window", children=(child,))
    tree = SemanticLayoutTree(root=root, display_id="primary")

    walked_ids = tuple(node.node_id for node in tree.walk())

    assert walked_ids == ("root", "button-1")
    assert tree.find_node("button-1") == child
    assert tree.find_node("missing") is None


def test_semantic_candidate_actionable_and_snapshot_lookup() -> None:
    actionable = SemanticCandidate(
        candidate_id="candidate-1",
        label="Submit",
        bounds=_button_bounds(),
        node_id="button-1",
        role="button",
        confidence=0.9,
    )
    hidden = SemanticCandidate(
        candidate_id="candidate-2",
        label="Cancel",
        bounds=NormalizedBBox(left=0.5, top=0.2, width=0.2, height=0.1),
        visible=False,
    )
    snapshot = SemanticStateSnapshot(candidates=(actionable, hidden))

    assert actionable.actionable is True
    assert hidden.actionable is False
    assert snapshot.get_candidate("candidate-1") == actionable
    assert snapshot.visible_candidates == (actionable,)


def test_semantic_snapshot_rejects_duplicate_candidate_ids() -> None:
    candidate = SemanticCandidate(candidate_id="duplicate", label="Submit", bounds=_button_bounds())

    with pytest.raises(ValueError, match="candidate identifiers must be unique"):
        SemanticStateSnapshot(candidates=(candidate, candidate))


def test_semantic_snapshot_rejects_duplicate_region_block_ids() -> None:
    block = SemanticRegionBlock(
        block_id="region-1",
        label="Analysis Region",
        bounds=_button_bounds(),
    )

    with pytest.raises(ValueError, match="region block identifiers must be unique"):
        SemanticStateSnapshot(region_blocks=(block, block))


def test_semantic_snapshot_rejects_duplicate_text_region_ids() -> None:
    text_region = SemanticTextRegion(
        region_id="text-1",
        label="Detected Text Region",
        bounds=_button_bounds(),
    )

    with pytest.raises(ValueError, match="text region identifiers must be unique"):
        SemanticStateSnapshot(text_regions=(text_region, text_region))


def test_verification_contract_satisfied_when_required_state_is_present() -> None:
    button_node = SemanticNode(node_id="button-1", role="button", name="Submit", bounds=_button_bounds())
    tree = SemanticLayoutTree(root=SemanticNode(node_id="root", role="window", children=(button_node,)))
    snapshot = SemanticStateSnapshot(
        layout_tree=tree,
        candidates=(
            SemanticCandidate(candidate_id="submit", label="Submit", bounds=_button_bounds(), node_id="button-1"),
        ),
    )
    expectation = SemanticTransitionExpectation(
        summary="Submit button should remain available",
        required_candidate_ids=("submit",),
        required_node_ids=("button-1",),
    )

    result = evaluate_semantic_transition(
        expectation,
        SemanticStateTransition(before=None, after=snapshot),
    )

    assert result.status is VerificationStatus.satisfied
    assert result.success is True
    assert result.matched_candidate_ids == ("submit",)
    assert result.missing_candidate_ids == ()
    assert result.missing_node_ids == ()


def test_verification_contract_detects_missing_and_forbidden_state() -> None:
    snapshot = SemanticStateSnapshot(
        candidates=(
            SemanticCandidate(candidate_id="danger", label="Delete", bounds=_button_bounds()),
        )
    )
    expectation = SemanticTransitionExpectation(
        summary="Only safe candidate should be present",
        required_candidate_ids=("submit",),
        forbidden_candidate_ids=("danger",),
        required_node_ids=("button-1",),
    )

    result = evaluate_semantic_transition(
        expectation,
        SemanticStateTransition(before=None, after=snapshot),
    )

    assert result.status is VerificationStatus.unsatisfied
    assert result.success is False
    assert result.missing_candidate_ids == ("submit",)
    assert result.unexpected_candidate_ids == ("danger",)
    assert result.missing_node_ids == ("button-1",)
