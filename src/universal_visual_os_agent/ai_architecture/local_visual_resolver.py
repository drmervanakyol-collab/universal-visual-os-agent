"""Observe-only local visual resolver scaffolding for future crop-based resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.ai_architecture.contracts import (
    AiArchitectureSignalStatus,
)
from universal_visual_os_agent.ai_architecture.escalation_engine import (
    DeterministicEscalationDecision,
    DeterministicEscalationDisposition,
    DeterministicEscalationReason,
)
from universal_visual_os_agent.ai_architecture.ontology import (
    ObserveOnlySharedOntologyBinder,
    SharedCandidateLabel,
    SharedCandidateOntologyBinding,
    SharedTargetLabel,
)
from universal_visual_os_agent.geometry.models import NormalizedBBox, NormalizedPoint
from universal_visual_os_agent.semantics.candidate_exposure import (
    CandidateExposureView,
    ExposedCandidate,
)
from universal_visual_os_agent.semantics.ontology import CandidateSelectionRiskLevel
from universal_visual_os_agent.semantics.state import SemanticCandidate, SemanticStateSnapshot


class LocalVisualResolverTaskType(StrEnum):
    """Supported future local visual resolver task types."""

    choose_candidate = "choose_candidate"
    classify_region = "classify_region"
    confirm_ui_role = "confirm_ui_role"


class LocalVisualResolverOutcome(StrEnum):
    """Stable non-executing resolver outcomes."""

    resolved = "resolved"
    unresolved = "unresolved"
    unknown = "unknown"


class LocalVisualResolverRationaleCode(StrEnum):
    """Stable structured rationale codes for resolver responses."""

    shortlist_disambiguation = "shortlist_disambiguation"
    constrained_label_match = "constrained_label_match"
    expected_role_confirmed = "expected_role_confirmed"
    conflicting_signals = "conflicting_signals"
    insufficient_context = "insufficient_context"
    unresolved_shortlist = "unresolved_shortlist"
    unknown = "unknown"


@dataclass(slots=True, frozen=True, kw_only=True)
class LocalVisualResolverCropReference:
    """Compact crop/reference metadata for one shortlisted candidate."""

    crop_id: str
    candidate_id: str
    snapshot_id: str
    bounds: NormalizedBBox
    center: NormalizedPoint
    source_layout_region_id: str | None = None
    source_text_region_id: str | None = None
    source_text_block_id: str | None = None
    semantic_layout_role: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.crop_id:
            raise ValueError("crop_id must not be empty.")
        if not self.candidate_id:
            raise ValueError("candidate_id must not be empty.")
        if not self.snapshot_id:
            raise ValueError("snapshot_id must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class LocalVisualResolverShortlistEntry:
    """One deterministic candidate option for future local visual resolution."""

    candidate_binding: SharedCandidateOntologyBinding
    crop_reference: LocalVisualResolverCropReference
    rank: int
    visible: bool
    score: float | None = None
    completeness_status: str = "available"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.rank <= 0:
            raise ValueError("rank must be positive.")
        if self.candidate_binding.candidate_id != self.crop_reference.candidate_id:
            raise ValueError("candidate_binding and crop_reference must reference the same candidate_id.")
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0 inclusive.")
        if self.completeness_status not in {"available", "partial"}:
            raise ValueError("completeness_status must be 'available' or 'partial'.")


@dataclass(slots=True, frozen=True, kw_only=True)
class LocalVisualResolverAmbiguityContext:
    """Risk and ambiguity context for future local visual resolution."""

    selection_risk_level: CandidateSelectionRiskLevel | None = None
    disambiguation_needed: bool = False
    requires_local_resolver: bool = False
    source_conflict_present: bool = False
    escalation_disposition: DeterministicEscalationDisposition | None = None
    escalation_reason_codes: tuple[DeterministicEscalationReason, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(slots=True, frozen=True, kw_only=True)
class LocalVisualResolverRequest:
    """Structured non-executing request for a future local visual resolver."""

    request_id: str
    summary: str
    snapshot_id: str
    task_type: LocalVisualResolverTaskType
    candidate_shortlist: tuple[LocalVisualResolverShortlistEntry, ...]
    expected_target_label: SharedTargetLabel = SharedTargetLabel.candidate_center
    allowed_candidate_labels: tuple[SharedCandidateLabel, ...] = ()
    ambiguity_context: LocalVisualResolverAmbiguityContext = field(
        default_factory=LocalVisualResolverAmbiguityContext
    )
    scenario_id: str | None = None
    signal_status: AiArchitectureSignalStatus = AiArchitectureSignalStatus.available
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("request_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.snapshot_id:
            raise ValueError("snapshot_id must not be empty.")
        if not self.candidate_shortlist:
            raise ValueError("candidate_shortlist must not be empty.")
        shortlist_ids = tuple(
            entry.candidate_binding.candidate_id for entry in self.candidate_shortlist
        )
        if len(set(shortlist_ids)) != len(shortlist_ids):
            raise ValueError("candidate_shortlist candidate IDs must be unique.")
        if len(set(self.allowed_candidate_labels)) != len(self.allowed_candidate_labels):
            raise ValueError("allowed_candidate_labels must not contain duplicates.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError(
                "Local visual resolver requests must remain safety-first and non-executing."
            )


@dataclass(slots=True, frozen=True, kw_only=True)
class LocalVisualResolverOutputContract:
    """Typed future local visual resolver output before binding to deterministic state."""

    response_id: str
    request_id: str
    summary: str
    task_type: LocalVisualResolverTaskType
    outcome: LocalVisualResolverOutcome
    rationale_code: LocalVisualResolverRationaleCode
    selected_candidate_id: str | None = None
    selected_label: SharedCandidateLabel | None = None
    confidence: float | None = None
    need_more_context: bool = False
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.response_id:
            raise ValueError("response_id must not be empty.")
        if not self.request_id:
            raise ValueError("request_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")
        if self.outcome is LocalVisualResolverOutcome.resolved:
            if self.selected_candidate_id is None:
                raise ValueError("Resolved resolver outputs must include selected_candidate_id.")
            if self.confidence is None:
                raise ValueError("Resolved resolver outputs must include confidence.")
        if self.need_more_context and self.outcome is LocalVisualResolverOutcome.resolved:
            raise ValueError("need_more_context cannot be true for a resolved output.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError(
                "Local visual resolver output contracts must remain safety-first and non-executing."
            )


@dataclass(slots=True, frozen=True, kw_only=True)
class LocalVisualResolverResponse:
    """Bound future local visual resolver output grounded in deterministic state."""

    response_id: str
    request_id: str
    task_type: LocalVisualResolverTaskType
    outcome: LocalVisualResolverOutcome
    rationale_code: LocalVisualResolverRationaleCode
    summary: str
    selected_candidate_id: str | None = None
    selected_candidate_binding: SharedCandidateOntologyBinding | None = None
    selected_crop_reference: LocalVisualResolverCropReference | None = None
    selected_label: SharedCandidateLabel | None = None
    confidence: float | None = None
    need_more_context: bool = False
    signal_status: AiArchitectureSignalStatus = AiArchitectureSignalStatus.available
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.response_id:
            raise ValueError("response_id must not be empty.")
        if not self.request_id:
            raise ValueError("request_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")
        if self.selected_candidate_id is not None:
            if self.selected_candidate_binding is None or self.selected_crop_reference is None:
                raise ValueError(
                    "selected_candidate_binding and selected_crop_reference are required when selected_candidate_id is set."
                )
            if self.selected_candidate_binding.candidate_id != self.selected_candidate_id:
                raise ValueError("selected_candidate_binding must match selected_candidate_id.")
            if self.selected_crop_reference.candidate_id != self.selected_candidate_id:
                raise ValueError("selected_crop_reference must match selected_candidate_id.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError(
                "Local visual resolver responses must remain safety-first and non-executing."
            )


@dataclass(slots=True, frozen=True, kw_only=True)
class LocalVisualResolverRequestBuildResult:
    """Failure-safe local visual resolver request construction result."""

    scaffolder_name: str
    success: bool
    request: LocalVisualResolverRequest | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scaffolder_name:
            raise ValueError("scaffolder_name must not be empty.")
        if self.success and self.request is None:
            raise ValueError("Successful request build results must include request.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed request build results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful request build results must not include error details.")
        if not self.success and self.request is not None:
            raise ValueError("Failed request build results must not include request.")

    @classmethod
    def ok(
        cls,
        *,
        scaffolder_name: str,
        request: LocalVisualResolverRequest,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            scaffolder_name=scaffolder_name,
            success=True,
            request=request,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        scaffolder_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            scaffolder_name=scaffolder_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class LocalVisualResolverResponseBindResult:
    """Failure-safe local visual resolver response binding result."""

    scaffolder_name: str
    success: bool
    response: LocalVisualResolverResponse | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scaffolder_name:
            raise ValueError("scaffolder_name must not be empty.")
        if self.success and self.response is None:
            raise ValueError("Successful response bind results must include response.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed response bind results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful response bind results must not include error details.")
        if not self.success and self.response is not None:
            raise ValueError("Failed response bind results must not include response.")

    @classmethod
    def ok(
        cls,
        *,
        scaffolder_name: str,
        response: LocalVisualResolverResponse,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            scaffolder_name=scaffolder_name,
            success=True,
            response=response,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        scaffolder_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            scaffolder_name=scaffolder_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


class ObserveOnlyLocalVisualResolverScaffolder:
    """Build and bind typed local visual resolver scaffolding without model execution."""

    scaffolder_name = "ObserveOnlyLocalVisualResolverScaffolder"

    def __init__(self, *, ontology_binder: ObserveOnlySharedOntologyBinder | None = None) -> None:
        self._ontology_binder = (
            ObserveOnlySharedOntologyBinder() if ontology_binder is None else ontology_binder
        )

    def build_request(
        self,
        snapshot: SemanticStateSnapshot,
        exposure_view: CandidateExposureView,
        *,
        candidate_ids: tuple[str, ...],
        summary: str,
        request_id: str,
        task_type: LocalVisualResolverTaskType = LocalVisualResolverTaskType.choose_candidate,
        expected_target_label: SharedTargetLabel = SharedTargetLabel.candidate_center,
        allowed_candidate_labels: tuple[SharedCandidateLabel, ...] = (),
        escalation_decision: DeterministicEscalationDecision | None = None,
        scenario_id: str | None = None,
    ) -> LocalVisualResolverRequestBuildResult:
        if exposure_view.snapshot_id != snapshot.snapshot_id:
            return LocalVisualResolverRequestBuildResult.failure(
                scaffolder_name=self.scaffolder_name,
                error_code="local_visual_resolver_request_snapshot_mismatch",
                error_message=(
                    "Exposure view must come from the same semantic snapshot as the local visual resolver request."
                ),
                details={
                    "snapshot_id": snapshot.snapshot_id,
                    "exposure_snapshot_id": exposure_view.snapshot_id,
                },
            )
        shortlist_candidate_ids = tuple(dict.fromkeys(candidate_ids))
        if not shortlist_candidate_ids:
            return LocalVisualResolverRequestBuildResult.failure(
                scaffolder_name=self.scaffolder_name,
                error_code="local_visual_resolver_request_empty_shortlist",
                error_message="Local visual resolver requests require at least one shortlist candidate.",
            )
        try:
            task_validation_error = _validate_task_constraints(
                task_type=task_type,
                allowed_candidate_labels=allowed_candidate_labels,
            )
            if task_validation_error is not None:
                return LocalVisualResolverRequestBuildResult.failure(
                    scaffolder_name=self.scaffolder_name,
                    error_code="local_visual_resolver_request_task_constraint",
                    error_message=task_validation_error,
                    details={
                        "task_type": task_type.value,
                        "allowed_candidate_labels": tuple(
                            label.value for label in allowed_candidate_labels
                        ),
                    },
                )

            shortlist_entries: list[LocalVisualResolverShortlistEntry] = []
            partial_candidate_ids: list[str] = []
            shortlist_labels: list[SharedCandidateLabel] = []
            for rank, candidate_id in enumerate(shortlist_candidate_ids, start=1):
                exposed_candidate = _find_exposed_candidate(exposure_view, candidate_id)
                if exposed_candidate is None:
                    return LocalVisualResolverRequestBuildResult.failure(
                        scaffolder_name=self.scaffolder_name,
                        error_code="local_visual_resolver_request_candidate_unavailable",
                        error_message=(
                            f"Shortlist candidate '{candidate_id}' is not available in the current exposure view."
                        ),
                        details={
                            "candidate_id": candidate_id,
                            "available_candidate_ids": tuple(
                                candidate.candidate_id for candidate in exposure_view.candidates
                            ),
                        },
                    )
                semantic_candidate = snapshot.get_candidate(candidate_id)
                if semantic_candidate is None:
                    return LocalVisualResolverRequestBuildResult.failure(
                        scaffolder_name=self.scaffolder_name,
                        error_code="local_visual_resolver_request_candidate_missing_from_snapshot",
                        error_message=(
                            f"Shortlist candidate '{candidate_id}' is not present in the semantic snapshot."
                        ),
                    )
                entry = self._build_shortlist_entry(
                    snapshot=snapshot,
                    semantic_candidate=semantic_candidate,
                    exposed_candidate=exposed_candidate,
                    rank=rank,
                )
                shortlist_entries.append(entry)
                if entry.completeness_status != "available":
                    partial_candidate_ids.append(candidate_id)
                if entry.candidate_binding.shared_candidate_label is not None:
                    shortlist_labels.append(entry.candidate_binding.shared_candidate_label)

            if allowed_candidate_labels and not any(
                label in allowed_candidate_labels for label in shortlist_labels
            ):
                return LocalVisualResolverRequestBuildResult.failure(
                    scaffolder_name=self.scaffolder_name,
                    error_code="local_visual_resolver_request_label_conflict",
                    error_message=(
                        "Resolver label constraints do not overlap with the deterministic shortlist labels."
                    ),
                    details={
                        "allowed_candidate_labels": tuple(
                            label.value for label in allowed_candidate_labels
                        ),
                        "shortlist_labels": tuple(label.value for label in shortlist_labels),
                    },
                )

            request = LocalVisualResolverRequest(
                request_id=request_id,
                summary=summary,
                snapshot_id=snapshot.snapshot_id,
                task_type=task_type,
                candidate_shortlist=tuple(shortlist_entries),
                expected_target_label=expected_target_label,
                allowed_candidate_labels=allowed_candidate_labels,
                ambiguity_context=_build_ambiguity_context(
                    shortlist_entries=tuple(shortlist_entries),
                    escalation_decision=escalation_decision,
                ),
                scenario_id=scenario_id,
                signal_status=_request_signal_status(
                    exposure_view_signal_status=exposure_view.signal_status,
                    partial_candidate_ids=tuple(partial_candidate_ids),
                ),
                metadata={
                    "shortlist_candidate_ids": shortlist_candidate_ids,
                    "partial_candidate_ids": tuple(partial_candidate_ids),
                    "shortlist_count": len(shortlist_entries),
                    "expected_target_label": expected_target_label.value,
                    "allowed_candidate_labels": tuple(
                        label.value for label in allowed_candidate_labels
                    ),
                    "task_type": task_type.value,
                    "scenario_id": scenario_id,
                    "triggering_escalation_disposition": (
                        None
                        if escalation_decision is None
                        else escalation_decision.disposition.value
                    ),
                    "observe_only": True,
                    "read_only": True,
                    "non_executing": True,
                },
            )
        except Exception as exc:  # noqa: BLE001 - scaffolding must remain failure-safe
            return LocalVisualResolverRequestBuildResult.failure(
                scaffolder_name=self.scaffolder_name,
                error_code="local_visual_resolver_request_build_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return LocalVisualResolverRequestBuildResult.ok(
            scaffolder_name=self.scaffolder_name,
            request=request,
            details={
                "signal_status": request.signal_status.value,
                "shortlist_count": len(request.candidate_shortlist),
            },
        )

    def bind_response(
        self,
        request: LocalVisualResolverRequest,
        *,
        contract: LocalVisualResolverOutputContract,
    ) -> LocalVisualResolverResponseBindResult:
        try:
            if contract.request_id != request.request_id:
                return LocalVisualResolverResponseBindResult.failure(
                    scaffolder_name=self.scaffolder_name,
                    error_code="local_visual_resolver_response_request_mismatch",
                    error_message="Resolver output request_id did not match the originating request.",
                    details={
                        "request_id": request.request_id,
                        "contract_request_id": contract.request_id,
                    },
                )
            if contract.task_type is not request.task_type:
                return LocalVisualResolverResponseBindResult.failure(
                    scaffolder_name=self.scaffolder_name,
                    error_code="local_visual_resolver_response_task_mismatch",
                    error_message="Resolver output task_type did not match the originating request.",
                    details={
                        "request_task_type": request.task_type.value,
                        "contract_task_type": contract.task_type.value,
                    },
                )

            selected_entry: LocalVisualResolverShortlistEntry | None = None
            selected_label = contract.selected_label
            if contract.outcome is LocalVisualResolverOutcome.resolved:
                if contract.selected_candidate_id is None:
                    return LocalVisualResolverResponseBindResult.failure(
                        scaffolder_name=self.scaffolder_name,
                        error_code="local_visual_resolver_response_missing_candidate",
                        error_message="Resolved resolver outputs must include selected_candidate_id.",
                    )
                selected_entry = _find_shortlist_entry(request, contract.selected_candidate_id)
                if selected_entry is None:
                    return LocalVisualResolverResponseBindResult.failure(
                        scaffolder_name=self.scaffolder_name,
                        error_code="local_visual_resolver_response_candidate_unavailable",
                        error_message=(
                            f"Resolved candidate '{contract.selected_candidate_id}' is not present in the request shortlist."
                        ),
                        details={
                            "selected_candidate_id": contract.selected_candidate_id,
                            "shortlist_candidate_ids": tuple(
                                entry.candidate_binding.candidate_id
                                for entry in request.candidate_shortlist
                            ),
                        },
                    )
                if selected_label is None:
                    selected_label = selected_entry.candidate_binding.shared_candidate_label
                if (
                    selected_label is not None
                    and request.allowed_candidate_labels
                    and selected_label not in request.allowed_candidate_labels
                ):
                    return LocalVisualResolverResponseBindResult.failure(
                        scaffolder_name=self.scaffolder_name,
                        error_code="local_visual_resolver_response_label_conflict",
                        error_message="Resolved label is outside the allowed resolver label set.",
                        details={
                            "selected_label": selected_label.value,
                            "allowed_candidate_labels": tuple(
                                label.value for label in request.allowed_candidate_labels
                            ),
                        },
                    )
                binding_label = selected_entry.candidate_binding.shared_candidate_label
                if (
                    selected_label is not None
                    and binding_label is not None
                    and selected_label is not binding_label
                ):
                    return LocalVisualResolverResponseBindResult.failure(
                        scaffolder_name=self.scaffolder_name,
                        error_code="local_visual_resolver_response_binding_label_mismatch",
                        error_message="Resolved label did not match the deterministic shortlist binding.",
                        details={
                            "selected_label": selected_label.value,
                            "binding_label": binding_label.value,
                        },
                    )
            else:
                if contract.selected_candidate_id is not None or contract.selected_label is not None:
                    return LocalVisualResolverResponseBindResult.failure(
                        scaffolder_name=self.scaffolder_name,
                        error_code="local_visual_resolver_response_unresolved_selection",
                        error_message=(
                            "Unresolved or unknown resolver outputs must not select a candidate or label."
                        ),
                    )

            response = LocalVisualResolverResponse(
                response_id=contract.response_id,
                request_id=request.request_id,
                task_type=request.task_type,
                outcome=contract.outcome,
                rationale_code=contract.rationale_code,
                summary=contract.summary,
                selected_candidate_id=(
                    None if selected_entry is None else selected_entry.candidate_binding.candidate_id
                ),
                selected_candidate_binding=(
                    None if selected_entry is None else selected_entry.candidate_binding
                ),
                selected_crop_reference=(
                    None if selected_entry is None else selected_entry.crop_reference
                ),
                selected_label=selected_label,
                confidence=contract.confidence,
                need_more_context=contract.need_more_context,
                signal_status=_response_signal_status(
                    request_signal_status=request.signal_status,
                    outcome=contract.outcome,
                    need_more_context=contract.need_more_context,
                ),
                metadata={
                    **dict(contract.metadata),
                    "request_task_type": request.task_type.value,
                    "request_expected_target_label": request.expected_target_label.value,
                    "request_allowed_candidate_labels": tuple(
                        label.value for label in request.allowed_candidate_labels
                    ),
                    "selected_candidate_rank": None if selected_entry is None else selected_entry.rank,
                    "observe_only": True,
                    "read_only": True,
                    "non_executing": True,
                },
            )
        except Exception as exc:  # noqa: BLE001 - scaffolding must remain failure-safe
            return LocalVisualResolverResponseBindResult.failure(
                scaffolder_name=self.scaffolder_name,
                error_code="local_visual_resolver_response_bind_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return LocalVisualResolverResponseBindResult.ok(
            scaffolder_name=self.scaffolder_name,
            response=response,
            details={
                "signal_status": response.signal_status.value,
                "outcome": response.outcome.value,
                "need_more_context": response.need_more_context,
            },
        )

    def _build_shortlist_entry(
        self,
        *,
        snapshot: SemanticStateSnapshot,
        semantic_candidate: SemanticCandidate,
        exposed_candidate: ExposedCandidate,
        rank: int,
    ) -> LocalVisualResolverShortlistEntry:
        binding_result = self._ontology_binder.bind_exposed_candidate(exposed_candidate)
        if not binding_result.success or binding_result.binding is None:
            raise ValueError(
                f"Failed to bind shortlist candidate '{exposed_candidate.candidate_id}' to the shared ontology."
            )
        crop_reference = LocalVisualResolverCropReference(
            crop_id=f"{exposed_candidate.candidate_id}:crop_reference",
            candidate_id=semantic_candidate.candidate_id,
            snapshot_id=snapshot.snapshot_id,
            bounds=semantic_candidate.bounds,
            center=_bbox_center(semantic_candidate.bounds),
            source_layout_region_id=exposed_candidate.source_layout_region_id,
            source_text_region_id=exposed_candidate.source_text_region_id,
            source_text_block_id=exposed_candidate.source_text_block_id,
            semantic_layout_role=exposed_candidate.semantic_layout_role,
            metadata={
                "candidate_rank": exposed_candidate.rank,
                "candidate_visibility": exposed_candidate.visible,
                "candidate_score": exposed_candidate.score,
            },
        )
        completeness_status = (
            "partial"
            if (
                binding_result.binding.completeness_status != "available"
                or exposed_candidate.completeness_status != "available"
            )
            else "available"
        )
        return LocalVisualResolverShortlistEntry(
            candidate_binding=binding_result.binding,
            crop_reference=crop_reference,
            rank=rank,
            visible=exposed_candidate.visible,
            score=exposed_candidate.score,
            completeness_status=completeness_status,
            metadata={
                **dict(exposed_candidate.metadata),
                "semantic_candidate_role": semantic_candidate.role,
                "semantic_candidate_visible": semantic_candidate.visible,
            },
        )


def _validate_task_constraints(
    *,
    task_type: LocalVisualResolverTaskType,
    allowed_candidate_labels: tuple[SharedCandidateLabel, ...],
) -> str | None:
    if task_type is LocalVisualResolverTaskType.classify_region and not allowed_candidate_labels:
        return "classify_region requests require a constrained allowed_candidate_labels set."
    if task_type is LocalVisualResolverTaskType.confirm_ui_role and len(allowed_candidate_labels) != 1:
        return "confirm_ui_role requests require exactly one allowed_candidate_label."
    return None


def _build_ambiguity_context(
    *,
    shortlist_entries: tuple[LocalVisualResolverShortlistEntry, ...],
    escalation_decision: DeterministicEscalationDecision | None,
) -> LocalVisualResolverAmbiguityContext:
    return LocalVisualResolverAmbiguityContext(
        selection_risk_level=_max_risk_level(
            tuple(entry.candidate_binding.selection_risk_level for entry in shortlist_entries)
        ),
        disambiguation_needed=any(
            entry.candidate_binding.disambiguation_needed for entry in shortlist_entries
        ),
        requires_local_resolver=any(
            entry.candidate_binding.requires_local_resolver for entry in shortlist_entries
        ),
        source_conflict_present=any(
            entry.candidate_binding.source_conflict_present for entry in shortlist_entries
        ),
        escalation_disposition=(
            None if escalation_decision is None else escalation_decision.disposition
        ),
        escalation_reason_codes=(
            () if escalation_decision is None else escalation_decision.reason_codes
        ),
        metadata={
            "shortlist_candidate_ids": tuple(
                entry.candidate_binding.candidate_id for entry in shortlist_entries
            ),
        },
    )


def _max_risk_level(
    levels: tuple[CandidateSelectionRiskLevel | None, ...],
) -> CandidateSelectionRiskLevel | None:
    ranking = {
        CandidateSelectionRiskLevel.low: 1,
        CandidateSelectionRiskLevel.medium: 2,
        CandidateSelectionRiskLevel.high: 3,
    }
    populated = [level for level in levels if level is not None]
    if not populated:
        return None
    return max(populated, key=lambda level: ranking[level])


def _request_signal_status(
    *,
    exposure_view_signal_status: str,
    partial_candidate_ids: tuple[str, ...],
) -> AiArchitectureSignalStatus:
    if exposure_view_signal_status == "partial" or partial_candidate_ids:
        return AiArchitectureSignalStatus.partial
    if exposure_view_signal_status == "absent":
        return AiArchitectureSignalStatus.absent
    return AiArchitectureSignalStatus.available


def _response_signal_status(
    *,
    request_signal_status: AiArchitectureSignalStatus,
    outcome: LocalVisualResolverOutcome,
    need_more_context: bool,
) -> AiArchitectureSignalStatus:
    if request_signal_status is not AiArchitectureSignalStatus.available:
        return AiArchitectureSignalStatus.partial
    if need_more_context or outcome is not LocalVisualResolverOutcome.resolved:
        return AiArchitectureSignalStatus.partial
    return AiArchitectureSignalStatus.available


def _find_exposed_candidate(
    exposure_view: CandidateExposureView,
    candidate_id: str,
) -> ExposedCandidate | None:
    return next(
        (candidate for candidate in exposure_view.candidates if candidate.candidate_id == candidate_id),
        None,
    )


def _find_shortlist_entry(
    request: LocalVisualResolverRequest,
    candidate_id: str,
) -> LocalVisualResolverShortlistEntry | None:
    return next(
        (
            entry
            for entry in request.candidate_shortlist
            if entry.candidate_binding.candidate_id == candidate_id
        ),
        None,
    )


def _bbox_center(bounds: NormalizedBBox) -> NormalizedPoint:
    return NormalizedPoint(
        x=bounds.left + (bounds.width / 2.0),
        y=bounds.top + (bounds.height / 2.0),
    )
