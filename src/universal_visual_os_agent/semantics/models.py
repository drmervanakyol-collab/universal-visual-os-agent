"""Semantic candidate contracts."""

from __future__ import annotations

from dataclasses import dataclass

from universal_visual_os_agent.geometry.models import NormalizedBBox


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticCandidate:
    """Target candidate derived from a visual or logical UI signal."""

    candidate_id: str
    label: str
    bounds: NormalizedBBox
    visible: bool = True
    enabled: bool = True
    occluded: bool = False

