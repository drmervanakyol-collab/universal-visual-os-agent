"""Semantic candidate and snapshot models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping
from uuid import uuid4

from universal_visual_os_agent.geometry.models import NormalizedBBox
from universal_visual_os_agent.semantics.layout import SemanticLayoutTree


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticCandidate:
    """Target candidate derived from semantic understanding."""

    candidate_id: str
    label: str
    bounds: NormalizedBBox
    node_id: str | None = None
    role: str | None = None
    confidence: float | None = None
    visible: bool = True
    enabled: bool = True
    occluded: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("candidate_id must not be empty.")
        if not self.label:
            raise ValueError("label must not be empty.")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")

    @property
    def actionable(self) -> bool:
        """Whether the candidate is currently eligible for a safe action."""

        return self.visible and self.enabled and not self.occluded


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticStateSnapshot:
    """A point-in-time semantic view of the UI state."""

    layout_tree: SemanticLayoutTree | None = None
    candidates: tuple[SemanticCandidate, ...] = ()
    snapshot_id: str = field(default_factory=lambda: str(uuid4()))
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        candidate_ids = {candidate.candidate_id for candidate in self.candidates}
        if len(candidate_ids) != len(self.candidates):
            raise ValueError("candidate identifiers must be unique within a snapshot.")

    def get_candidate(self, candidate_id: str) -> SemanticCandidate | None:
        """Find a candidate by identifier."""

        for candidate in self.candidates:
            if candidate.candidate_id == candidate_id:
                return candidate
        return None

    @property
    def visible_candidates(self) -> tuple[SemanticCandidate, ...]:
        """Return the candidates that are visible in this snapshot."""

        return tuple(candidate for candidate in self.candidates if candidate.visible)

