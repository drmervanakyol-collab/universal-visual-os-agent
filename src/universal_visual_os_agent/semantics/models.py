"""Compatibility exports for semantic models."""

from universal_visual_os_agent.semantics.building import (
    PreparedSemanticStateBuilder,
    SemanticStateBuildResult,
)
from universal_visual_os_agent.semantics.interfaces import (
    SemanticExtractionInputAdapter,
    SemanticStateBuilder,
)
from universal_visual_os_agent.semantics.layout import SemanticLayoutTree, SemanticNode
from universal_visual_os_agent.semantics.preparation import (
    FullDesktopCaptureSemanticInputAdapter,
    SemanticExtractionInput,
    SemanticExtractionPreparationResult,
    SemanticSnapshotPreparation,
)
from universal_visual_os_agent.semantics.state import SemanticCandidate, SemanticStateSnapshot

__all__ = [
    "FullDesktopCaptureSemanticInputAdapter",
    "PreparedSemanticStateBuilder",
    "SemanticCandidate",
    "SemanticExtractionInput",
    "SemanticExtractionInputAdapter",
    "SemanticExtractionPreparationResult",
    "SemanticLayoutTree",
    "SemanticNode",
    "SemanticStateBuildResult",
    "SemanticStateBuilder",
    "SemanticSnapshotPreparation",
    "SemanticStateSnapshot",
]
