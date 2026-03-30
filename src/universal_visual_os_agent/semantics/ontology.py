"""Stable candidate-source ontology models for hybrid semantic perception."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Protocol


class SemanticCandidateSourceType(StrEnum):
    """Dominant source typing for one semantic candidate."""

    ocr = "ocr"
    layout = "layout"
    heuristic = "heuristic"
    visual_model = "visual_model"
    uia = "uia"
    mixed = "mixed"


class CandidateSelectionRiskLevel(StrEnum):
    """Conservative selection risk labels for future resolver and action use."""

    low = "low"
    medium = "medium"
    high = "high"


@dataclass(slots=True, frozen=True, kw_only=True)
class CandidateProvenanceRecord:
    """Structured provenance entry for one candidate source contribution."""

    source_type: SemanticCandidateSourceType
    source_id: str
    source_label: str | None = None
    confidence: float | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("source_id must not be empty.")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")


class CandidateOntologyCarrier(Protocol):
    """Structural interface for objects that expose candidate ontology fields."""

    source_type: SemanticCandidateSourceType | None
    selection_risk_level: CandidateSelectionRiskLevel | None
    disambiguation_needed: bool
    requires_local_resolver: bool
    source_conflict_present: bool
    source_of_truth_priority: tuple[SemanticCandidateSourceType, ...]
    provenance: tuple[CandidateProvenanceRecord, ...]


_SOURCE_PRIORITY_RANK = {
    SemanticCandidateSourceType.uia: 0,
    SemanticCandidateSourceType.visual_model: 1,
    SemanticCandidateSourceType.ocr: 2,
    SemanticCandidateSourceType.layout: 3,
    SemanticCandidateSourceType.heuristic: 4,
    SemanticCandidateSourceType.mixed: 5,
}


def normalize_source_of_truth_priority(
    source_types: tuple[SemanticCandidateSourceType, ...],
) -> tuple[SemanticCandidateSourceType, ...]:
    """Return a deterministic source-of-truth priority ordering."""

    unique_source_types = tuple(dict.fromkeys(source_types))
    return tuple(
        sorted(
            unique_source_types,
            key=lambda source_type: (_SOURCE_PRIORITY_RANK[source_type], source_type.value),
        )
    )


def normalize_provenance(
    provenance: tuple[CandidateProvenanceRecord, ...],
) -> tuple[CandidateProvenanceRecord, ...]:
    """Return provenance entries in deterministic source-priority order."""

    return tuple(
        sorted(
            provenance,
            key=lambda record: (
                _SOURCE_PRIORITY_RANK[record.source_type],
                record.source_id,
                "" if record.source_label is None else record.source_label,
            ),
        )
    )


def candidate_ontology_completeness_status(candidate: CandidateOntologyCarrier) -> str:
    """Return whether explicit ontology metadata is complete enough for downstream use."""

    if candidate.source_type is None:
        return "partial"
    if candidate.selection_risk_level is None:
        return "partial"
    if not candidate.source_of_truth_priority:
        return "partial"
    if not candidate.provenance:
        return "partial"
    return "available"


def provenance_source_types(
    provenance: tuple[CandidateProvenanceRecord, ...],
) -> tuple[SemanticCandidateSourceType, ...]:
    """Return the unique source types present in deterministic provenance order."""

    return tuple(dict.fromkeys(record.source_type for record in normalize_provenance(provenance)))
