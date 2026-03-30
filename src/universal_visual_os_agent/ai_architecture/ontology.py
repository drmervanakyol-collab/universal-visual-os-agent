"""Shared ontology binding for deterministic pipeline, planner, and resolver scaffolding."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.semantics.candidate_exposure import ExposedCandidate
from universal_visual_os_agent.semantics.ontology import (
    CandidateProvenanceRecord,
    CandidateSelectionRiskLevel,
    SemanticCandidateSourceType,
    candidate_ontology_completeness_status,
)
from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
    SemanticCandidateClass,
)


SHARED_AI_ONTOLOGY_VERSION = "shared_ai_ontology_v1"


class SharedCandidateLabel(StrEnum):
    """Stable candidate labels shared across deterministic and future AI layers."""

    button = "button"
    input = "input"
    tab = "tab"
    close = "close"
    popup_dismiss = "popup_dismiss"
    interactive_region = "interactive_region"


class SharedTargetLabel(StrEnum):
    """Stable target labels shared across planner and resolver scaffolding."""

    candidate_center = "candidate_center"
    candidate_point = "candidate_point"


_SHARED_CANDIDATE_LABELS = {
    SemanticCandidateClass.button_like: SharedCandidateLabel.button,
    SemanticCandidateClass.input_like: SharedCandidateLabel.input,
    SemanticCandidateClass.tab_like: SharedCandidateLabel.tab,
    SemanticCandidateClass.close_like: SharedCandidateLabel.close,
    SemanticCandidateClass.popup_dismiss_like: SharedCandidateLabel.popup_dismiss,
    SemanticCandidateClass.interactive_region_like: SharedCandidateLabel.interactive_region,
}


@dataclass(slots=True, frozen=True, kw_only=True)
class SharedCandidateOntologyBinding:
    """Typed shared-ontology view of one deterministic candidate."""

    binding_id: str
    candidate_id: str
    candidate_label: str
    shared_candidate_label: SharedCandidateLabel | None
    deterministic_candidate_class: SemanticCandidateClass | None = None
    confidence: float | None = None
    source_type: SemanticCandidateSourceType | None = None
    selection_risk_level: CandidateSelectionRiskLevel | None = None
    disambiguation_needed: bool = False
    requires_local_resolver: bool = False
    source_conflict_present: bool = False
    source_of_truth_priority: tuple[SemanticCandidateSourceType, ...] = ()
    provenance: tuple[CandidateProvenanceRecord, ...] = ()
    completeness_status: str = "available"
    allowed_target_labels: tuple[SharedTargetLabel, ...] = (
        SharedTargetLabel.candidate_center,
        SharedTargetLabel.candidate_point,
    )
    ontology_version: str = SHARED_AI_ONTOLOGY_VERSION
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.binding_id:
            raise ValueError("binding_id must not be empty.")
        if not self.candidate_id:
            raise ValueError("candidate_id must not be empty.")
        if not self.candidate_label:
            raise ValueError("candidate_label must not be empty.")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")
        if self.completeness_status not in {"available", "partial"}:
            raise ValueError("completeness_status must be available or partial.")
        if not self.allowed_target_labels:
            raise ValueError("allowed_target_labels must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Shared ontology bindings must remain safety-first and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SharedOntologyBindingResult:
    """Failure-safe result for shared ontology binding."""

    binder_name: str
    success: bool
    binding: SharedCandidateOntologyBinding | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.binder_name:
            raise ValueError("binder_name must not be empty.")
        if self.success and self.binding is None:
            raise ValueError("Successful ontology binding must include binding.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed ontology binding must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful ontology binding must not include error details.")
        if not self.success and self.binding is not None:
            raise ValueError("Failed ontology binding must not include binding.")

    @classmethod
    def ok(
        cls,
        *,
        binder_name: str,
        binding: SharedCandidateOntologyBinding,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            binder_name=binder_name,
            success=True,
            binding=binding,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        binder_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            binder_name=binder_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


class ObserveOnlySharedOntologyBinder:
    """Bind deterministic candidates to the shared AI-facing ontology."""

    binder_name = "ObserveOnlySharedOntologyBinder"

    def bind_semantic_candidate(
        self,
        candidate: SemanticCandidate,
    ) -> SharedOntologyBindingResult:
        try:
            binding = self._build_binding(
                candidate_id=candidate.candidate_id,
                candidate_label=candidate.label,
                candidate_class=candidate.candidate_class,
                confidence=candidate.confidence,
                source_type=candidate.source_type,
                selection_risk_level=candidate.selection_risk_level,
                disambiguation_needed=candidate.disambiguation_needed,
                requires_local_resolver=candidate.requires_local_resolver,
                source_conflict_present=candidate.source_conflict_present,
                source_of_truth_priority=candidate.source_of_truth_priority,
                provenance=candidate.provenance,
                completeness_status=candidate_ontology_completeness_status(candidate),
                metadata=dict(candidate.metadata),
            )
        except Exception as exc:  # noqa: BLE001 - binder must remain failure-safe
            return SharedOntologyBindingResult.failure(
                binder_name=self.binder_name,
                error_code="shared_ontology_binding_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return SharedOntologyBindingResult.ok(
            binder_name=self.binder_name,
            binding=binding,
            details={"binding_id": binding.binding_id, "completeness_status": binding.completeness_status},
        )

    def bind_exposed_candidate(
        self,
        candidate: ExposedCandidate,
    ) -> SharedOntologyBindingResult:
        try:
            completeness_status = (
                "partial"
                if candidate.completeness_status != "available"
                or candidate_ontology_completeness_status(candidate) != "available"
                else "available"
            )
            binding = self._build_binding(
                candidate_id=candidate.candidate_id,
                candidate_label=candidate.label,
                candidate_class=candidate.candidate_class,
                confidence=candidate.score,
                source_type=candidate.source_type,
                selection_risk_level=candidate.selection_risk_level,
                disambiguation_needed=candidate.disambiguation_needed,
                requires_local_resolver=candidate.requires_local_resolver,
                source_conflict_present=candidate.source_conflict_present,
                source_of_truth_priority=candidate.source_of_truth_priority,
                provenance=candidate.provenance,
                completeness_status=completeness_status,
                metadata=dict(candidate.metadata),
            )
        except Exception as exc:  # noqa: BLE001 - binder must remain failure-safe
            return SharedOntologyBindingResult.failure(
                binder_name=self.binder_name,
                error_code="shared_ontology_binding_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return SharedOntologyBindingResult.ok(
            binder_name=self.binder_name,
            binding=binding,
            details={"binding_id": binding.binding_id, "completeness_status": binding.completeness_status},
        )

    def _build_binding(
        self,
        *,
        candidate_id: str,
        candidate_label: str,
        candidate_class: SemanticCandidateClass | None,
        confidence: float | None,
        source_type: SemanticCandidateSourceType | None,
        selection_risk_level: CandidateSelectionRiskLevel | None,
        disambiguation_needed: bool,
        requires_local_resolver: bool,
        source_conflict_present: bool,
        source_of_truth_priority: tuple[SemanticCandidateSourceType, ...],
        provenance: tuple[CandidateProvenanceRecord, ...],
        completeness_status: str,
        metadata: Mapping[str, object],
    ) -> SharedCandidateOntologyBinding:
        shared_candidate_label = (
            None if candidate_class is None else _SHARED_CANDIDATE_LABELS.get(candidate_class)
        )
        if shared_candidate_label is None:
            completeness_status = "partial"
        if source_type is None or selection_risk_level is None:
            completeness_status = "partial"
        if not source_of_truth_priority or not provenance:
            completeness_status = "partial"
        return SharedCandidateOntologyBinding(
            binding_id=f"{candidate_id}:shared_ontology",
            candidate_id=candidate_id,
            candidate_label=candidate_label,
            shared_candidate_label=shared_candidate_label,
            deterministic_candidate_class=candidate_class,
            confidence=confidence,
            source_type=source_type,
            selection_risk_level=selection_risk_level,
            disambiguation_needed=disambiguation_needed,
            requires_local_resolver=requires_local_resolver,
            source_conflict_present=source_conflict_present,
            source_of_truth_priority=source_of_truth_priority,
            provenance=provenance,
            completeness_status=completeness_status,
            metadata={
                **dict(metadata),
                "shared_ai_ontology_bound": True,
                "shared_ai_ontology_binder": self.binder_name,
                "shared_ai_ontology_label": (
                    None if shared_candidate_label is None else shared_candidate_label.value
                ),
            },
        )
