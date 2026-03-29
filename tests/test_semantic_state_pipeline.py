from __future__ import annotations

import pytest

from universal_visual_os_agent.geometry.models import NormalizedBBox
from universal_visual_os_agent.semantics.models import (
    SemanticCandidate,
    SemanticLayoutNode,
    SemanticLayoutTree,
    SemanticStateSnapshot,
)
from universal_visual_os_agent.verification.models import (
    SemanticStateExpectation,
    VerificationContract,
)


def _bbox() -> NormalizedBBox:
    return NormalizedBBox(left=0.1, top=0.1, width=0.2, height=0.2)


def test_semantic_candidate_validity_flags_drive_actionability() -> None:
    candidate = SemanticCandidate(candidate_id="c-1", label="Submit", bounds=_bbox())
    hidden = SemanticCandidate(candidate_id="c-2", label="Hidden", bounds=_bbox(), visible=False)
    blocked = SemanticCandidate(candidate_id="c-3", label="Blocked", bounds=_bbox(), occluded=True)

    assert candidate.is_actionable is True
    assert hidden.is_actionable is False
    assert blocked.is_actionable is False


def test_layout_tree_parent_child_consistency() -> None:
    root = SemanticLayoutNode(node_id="root", role="window", child_ids=("button",))
    button = SemanticLayoutNode(
        node_id="button",
        role="button",
        parent_id="root",
        child_ids=(),
    )

    tree = SemanticLayoutTree(root_id="root", nodes={"root": root, "button": button})

    assert tree.children_of("root") == (button,)


def test_layout_tree_rejects_inconsistent_parent_child_links() -> None:
    root = SemanticLayoutNode(node_id="root", role="window", child_ids=("button",))
    button = SemanticLayoutNode(node_id="button", role="button", parent_id="other")

    with pytest.raises(ValueError, match="parent_id does not match parent"):
        SemanticLayoutTree(root_id="root", nodes={"root": root, "button": button})


def test_visibility_enabled_occlusion_flags_filter_actionable_candidates() -> None:
    state = SemanticStateSnapshot(
        candidates=(
            SemanticCandidate(candidate_id="ok", label="OK", bounds=_bbox()),
            SemanticCandidate(candidate_id="hidden", label="Hidden", bounds=_bbox(), visible=False),
            SemanticCandidate(candidate_id="disabled", label="Disabled", bounds=_bbox(), enabled=False),
            SemanticCandidate(candidate_id="blocked", label="Blocked", bounds=_bbox(), occluded=True),
        )
    )

    assert tuple(item.candidate_id for item in state.actionable_candidates()) == ("ok",)


def test_verification_contract_serialization_and_validation() -> None:
    contract = VerificationContract(
        contract_id="verify-submit",
        expectations=(
            SemanticStateExpectation(target_candidate_id="submit-button"),
        ),
        metadata={"phase": "semantic"},
    )

    payload = contract.to_dict()
    restored = VerificationContract.from_dict(payload)

    assert restored == contract


def test_verification_contract_requires_at_least_one_expectation() -> None:
    with pytest.raises(ValueError, match="expectations must not be empty"):
        VerificationContract(contract_id="empty", expectations=())


def test_semantic_state_handles_missing_or_partial_data_safely() -> None:
    state = SemanticStateSnapshot()

    assert state.resolve_node("missing") is None
    assert state.actionable_candidates() == ()

    root = SemanticLayoutNode(node_id="root", role="window")
    tree = SemanticLayoutTree(root_id="root", nodes={"root": root})
    partial_state = SemanticStateSnapshot(layout_tree=tree)

    assert partial_state.resolve_node("root") == root
    assert partial_state.resolve_node("other") is None
