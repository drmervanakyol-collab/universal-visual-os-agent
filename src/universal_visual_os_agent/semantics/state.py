"""Semantic candidate and snapshot models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Mapping
from uuid import uuid4

from universal_visual_os_agent.geometry.models import NormalizedBBox
from universal_visual_os_agent.semantics.layout import SemanticLayoutTree


class SemanticTextStatus(StrEnum):
    """Status of a text region in the observe-only OCR pipeline."""

    pending = "pending"
    extracted = "extracted"
    unavailable = "unavailable"


class SemanticLayoutRegionKind(StrEnum):
    """High-level geometric region semantics for observe-only layout analysis."""

    full_surface = "full_surface"
    header = "header"
    content = "content"
    footer = "footer"
    left_sidebar = "left_sidebar"
    right_sidebar = "right_sidebar"
    modal_like = "modal_like"


class SemanticLayoutRole(StrEnum):
    """Conservative semantic interpretations layered on top of geometric regions."""

    application_surface = "application_surface"
    header_bar = "header_bar"
    navigation_header = "navigation_header"
    primary_content = "primary_content"
    footer_bar = "footer_bar"
    status_footer = "status_footer"
    sidebar_panel = "sidebar_panel"
    navigation_sidebar = "navigation_sidebar"
    dialog_overlay = "dialog_overlay"


class SemanticCandidateClass(StrEnum):
    """Non-actionable heuristic classes for semantic candidate generation."""

    button_like = "button_like"
    input_like = "input_like"
    tab_like = "tab_like"
    close_like = "close_like"
    popup_dismiss_like = "popup_dismiss_like"
    interactive_region_like = "interactive_region_like"


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticRegionBlock:
    """A non-actionable analysis region derived from the observed frame."""

    block_id: str
    label: str
    bounds: NormalizedBBox
    node_id: str | None = None
    role: str = "analysis_region"
    visible: bool = True
    enabled: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.block_id:
            raise ValueError("block_id must not be empty.")
        if not self.label:
            raise ValueError("label must not be empty.")
        if not self.role:
            raise ValueError("role must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticLayoutRegion:
    """A geometric region derived from semantic scaffold and OCR-aware analysis."""

    region_id: str
    kind: SemanticLayoutRegionKind
    label: str
    bounds: NormalizedBBox
    node_id: str | None = None
    semantic_role: SemanticLayoutRole | None = None
    parent_region_id: str | None = None
    source_region_block_ids: tuple[str, ...] = ()
    source_text_region_ids: tuple[str, ...] = ()
    visible: bool = True
    enabled: bool = False
    confidence: float | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.region_id:
            raise ValueError("region_id must not be empty.")
        if not self.label:
            raise ValueError("label must not be empty.")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticTextRegion:
    """A text/OCR-oriented semantic region derived from the observe-only pipeline."""

    region_id: str
    label: str
    bounds: NormalizedBBox
    node_id: str | None = None
    block_id: str | None = None
    role: str = "text_region"
    status: SemanticTextStatus = SemanticTextStatus.pending
    visible: bool = True
    enabled: bool = False
    extracted_text: str | None = None
    confidence: float | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.region_id:
            raise ValueError("region_id must not be empty.")
        if not self.label:
            raise ValueError("label must not be empty.")
        if not self.role:
            raise ValueError("role must not be empty.")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticTextBlock:
    """A non-actionable OCR/text block derived from a text region."""

    text_block_id: str
    region_id: str
    label: str
    bounds: NormalizedBBox
    role: str = "text_block"
    visible: bool = True
    enabled: bool = False
    extracted_text: str | None = None
    confidence: float | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text_block_id:
            raise ValueError("text_block_id must not be empty.")
        if not self.region_id:
            raise ValueError("region_id must not be empty.")
        if not self.label:
            raise ValueError("label must not be empty.")
        if not self.role:
            raise ValueError("role must not be empty.")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticCandidate:
    """Target candidate derived from semantic understanding."""

    candidate_id: str
    label: str
    bounds: NormalizedBBox
    node_id: str | None = None
    role: str | None = None
    candidate_class: SemanticCandidateClass | None = None
    confidence: float | None = None
    visible: bool = True
    enabled: bool = True
    occluded: bool = False
    heuristic_explanations: tuple[str, ...] = ()
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
    region_blocks: tuple[SemanticRegionBlock, ...] = ()
    layout_regions: tuple[SemanticLayoutRegion, ...] = ()
    text_regions: tuple[SemanticTextRegion, ...] = ()
    text_blocks: tuple[SemanticTextBlock, ...] = ()
    candidates: tuple[SemanticCandidate, ...] = ()
    snapshot_id: str = field(default_factory=lambda: str(uuid4()))
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        region_block_ids = {block.block_id for block in self.region_blocks}
        if len(region_block_ids) != len(self.region_blocks):
            raise ValueError("region block identifiers must be unique within a snapshot.")
        layout_region_ids = {region.region_id for region in self.layout_regions}
        if len(layout_region_ids) != len(self.layout_regions):
            raise ValueError("layout region identifiers must be unique within a snapshot.")
        text_region_ids = {region.region_id for region in self.text_regions}
        if len(text_region_ids) != len(self.text_regions):
            raise ValueError("text region identifiers must be unique within a snapshot.")
        text_block_ids = {block.text_block_id for block in self.text_blocks}
        if len(text_block_ids) != len(self.text_blocks):
            raise ValueError("text block identifiers must be unique within a snapshot.")
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
