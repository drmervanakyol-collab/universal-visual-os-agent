"""Semantic extraction preparation contracts."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.perception.models import CaptureResult
from universal_visual_os_agent.semantics.building import SemanticStateBuildResult
from universal_visual_os_agent.semantics.layout_region_analysis import (
    LayoutRegionAnalysisResult,
)
from universal_visual_os_agent.semantics.ocr import (
    TextExtractionRequest,
    TextExtractionResponse,
    TextExtractionResult,
)
from universal_visual_os_agent.semantics.preparation import (
    SemanticExtractionPreparationResult,
)
from universal_visual_os_agent.semantics.semantic_layout_enrichment import (
    SemanticLayoutEnrichmentResult,
)
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot


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


class TextExtractionBackend(Protocol):
    """Future OCR backend contract for observe-only text extraction requests."""

    def run(self, request: TextExtractionRequest) -> TextExtractionResponse:
        """Return a structured OCR/text extraction response."""


class LayoutRegionAnalyzer(Protocol):
    """Analyze a semantic snapshot into higher-level geometric layout regions."""

    def analyze(self, snapshot: SemanticStateSnapshot) -> LayoutRegionAnalysisResult:
        """Return a structured layout region analysis result."""


class SemanticLayoutEnricher(Protocol):
    """Refine geometric layout regions into stronger semantic interpretations."""

    def enrich(self, snapshot: SemanticStateSnapshot) -> SemanticLayoutEnrichmentResult:
        """Return a structured semantic layout enrichment result."""
