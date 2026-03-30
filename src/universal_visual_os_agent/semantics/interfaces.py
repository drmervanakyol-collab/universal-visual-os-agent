"""Semantic extraction preparation contracts."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.perception.models import CaptureResult
from universal_visual_os_agent.semantics.preparation import (
    SemanticExtractionPreparationResult,
)


class SemanticExtractionInputAdapter(Protocol):
    """Prepare semantic extraction input from observe-only capture results."""

    def prepare(self, capture_result: CaptureResult) -> SemanticExtractionPreparationResult:
        """Return a structured semantic extraction preparation result."""
