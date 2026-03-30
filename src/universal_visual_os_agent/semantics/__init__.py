"""Semantic understanding exports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

_EXPORT_MODULES = {
    ".interfaces": (
        "CandidateExposer",
        "CandidateGenerator",
        "CandidateScorer",
        "LayoutRegionAnalyzer",
        "SemanticExtractionInputAdapter",
        "SemanticLayoutEnricher",
        "SemanticDeltaComparator",
        "SemanticStateBuilder",
        "TextExtractionBackend",
        "TextExtractionAdapter",
    ),
    ".ontology": (
        "CandidateOntologyCarrier",
        "CandidateProvenanceRecord",
        "CandidateResolverReadiness",
        "CandidateResolverReadinessReason",
        "CandidateResolverReadinessStatus",
        "CandidateSelectionRiskLevel",
        "SemanticCandidateSourceType",
        "evaluate_candidate_resolver_readiness",
    ),
    ".candidate_exposure": (
        "CandidateExposureOptions",
        "CandidateExposureResult",
        "CandidateExposureView",
        "ExposedCandidate",
        "ExposedCandidateGroup",
        "ObserveOnlyCandidateExposer",
    ),
    ".candidate_generation": (
        "CandidateGenerationResult",
        "ObserveOnlyCandidateGenerator",
    ),
    ".candidate_scoring": (
        "CandidateScoringResult",
        "ObserveOnlyCandidateScorer",
    ),
    ".preparation": (
        "FullDesktopCaptureSemanticInputAdapter",
        "SemanticExtractionInput",
        "SemanticExtractionPreparationResult",
        "SemanticSnapshotPreparation",
    ),
    ".layout_region_analysis": (
        "GeometricLayoutRegionAnalyzer",
        "LayoutRegionAnalysisResult",
    ),
    ".semantic_layout_enrichment": (
        "OcrAwareSemanticLayoutEnricher",
        "SemanticLayoutEnrichmentResult",
    ),
    ".building": (
        "PreparedSemanticStateBuilder",
        "SemanticStateBuildResult",
    ),
    ".ocr": (
        "PreparedSemanticTextExtractionAdapter",
        "TextExtractionRegionRequest",
        "TextExtractionRequest",
        "TextExtractionResponse",
        "TextExtractionResponseStatus",
        "TextExtractionResult",
    ),
    ".ocr_rapidocr": ("RapidOcrTextExtractionBackend",),
    ".layout": ("SemanticLayoutTree", "SemanticNode"),
    ".semantic_delta": (
        "ObserveOnlySemanticDeltaComparator",
        "SemanticDelta",
        "SemanticDeltaCategory",
        "SemanticDeltaChange",
        "SemanticDeltaChangeType",
        "SemanticDeltaResult",
        "SemanticDeltaSummary",
    ),
    ".state": (
        "SemanticCandidate",
        "SemanticCandidateClass",
        "SemanticLayoutRegion",
        "SemanticLayoutRegionKind",
        "SemanticLayoutRole",
        "SemanticRegionBlock",
        "SemanticStateSnapshot",
        "SemanticTextBlock",
        "SemanticTextRegion",
        "SemanticTextStatus",
    ),
}
_EXPORTS = {
    name: module_name
    for module_name, names in _EXPORT_MODULES.items()
    for name in names
}

__all__ = tuple(name for names in _EXPORT_MODULES.values() for name in names)


def __getattr__(name: str) -> object:
    """Lazily resolve public semantic exports to reduce package import coupling."""

    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name, __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return a stable view of module globals plus lazy exports."""

    return sorted((*globals(), *__all__))


if TYPE_CHECKING:
    from .building import PreparedSemanticStateBuilder, SemanticStateBuildResult
    from .candidate_exposure import (
        CandidateExposureOptions,
        CandidateExposureResult,
        CandidateExposureView,
        ExposedCandidate,
        ExposedCandidateGroup,
        ObserveOnlyCandidateExposer,
    )
    from .candidate_generation import (
        CandidateGenerationResult,
        ObserveOnlyCandidateGenerator,
    )
    from .candidate_scoring import (
        CandidateScoringResult,
        ObserveOnlyCandidateScorer,
    )
    from .interfaces import (
        CandidateExposer,
        CandidateGenerator,
        CandidateScorer,
        LayoutRegionAnalyzer,
        SemanticExtractionInputAdapter,
        SemanticLayoutEnricher,
        SemanticDeltaComparator,
        SemanticStateBuilder,
        TextExtractionAdapter,
        TextExtractionBackend,
    )
    from .layout import SemanticLayoutTree, SemanticNode
    from .layout_region_analysis import (
        GeometricLayoutRegionAnalyzer,
        LayoutRegionAnalysisResult,
    )
    from .ocr import (
        PreparedSemanticTextExtractionAdapter,
        TextExtractionRegionRequest,
        TextExtractionRequest,
        TextExtractionResponse,
        TextExtractionResponseStatus,
        TextExtractionResult,
    )
    from .ocr_rapidocr import RapidOcrTextExtractionBackend
    from .ontology import (
        CandidateOntologyCarrier,
        CandidateProvenanceRecord,
        CandidateResolverReadiness,
        CandidateResolverReadinessReason,
        CandidateResolverReadinessStatus,
        CandidateSelectionRiskLevel,
        SemanticCandidateSourceType,
        evaluate_candidate_resolver_readiness,
    )
    from .preparation import (
        FullDesktopCaptureSemanticInputAdapter,
        SemanticExtractionInput,
        SemanticExtractionPreparationResult,
        SemanticSnapshotPreparation,
    )
    from .semantic_delta import (
        ObserveOnlySemanticDeltaComparator,
        SemanticDelta,
        SemanticDeltaCategory,
        SemanticDeltaChange,
        SemanticDeltaChangeType,
        SemanticDeltaResult,
        SemanticDeltaSummary,
    )
    from .semantic_layout_enrichment import (
        OcrAwareSemanticLayoutEnricher,
        SemanticLayoutEnrichmentResult,
    )
    from .state import (
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
