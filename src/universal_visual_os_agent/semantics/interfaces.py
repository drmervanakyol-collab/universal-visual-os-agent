"""Semantic extraction preparation contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from universal_visual_os_agent.perception.models import CaptureResult

    from .building import SemanticStateBuildResult
    from .candidate_exposure import CandidateExposureOptions, CandidateExposureResult
    from .candidate_generation import CandidateGenerationResult
    from .candidate_scoring import CandidateScoringResult
    from .layout_region_analysis import LayoutRegionAnalysisResult
    from .ocr import TextExtractionRequest, TextExtractionResponse, TextExtractionResult
    from .preparation import SemanticExtractionPreparationResult
    from .semantic_delta import SemanticDeltaResult
    from .semantic_layout_enrichment import SemanticLayoutEnrichmentResult
    from .state import SemanticStateSnapshot


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


class CandidateGenerator(Protocol):
    """Generate richer observe-only semantic candidates from enriched snapshots."""

    def generate(self, snapshot: SemanticStateSnapshot) -> CandidateGenerationResult:
        """Return a structured observe-only candidate generation result."""


class CandidateScorer(Protocol):
    """Score generated observe-only semantic candidates."""

    def score(self, snapshot: SemanticStateSnapshot) -> CandidateScoringResult:
        """Return a structured observe-only candidate scoring result."""


class CandidateExposer(Protocol):
    """Expose scored observe-only semantic candidates in a stable view."""

    def expose(
        self,
        snapshot: SemanticStateSnapshot,
        *,
        options: CandidateExposureOptions | None = None,
    ) -> CandidateExposureResult:
        """Return a structured observe-only candidate exposure result."""


class SemanticDeltaComparator(Protocol):
    """Compare semantic snapshots into a structured observe-only delta."""

    def compare(
        self,
        before: SemanticStateSnapshot | None,
        after: SemanticStateSnapshot | None,
    ) -> SemanticDeltaResult:
        """Return a structured observe-only semantic delta result."""
