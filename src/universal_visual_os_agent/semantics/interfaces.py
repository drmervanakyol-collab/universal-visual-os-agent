"""Semantic extraction preparation contracts."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.perception.models import CaptureResult
from universal_visual_os_agent.semantics.building import SemanticStateBuildResult
from universal_visual_os_agent.semantics.ocr import TextExtractionResult
from universal_visual_os_agent.semantics.preparation import (
    SemanticExtractionPreparationResult,
)


class SemanticExtractionInputAdapter(Protocol):
    """Prepare semantic extraction input from observe-only capture results."""

    def prepare(self, capture_result: CaptureResult) -> SemanticExtractionPreparationResult:
        """Return a structured semantic extraction preparation result."""


class SemanticStateBuilder(Protocol):
    """Build semantic state objects from prepared semantic extraction input."""

    def build(self, preparation_result: SemanticExtractionPreparationResult) -> SemanticStateBuildResult:
        """Return a structured semantic state build result."""


class TextExtractionAdapter(Protocol):
    """Extract OCR/text-ready semantic signals from prepared semantic state."""

    def extract(
        self,
        preparation_result: SemanticExtractionPreparationResult,
        state_result: SemanticStateBuildResult,
    ) -> TextExtractionResult:
        """Return a structured text extraction scaffolding result."""
