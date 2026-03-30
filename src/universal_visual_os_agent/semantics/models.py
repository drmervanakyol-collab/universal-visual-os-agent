"""Compatibility exports for semantic models."""

from universal_visual_os_agent.semantics.building import (
    PreparedSemanticStateBuilder,
    SemanticStateBuildResult,
)
from universal_visual_os_agent.semantics.interfaces import (
    SemanticExtractionInputAdapter,
    SemanticStateBuilder,
    TextExtractionBackend,
    TextExtractionAdapter,
)
from universal_visual_os_agent.semantics.layout import SemanticLayoutTree, SemanticNode
from universal_visual_os_agent.semantics.ocr import (
    PreparedSemanticTextExtractionAdapter,
    TextExtractionRegionRequest,
    TextExtractionRequest,
    TextExtractionResponse,
    TextExtractionResponseStatus,
    TextExtractionResult,
)
from universal_visual_os_agent.semantics.preparation import (
    FullDesktopCaptureSemanticInputAdapter,
    SemanticExtractionInput,
    SemanticExtractionPreparationResult,
    SemanticSnapshotPreparation,
)
from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
    SemanticRegionBlock,
    SemanticStateSnapshot,
    SemanticTextBlock,
    SemanticTextRegion,
    SemanticTextStatus,
)

__all__ = [
    "FullDesktopCaptureSemanticInputAdapter",
    "PreparedSemanticStateBuilder",
    "PreparedSemanticTextExtractionAdapter",
    "SemanticCandidate",
    "SemanticExtractionInput",
    "SemanticExtractionInputAdapter",
    "SemanticExtractionPreparationResult",
    "SemanticLayoutTree",
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
