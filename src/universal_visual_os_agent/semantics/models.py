"""Compatibility exports for semantic models."""

from universal_visual_os_agent.semantics.building import (
    PreparedSemanticStateBuilder,
    SemanticStateBuildResult,
)
from universal_visual_os_agent.semantics.interfaces import (
    LayoutRegionAnalyzer,
    SemanticExtractionInputAdapter,
    SemanticLayoutEnricher,
    SemanticStateBuilder,
    TextExtractionBackend,
    TextExtractionAdapter,
)
from universal_visual_os_agent.semantics.layout import SemanticLayoutTree, SemanticNode
from universal_visual_os_agent.semantics.layout_region_analysis import (
    GeometricLayoutRegionAnalyzer,
    LayoutRegionAnalysisResult,
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
from universal_visual_os_agent.semantics.semantic_layout_enrichment import (
    OcrAwareSemanticLayoutEnricher,
    SemanticLayoutEnrichmentResult,
)
from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
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
    "FullDesktopCaptureSemanticInputAdapter",
    "GeometricLayoutRegionAnalyzer",
    "LayoutRegionAnalysisResult",
    "LayoutRegionAnalyzer",
    "OcrAwareSemanticLayoutEnricher",
    "PreparedSemanticStateBuilder",
    "PreparedSemanticTextExtractionAdapter",
    "RapidOcrTextExtractionBackend",
    "SemanticCandidate",
    "SemanticExtractionInput",
    "SemanticExtractionInputAdapter",
    "SemanticExtractionPreparationResult",
    "SemanticLayoutEnricher",
    "SemanticLayoutEnrichmentResult",
    "SemanticLayoutTree",
    "SemanticLayoutRegion",
    "SemanticLayoutRegionKind",
    "SemanticLayoutRole",
    "SemanticNode",
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
