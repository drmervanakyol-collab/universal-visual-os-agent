"""Semantic layout tree models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Mapping

from universal_visual_os_agent.geometry.models import NormalizedBBox


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticNode:
    """A logical UI node in the semantic layout tree."""

    node_id: str
    role: str
    name: str | None = None
    bounds: NormalizedBBox | None = None
    visible: bool = True
    enabled: bool = True
    children: tuple["SemanticNode", ...] = ()
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("node_id must not be empty.")
        if not self.role:
            raise ValueError("role must not be empty.")

    def walk(self) -> Iterator["SemanticNode"]:
        """Yield this node and all descendants depth-first."""

        yield self
        for child in self.children:
            yield from child.walk()


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticLayoutTree:
    """A semantic representation of the current UI layout."""

    root: SemanticNode
    display_id: str | None = None

    def __post_init__(self) -> None:
        if self.display_id == "":
            raise ValueError("display_id must not be an empty string.")

    def find_node(self, node_id: str) -> SemanticNode | None:
        """Find a node by identifier."""

        for node in self.root.walk():
            if node.node_id == node_id:
                return node
        return None

    def walk(self) -> tuple[SemanticNode, ...]:
        """Return every node in depth-first order."""

        return tuple(self.root.walk())

