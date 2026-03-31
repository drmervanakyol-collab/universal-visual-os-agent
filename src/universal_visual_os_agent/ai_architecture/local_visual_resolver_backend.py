"""Backend-backed local visual resolver integration for compact ambiguity tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.ai_architecture.local_visual_resolver import (
    LocalVisualResolverOutputContract,
    LocalVisualResolverOutcome,
    LocalVisualResolverRationaleCode,
    LocalVisualResolverRequest,
    LocalVisualResolverResponse,
    LocalVisualResolverResponseBindResult,
    LocalVisualResolverShortlistEntry,
    LocalVisualResolverTaskType,
    ObserveOnlyLocalVisualResolverScaffolder,
)
from universal_visual_os_agent.ai_architecture.escalation_engine import (
    DeterministicEscalationDecision,
)
from universal_visual_os_agent.ai_architecture.ontology import (
    SharedCandidateLabel,
    SharedTargetLabel,
)
from universal_visual_os_agent.semantics.ontology import (
    CandidateResolverReadinessStatus,
    CandidateSelectionRiskLevel,
)
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot
from universal_visual_os_agent.semantics.candidate_exposure import CandidateExposureView


class LocalVisualResolverBackendAvailability(StrEnum):
    """Availability states for the real local visual resolver backend."""

    available = "available"
    unavailable = "unavailable"


@dataclass(slots=True, frozen=True, kw_only=True)
class LocalVisualResolverBackendConfig:
    """Deterministic thresholds for the first local visual resolver backend."""

    choose_candidate_min_confidence: float = 0.80
    classify_region_min_confidence: float = 0.78
    confirm_ui_role_min_confidence: float = 0.82
    decisive_margin_threshold: float = 0.05
    visible_bonus: float = 0.02
    hidden_penalty: float = 0.08
    medium_risk_penalty: float = 0.04
    high_risk_penalty: float = 0.10
    conflicted_readiness_penalty: float = 0.18
    partial_readiness_penalty: float = 0.30
    rank_penalty_step: float = 0.01
    label_match_bonus: float = 0.08
    label_mismatch_penalty: float = 0.25
    availability: LocalVisualResolverBackendAvailability = (
        LocalVisualResolverBackendAvailability.available
    )
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "choose_candidate_min_confidence",
            "classify_region_min_confidence",
            "confirm_ui_role_min_confidence",
            "decisive_margin_threshold",
            "visible_bonus",
            "hidden_penalty",
            "medium_risk_penalty",
            "high_risk_penalty",
            "conflicted_readiness_penalty",
            "partial_readiness_penalty",
            "rank_penalty_step",
            "label_match_bonus",
            "label_mismatch_penalty",
        ):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0 inclusive.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Local visual resolver backend config must remain safety-first.")


@dataclass(slots=True, frozen=True, kw_only=True)
class LocalVisualResolverBackendResult:
    """Failure-safe backend evaluation result."""

    backend_name: str
    success: bool
    availability: LocalVisualResolverBackendAvailability
    output_contract: LocalVisualResolverOutputContract | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.backend_name:
            raise ValueError("backend_name must not be empty.")
        if self.success and self.output_contract is None:
            raise ValueError("Successful backend results must include output_contract.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed backend results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful backend results must not include error details.")
        if not self.success and self.output_contract is not None:
            raise ValueError("Failed backend results must not include output_contract.")

    @classmethod
    def ok(
        cls,
        *,
        backend_name: str,
        availability: LocalVisualResolverBackendAvailability,
        output_contract: LocalVisualResolverOutputContract,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            backend_name=backend_name,
            success=True,
            availability=availability,
            output_contract=output_contract,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        backend_name: str,
        availability: LocalVisualResolverBackendAvailability,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            backend_name=backend_name,
            success=False,
            availability=availability,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class LocalVisualResolverExecutionResult:
    """End-to-end result for scaffolded request -> backend -> bound response."""

    resolver_name: str
    success: bool
    availability: LocalVisualResolverBackendAvailability
    request: LocalVisualResolverRequest | None = None
    backend_result: LocalVisualResolverBackendResult | None = None
    response_bind_result: LocalVisualResolverResponseBindResult | None = None
    response: LocalVisualResolverResponse | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.resolver_name:
            raise ValueError("resolver_name must not be empty.")
        if self.success and (
            self.request is None
            or self.backend_result is None
            or self.response_bind_result is None
            or self.response is None
        ):
            raise ValueError(
                "Successful execution results must include request, backend_result, response_bind_result, and response."
            )
        if not self.success and self.error_code is None:
            raise ValueError("Failed execution results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful execution results must not include error details.")

    @classmethod
    def ok(
        cls,
        *,
        resolver_name: str,
        availability: LocalVisualResolverBackendAvailability,
        request: LocalVisualResolverRequest,
        backend_result: LocalVisualResolverBackendResult,
        response_bind_result: LocalVisualResolverResponseBindResult,
        response: LocalVisualResolverResponse,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            resolver_name=resolver_name,
            success=True,
            availability=availability,
            request=request,
            backend_result=backend_result,
            response_bind_result=response_bind_result,
            response=response,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        resolver_name: str,
        availability: LocalVisualResolverBackendAvailability,
        error_code: str,
        error_message: str,
        request: LocalVisualResolverRequest | None = None,
        backend_result: LocalVisualResolverBackendResult | None = None,
        response_bind_result: LocalVisualResolverResponseBindResult | None = None,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            resolver_name=resolver_name,
            success=False,
            availability=availability,
            request=request,
            backend_result=backend_result,
            response_bind_result=response_bind_result,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


class ObserveOnlyMetadataLocalVisualResolverBackend:
    """Resolve compact local-resolver requests from shortlist metadata only."""

    backend_name = "ObserveOnlyMetadataLocalVisualResolverBackend"

    def __init__(
        self,
        *,
        config: LocalVisualResolverBackendConfig | None = None,
    ) -> None:
        self._config = LocalVisualResolverBackendConfig() if config is None else config

    @property
    def availability(self) -> LocalVisualResolverBackendAvailability:
        """Return the explicit backend availability state."""

        return self._config.availability

    def resolve(
        self,
        request: LocalVisualResolverRequest,
    ) -> LocalVisualResolverBackendResult:
        if self._config.availability is not LocalVisualResolverBackendAvailability.available:
            return LocalVisualResolverBackendResult.failure(
                backend_name=self.backend_name,
                availability=self._config.availability,
                error_code="local_visual_resolver_backend_unavailable",
                error_message="The local visual resolver backend is unavailable.",
                details={
                    "request_id": request.request_id,
                    "task_type": request.task_type.value,
                },
            )

        try:
            if request.signal_status is not request.signal_status.available:
                output_contract = self._make_output_contract(
                    request=request,
                    outcome=LocalVisualResolverOutcome.unresolved,
                    rationale_code=LocalVisualResolverRationaleCode.insufficient_context,
                    summary="Resolver request metadata is partial and needs more context.",
                    need_more_context=True,
                    metadata={"failure_mode": "partial_request_signal"},
                )
                return LocalVisualResolverBackendResult.ok(
                    backend_name=self.backend_name,
                    availability=self._config.availability,
                    output_contract=output_contract,
                    details={"outcome": output_contract.outcome.value},
                )

            if request.ambiguity_context.source_conflict_present:
                output_contract = self._make_output_contract(
                    request=request,
                    outcome=LocalVisualResolverOutcome.unresolved,
                    rationale_code=LocalVisualResolverRationaleCode.conflicting_signals,
                    summary="Resolver request carries source conflicts and needs more context.",
                    need_more_context=True,
                    metadata={"failure_mode": "source_conflict_present"},
                )
                return LocalVisualResolverBackendResult.ok(
                    backend_name=self.backend_name,
                    availability=self._config.availability,
                    output_contract=output_contract,
                    details={"outcome": output_contract.outcome.value},
                )

            scored_entries = tuple(
                sorted(
                    (
                        _ScoredShortlistEntry(
                            entry=entry,
                            resolution_confidence=self._score_entry(request, entry),
                        )
                        for entry in request.candidate_shortlist
                    ),
                    key=lambda item: (
                        -item.resolution_confidence,
                        item.entry.rank,
                        item.entry.candidate_binding.candidate_id,
                    ),
                )
            )
            if not scored_entries:
                return LocalVisualResolverBackendResult.failure(
                    backend_name=self.backend_name,
                    availability=self._config.availability,
                    error_code="local_visual_resolver_backend_empty_shortlist",
                    error_message="Local visual resolver requests require at least one shortlist entry.",
                )

            output_contract = self._resolve_from_scored_entries(
                request=request,
                scored_entries=scored_entries,
            )
        except Exception as exc:  # noqa: BLE001 - backend must remain failure-safe
            return LocalVisualResolverBackendResult.failure(
                backend_name=self.backend_name,
                availability=self._config.availability,
                error_code="local_visual_resolver_backend_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return LocalVisualResolverBackendResult.ok(
            backend_name=self.backend_name,
            availability=self._config.availability,
            output_contract=output_contract,
            details={
                "outcome": output_contract.outcome.value,
                "rationale_code": output_contract.rationale_code.value,
                "need_more_context": output_contract.need_more_context,
            },
        )

    def _resolve_from_scored_entries(
        self,
        *,
        request: LocalVisualResolverRequest,
        scored_entries: tuple["_ScoredShortlistEntry", ...],
    ) -> LocalVisualResolverOutputContract:
        matching_entries = _matching_entries(
            request=request,
            scored_entries=scored_entries,
        )
        top_entry = matching_entries[0] if matching_entries else None
        second_entry = matching_entries[1] if len(matching_entries) > 1 else None
        threshold = self._confidence_threshold_for_task(request.task_type)
        resolution_scores = tuple(
            {
                "candidate_id": item.entry.candidate_binding.candidate_id,
                "candidate_label": item.entry.candidate_binding.candidate_label,
                "shared_candidate_label": (
                    None
                    if item.entry.candidate_binding.shared_candidate_label is None
                    else item.entry.candidate_binding.shared_candidate_label.value
                ),
                "resolution_confidence": item.resolution_confidence,
                "rank": item.entry.rank,
                "visible": item.entry.visible,
                "readiness_status": item.readiness_status.value,
            }
            for item in scored_entries
        )

        if not matching_entries:
            return self._make_output_contract(
                request=request,
                outcome=LocalVisualResolverOutcome.unknown,
                rationale_code=LocalVisualResolverRationaleCode.unknown,
                summary="Resolver backend could not find a shortlist candidate matching the constrained label set.",
                metadata={
                    "resolution_scores": resolution_scores,
                    "confidence_threshold": threshold,
                    "failure_mode": "no_matching_candidate_label",
                },
            )

        if top_entry is None:
            return self._make_output_contract(
                request=request,
                outcome=LocalVisualResolverOutcome.unknown,
                rationale_code=LocalVisualResolverRationaleCode.unknown,
                summary="Resolver backend could not rank the shortlist safely.",
                metadata={
                    "resolution_scores": resolution_scores,
                    "confidence_threshold": threshold,
                    "failure_mode": "missing_top_candidate",
                },
            )

        if top_entry.readiness_status is CandidateResolverReadinessStatus.partial:
            return self._make_output_contract(
                request=request,
                outcome=LocalVisualResolverOutcome.unresolved,
                rationale_code=LocalVisualResolverRationaleCode.insufficient_context,
                summary="Resolver backend needs more context because shortlisted metadata is partial.",
                need_more_context=True,
                metadata={
                    "resolution_scores": resolution_scores,
                    "confidence_threshold": threshold,
                    "failure_mode": "partial_shortlist_entry",
                },
            )

        margin = (
            top_entry.resolution_confidence - second_entry.resolution_confidence
            if second_entry is not None
            else 1.0
        )
        if top_entry.resolution_confidence < threshold:
            return self._make_output_contract(
                request=request,
                outcome=LocalVisualResolverOutcome.unknown,
                rationale_code=LocalVisualResolverRationaleCode.unknown,
                summary="Resolver backend confidence stayed below the task threshold.",
                metadata={
                    "resolution_scores": resolution_scores,
                    "confidence_threshold": threshold,
                    "top_candidate_id": top_entry.entry.candidate_binding.candidate_id,
                    "failure_mode": "confidence_below_threshold",
                },
            )
        if second_entry is not None and margin < self._config.decisive_margin_threshold:
            return self._make_output_contract(
                request=request,
                outcome=LocalVisualResolverOutcome.unresolved,
                rationale_code=LocalVisualResolverRationaleCode.unresolved_shortlist,
                summary="Resolver backend found multiple plausible shortlist candidates and needs more context.",
                need_more_context=True,
                metadata={
                    "resolution_scores": resolution_scores,
                    "confidence_threshold": threshold,
                    "decisive_margin_threshold": self._config.decisive_margin_threshold,
                    "confidence_margin": margin,
                    "failure_mode": "shortlist_too_close",
                },
            )

        selected_label = top_entry.entry.candidate_binding.shared_candidate_label
        if request.task_type is LocalVisualResolverTaskType.choose_candidate:
            rationale_code = LocalVisualResolverRationaleCode.shortlist_disambiguation
            summary = "Resolver backend selected the most plausible shortlist candidate."
        elif request.task_type is LocalVisualResolverTaskType.classify_region:
            rationale_code = LocalVisualResolverRationaleCode.constrained_label_match
            summary = "Resolver backend matched the crop to the constrained shared label set."
        else:
            rationale_code = LocalVisualResolverRationaleCode.expected_role_confirmed
            summary = "Resolver backend confirmed the expected UI role for the shortlisted region."

        return self._make_output_contract(
            request=request,
            outcome=LocalVisualResolverOutcome.resolved,
            rationale_code=rationale_code,
            summary=summary,
            selected_candidate_id=top_entry.entry.candidate_binding.candidate_id,
            selected_label=selected_label,
            confidence=top_entry.resolution_confidence,
            metadata={
                "resolution_scores": resolution_scores,
                "confidence_threshold": threshold,
                "decisive_margin_threshold": self._config.decisive_margin_threshold,
                "confidence_margin": margin,
                "selected_candidate_rank": top_entry.entry.rank,
                "backend_kind": "metadata_heuristic",
                "boundary_validation_required": True,
                "tool_boundary_required": True,
            },
        )

    def _score_entry(
        self,
        request: LocalVisualResolverRequest,
        entry: LocalVisualResolverShortlistEntry,
    ) -> float:
        score = (
            entry.score
            if entry.score is not None
            else (entry.candidate_binding.confidence or 0.0)
        )
        readiness_status = _readiness_status_from_entry(entry)
        if readiness_status is CandidateResolverReadinessStatus.partial:
            score -= self._config.partial_readiness_penalty
        elif readiness_status is CandidateResolverReadinessStatus.conflicted:
            score -= self._config.conflicted_readiness_penalty

        if entry.visible:
            score += self._config.visible_bonus
        else:
            score -= self._config.hidden_penalty

        if entry.candidate_binding.selection_risk_level is CandidateSelectionRiskLevel.medium:
            score -= self._config.medium_risk_penalty
        elif entry.candidate_binding.selection_risk_level is CandidateSelectionRiskLevel.high:
            score -= self._config.high_risk_penalty

        score -= self._config.rank_penalty_step * float(max(entry.rank - 1, 0))

        shared_label = entry.candidate_binding.shared_candidate_label
        if request.allowed_candidate_labels:
            if shared_label in request.allowed_candidate_labels:
                score += self._config.label_match_bonus
            else:
                score -= self._config.label_mismatch_penalty

        return max(0.0, min(1.0, round(score, 6)))

    def _confidence_threshold_for_task(
        self,
        task_type: LocalVisualResolverTaskType,
    ) -> float:
        if task_type is LocalVisualResolverTaskType.choose_candidate:
            return self._config.choose_candidate_min_confidence
        if task_type is LocalVisualResolverTaskType.classify_region:
            return self._config.classify_region_min_confidence
        return self._config.confirm_ui_role_min_confidence

    def _make_output_contract(
        self,
        *,
        request: LocalVisualResolverRequest,
        outcome: LocalVisualResolverOutcome,
        rationale_code: LocalVisualResolverRationaleCode,
        summary: str,
        selected_candidate_id: str | None = None,
        selected_label: SharedCandidateLabel | None = None,
        confidence: float | None = None,
        need_more_context: bool = False,
        metadata: Mapping[str, object] | None = None,
    ) -> LocalVisualResolverOutputContract:
        return LocalVisualResolverOutputContract(
            response_id=f"{request.request_id}:backend_response",
            request_id=request.request_id,
            summary=summary,
            task_type=request.task_type,
            outcome=outcome,
            rationale_code=rationale_code,
            selected_candidate_id=selected_candidate_id,
            selected_label=selected_label,
            confidence=confidence,
            need_more_context=need_more_context,
            metadata={
                "backend_name": self.backend_name,
                "backend_availability": self._config.availability.value,
                "request_expected_target_label": request.expected_target_label.value,
                "request_task_type": request.task_type.value,
                "observe_only": True,
                "read_only": True,
                "non_executing": True,
                **({} if metadata is None else dict(metadata)),
            },
        )


class ObserveOnlyBackendBackedLocalVisualResolver:
    """Run scaffold build, backend resolution, and response binding safely."""

    resolver_name = "ObserveOnlyBackendBackedLocalVisualResolver"

    def __init__(
        self,
        *,
        scaffolder: ObserveOnlyLocalVisualResolverScaffolder | None = None,
        backend: ObserveOnlyMetadataLocalVisualResolverBackend | None = None,
    ) -> None:
        self._scaffolder = (
            ObserveOnlyLocalVisualResolverScaffolder()
            if scaffolder is None
            else scaffolder
        )
        self._backend = (
            ObserveOnlyMetadataLocalVisualResolverBackend()
            if backend is None
            else backend
        )

    def resolve(
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
    ) -> LocalVisualResolverExecutionResult:
        try:
            request_result = self._scaffolder.build_request(
                snapshot,
                exposure_view,
                candidate_ids=candidate_ids,
                summary=summary,
                request_id=request_id,
                task_type=task_type,
                expected_target_label=expected_target_label,
                allowed_candidate_labels=allowed_candidate_labels,
                escalation_decision=escalation_decision,
                scenario_id=scenario_id,
            )
        except Exception as exc:  # noqa: BLE001 - wrapper must remain failure-safe
            return LocalVisualResolverExecutionResult.failure(
                resolver_name=self.resolver_name,
                availability=self._backend.availability,
                error_code="local_visual_resolver_request_build_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        if not request_result.success or request_result.request is None:
            return LocalVisualResolverExecutionResult.failure(
                resolver_name=self.resolver_name,
                availability=self._backend.availability,
                error_code=(
                    "local_visual_resolver_request_build_failed"
                    if request_result.error_code is None
                    else request_result.error_code
                ),
                error_message=(
                    "Local visual resolver request construction failed."
                    if request_result.error_message is None
                    else request_result.error_message
                ),
                details=dict(request_result.details),
            )
        return self.resolve_request(request_result.request)

    def resolve_request(
        self,
        request: LocalVisualResolverRequest,
    ) -> LocalVisualResolverExecutionResult:
        try:
            backend_result = self._backend.resolve(request)
        except Exception as exc:  # noqa: BLE001 - wrapper must remain failure-safe
            return LocalVisualResolverExecutionResult.failure(
                resolver_name=self.resolver_name,
                availability=self._backend.availability,
                request=request,
                error_code="local_visual_resolver_backend_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        if not backend_result.success or backend_result.output_contract is None:
            return LocalVisualResolverExecutionResult.failure(
                resolver_name=self.resolver_name,
                availability=backend_result.availability,
                request=request,
                backend_result=backend_result,
                error_code=(
                    "local_visual_resolver_backend_failed"
                    if backend_result.error_code is None
                    else backend_result.error_code
                ),
                error_message=(
                    "Local visual resolver backend failed."
                    if backend_result.error_message is None
                    else backend_result.error_message
                ),
                details=dict(backend_result.details),
            )

        try:
            response_bind_result = self._scaffolder.bind_response(
                request,
                contract=backend_result.output_contract,
            )
        except Exception as exc:  # noqa: BLE001 - wrapper must remain failure-safe
            return LocalVisualResolverExecutionResult.failure(
                resolver_name=self.resolver_name,
                availability=backend_result.availability,
                request=request,
                backend_result=backend_result,
                error_code="local_visual_resolver_response_bind_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        if not response_bind_result.success or response_bind_result.response is None:
            return LocalVisualResolverExecutionResult.failure(
                resolver_name=self.resolver_name,
                availability=backend_result.availability,
                request=request,
                backend_result=backend_result,
                response_bind_result=response_bind_result,
                error_code=(
                    "local_visual_resolver_response_bind_failed"
                    if response_bind_result.error_code is None
                    else response_bind_result.error_code
                ),
                error_message=(
                    "Local visual resolver response binding failed."
                    if response_bind_result.error_message is None
                    else response_bind_result.error_message
                ),
                details=dict(response_bind_result.details),
            )

        return LocalVisualResolverExecutionResult.ok(
            resolver_name=self.resolver_name,
            availability=backend_result.availability,
            request=request,
            backend_result=backend_result,
            response_bind_result=response_bind_result,
            response=response_bind_result.response,
            details={
                "task_type": request.task_type.value,
                "outcome": response_bind_result.response.outcome.value,
                "signal_status": response_bind_result.response.signal_status.value,
                "need_more_context": response_bind_result.response.need_more_context,
            },
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class _ScoredShortlistEntry:
    entry: LocalVisualResolverShortlistEntry
    resolution_confidence: float

    @property
    def readiness_status(self) -> CandidateResolverReadinessStatus:
        return _readiness_status_from_entry(self.entry)


def _matching_entries(
    *,
    request: LocalVisualResolverRequest,
    scored_entries: tuple[_ScoredShortlistEntry, ...],
) -> tuple[_ScoredShortlistEntry, ...]:
    if not request.allowed_candidate_labels:
        return scored_entries
    return tuple(
        item
        for item in scored_entries
        if item.entry.candidate_binding.shared_candidate_label in request.allowed_candidate_labels
    )


def _readiness_status_from_entry(
    entry: LocalVisualResolverShortlistEntry,
) -> CandidateResolverReadinessStatus:
    raw_status = entry.metadata.get("candidate_resolver_readiness_status")
    if isinstance(raw_status, str):
        try:
            return CandidateResolverReadinessStatus(raw_status)
        except ValueError:
            pass
    if entry.completeness_status != "available":
        return CandidateResolverReadinessStatus.partial
    return CandidateResolverReadinessStatus.ready
