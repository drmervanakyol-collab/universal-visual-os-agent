"""Compatibility exports for semantic models."""

from universal_visual_os_agent.semantics.building import (
    PreparedSemanticStateBuilder,
    SemanticStateBuildResult,
)
from universal_visual_os_agent.semantics.candidate_generation import (
    CandidateGenerationResult,
    ObserveOnlyCandidateGenerator,
)
from universal_visual_os_agent.semantics.candidate_exposure import (
    CandidateExposureOptions,
    CandidateExposureResult,
    CandidateExposureView,
    ExposedCandidate,
    ExposedCandidateGroup,
    ObserveOnlyCandidateExposer,
)
from universal_visual_os_agent.semantics.candidate_scoring import (
    CandidateScoringResult,
    ObserveOnlyCandidateScorer,
)
from universal_visual_os_agent.semantics.interfaces import (
    CandidateExposer,
    CandidateGenerator,
    CandidateScorer,
    LayoutRegionAnalyzer,
    SemanticExtractionInputAdapter,
    SemanticLayoutEnricher,
    SemanticDeltaComparator,
    SemanticStateBuilder,
    TextExtractionBackend,
    TextExtractionAdapter,
)
from universal_visual_os_agent.semantics.layout import SemanticLayoutTree, SemanticNode
from universal_visual_os_agent.semantics.layout_region_analysis import (
    GeometricLayoutRegionAnalyzer,
    LayoutRegionAnalysisResult,
)
from universal_visual_os_agent.semantics.ontology import (
    CandidateOntologyCarrier,
    CandidateProvenanceRecord,
    CandidateSelectionRiskLevel,
    SemanticCandidateSourceType,
)
from universal_visual_os_agent.semantics.ocr import (
    PreparedSemanticTextExtractionAdapter,
    TextExtractionRegionRequest,
    TextExtractionRequest,
    TextExtractionResponse,
    TextExtractionResponseStatus,
    TextExtractionResult,
)
from universal_visual_os_agent.semantics.ocr_rapidocr import RapidOcrTextExtractionBackend
from universal_visual_os_agent.semantics.preparation import (
    FullDesktopCaptureSemanticInputAdapter,
    SemanticExtractionInput,
    SemanticExtractionPreparationResult,
    SemanticSnapshotPreparation,
)
from universal_visual_os_agent.semantics.semantic_delta import (
    ObserveOnlySemanticDeltaComparator,
    SemanticDelta,
    SemanticDeltaCategory,
    SemanticDeltaChange,
    SemanticDeltaChangeType,
    SemanticDeltaResult,
    SemanticDeltaSummary,
)
from universal_visual_os_agent.semantics.semantic_layout_enrichment import (
    OcrAwareSemanticLayoutEnricher,
    SemanticLayoutEnrichmentResult,
)
from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
    SemanticCandidateClass,
    SemanticLayoutRegion,
    SemanticLayoutRegionKind,
    SemanticLayoutRole,
    SemanticRegionBlock,
    SemanticStateSnapshot,
    SemanticTextBlock,
    SemanticTextRegion,
    SemanticTextStatus,
)

__all__ = [
    "CandidateExposer",
    "CandidateOntologyCarrier",
    "CandidateProvenanceRecord",
    "CandidateSelectionRiskLevel",
    "CandidateExposureOptions",
    "CandidateExposureResult",
    "CandidateExposureView",
    "CandidateGenerationResult",
    "CandidateGenerator",
    "CandidateScorer",
    "CandidateScoringResult",
    "ExposedCandidate",
    "ExposedCandidateGroup",
    "FullDesktopCaptureSemanticInputAdapter",
    "GeometricLayoutRegionAnalyzer",
    "LayoutRegionAnalysisResult",
    "LayoutRegionAnalyzer",
    "ObserveOnlyCandidateExposer",
    "ObserveOnlyCandidateGenerator",
    "ObserveOnlyCandidateScorer",
    "OcrAwareSemanticLayoutEnricher",
    "PreparedSemanticStateBuilder",
    "PreparedSemanticTextExtractionAdapter",
    "RapidOcrTextExtractionBackend",
    "SemanticCandidate",
    "SemanticCandidateClass",
    "SemanticCandidateSourceType",
    "SemanticExtractionInput",
    "SemanticExtractionInputAdapter",
    "SemanticExtractionPreparationResult",
    "SemanticLayoutEnricher",
    "SemanticLayoutEnrichmentResult",
    "SemanticDelta",
    "SemanticDeltaCategory",
    "SemanticDeltaChange",
    "SemanticDeltaChangeType",
    "SemanticDeltaComparator",
    "SemanticDeltaResult",
    "SemanticDeltaSummary",
    "SemanticLayoutTree",
    "SemanticLayoutRegion",
    "SemanticLayoutRegionKind",
    "SemanticLayoutRole",
    "SemanticNode",
    "ObserveOnlySemanticDeltaComparator",
    "SemanticRegionBlock",
    "SemanticTextRegion",
    "SemanticTextBlock",
    "SemanticTextStatus",
    "SemanticStateBuildResult",
    "SemanticStateBuilder",
    "SemanticSnapshotPreparation",
    "SemanticStateSnapshot",
    "TextExtractionAdapter",
    "TextExtractionBackend",
    "TextExtractionRegionRequest",
    "TextExtractionRequest",
    "TextExtractionResponse",
    "TextExtractionResponseStatus",
    "TextExtractionResult",
]
