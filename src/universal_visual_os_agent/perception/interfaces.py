"""Perception provider interfaces."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.perception.models import CaptureResult
from universal_visual_os_agent.perception.visual_grounding_models import (
    VisualGroundingRequest,
    VisualGroundingResult,
)


class CaptureProvider(Protocol):
    """Abstract frame provider for live or replay sources."""

    def capture_frame(self) -> CaptureResult:
        """Return the latest capture result without performing input actions."""


class VisualGroundingProvider(Protocol):
    """Abstract observe-only provider for non-text visual grounding scaffolding."""

    def ground(self, request: VisualGroundingRequest) -> VisualGroundingResult:
        """Return structured non-text grounding output without executing actions."""
