"""Semantic state contracts for the phase-4 pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

from universal_visual_os_agent.geometry.models import NormalizedBBox


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticLayoutNode:
    """A logical UI element in a semantic layout tree."""

    node_id: str
    role: str
    label: str = ""
    bounds: NormalizedBBox | None = None
    parent_id: str | None = None
    child_ids: tuple[str, ...] = field(default_factory=tuple)
    visible: bool = True
    enabled: bool = True
    occluded: bool = False

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("node_id must not be empty.")
        if not self.role:
            raise ValueError("role must not be empty.")
        if self.parent_id == self.node_id:
            raise ValueError("parent_id cannot match node_id.")
        if self.node_id in self.child_ids:
            raise ValueError("child_ids must not contain node_id.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticLayoutTree:
    """A validated parent/child index for semantic layout nodes."""

    root_id: str
    nodes: dict[str, SemanticLayoutNode]

    def __post_init__(self) -> None:
        if not self.root_id:
            raise ValueError("root_id must not be empty.")
        if self.root_id not in self.nodes:
            raise ValueError("root_id must exist in nodes.")
        self._validate_parent_child_consistency()

    def _validate_parent_child_consistency(self) -> None:
        for node in self.nodes.values():
            if node.parent_id is not None and node.parent_id not in self.nodes:
                raise ValueError(f"node {node.node_id} parent_id references unknown node.")

            for child_id in node.child_ids:
                child = self.nodes.get(child_id)
                if child is None:
                    raise ValueError(f"node {node.node_id} contains unknown child_id {child_id}.")
                if child.parent_id != node.node_id:
                    raise ValueError(
                        f"child {child_id} parent_id does not match parent {node.node_id}."
                    )

        root = self.nodes[self.root_id]
        if root.parent_id is not None:
            raise ValueError("root node must not have a parent_id.")

    def children_of(self, node_id: str) -> tuple[SemanticLayoutNode, ...]:
        """Return direct child nodes for the given node identifier."""

        node = self.nodes[node_id]
        return tuple(self.nodes[child_id] for child_id in node.child_ids)


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticCandidate:
    """A target candidate derived from semantic state."""

    candidate_id: str
    label: str
    bounds: NormalizedBBox
    source_node_id: str | None = None
    visible: bool = True
    enabled: bool = True
    occluded: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("candidate_id must not be empty.")

    @property
    def is_actionable(self) -> bool:
        """Return whether the candidate can safely be considered for action planning."""

        return self.visible and self.enabled and not self.occluded


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticStateSnapshot:
    """A partial-or-complete semantic state snapshot from perception/replay."""

    layout_tree: SemanticLayoutTree | None = None
    candidates: tuple[SemanticCandidate, ...] = field(default_factory=tuple)

    def actionable_candidates(self) -> tuple[SemanticCandidate, ...]:
        """Return candidates that are safe for planning in observe/dry-run flows."""

        return tuple(candidate for candidate in self.candidates if candidate.is_actionable)

    def resolve_node(self, node_id: str | None) -> SemanticLayoutNode | None:
        """Resolve a semantic node safely when full state may be missing."""

        if node_id is None or self.layout_tree is None:
            return None
        return self.layout_tree.nodes.get(node_id)
