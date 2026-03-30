"""Observe-only planner and resolver contract scaffolding for future AI integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.ai_architecture.ontology import (
    SHARED_AI_ONTOLOGY_VERSION,
    ObserveOnlySharedOntologyBinder,
    SharedCandidateOntologyBinding,
    SharedTargetLabel,
)
from universal_visual_os_agent.ai_boundary.models import (
    AiSuggestedActionType,
    CloudPlannerContract,
    LocalVisualResolverContract,
)
from universal_visual_os_agent.geometry.models import NormalizedPoint
from universal_visual_os_agent.semantics.candidate_exposure import (
    CandidateExposureView,
    ExposedCandidate,
)
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot
from universal_visual_os_agent.verification.models import SemanticTransitionExpectation


AI_ARCHITECTURE_SCHEMA_VERSION = "ai_architecture_v1"


class AiArchitectureSignalStatus(StrEnum):
    """Stable completeness signal states for AI-architecture contracts."""

    available = "available"
    partial = "partial"
    absent = "absent"


@dataclass(slots=True, frozen=True, kw_only=True)
class PlannerRequestContract:
    """Structured request scaffold for a future cloud planner."""

    request_id: str
    summary: str
    snapshot_id: str
    candidate_bindings: tuple[SharedCandidateOntologyBinding, ...]
    scenario_id: str | None = None
    expected_transition: SemanticTransitionExpectation | None = None
    allowed_action_types: tuple[AiSuggestedActionType, ...] = (
        AiSuggestedActionType.observe_only,
        AiSuggestedActionType.candidate_select,
    )
    schema_version: str = AI_ARCHITECTURE_SCHEMA_VERSION
    ontology_version: str = SHARED_AI_ONTOLOGY_VERSION
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
        if not self.allowed_action_types:
            raise ValueError("allowed_action_types must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Planner request contracts must remain observe-only and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class PlannerResponseContract:
    """Structured planner response scaffold bound to shared deterministic ontology."""

    response_id: str
    summary: str
    source_contract: CloudPlannerContract
    action_type: AiSuggestedActionType | None = None
    candidate_binding: SharedCandidateOntologyBinding | None = None
    target_label: SharedTargetLabel | None = None
    confidence: float | None = None
    dry_run_only: bool = True
    live_execution_requested: bool = False
    expected_transition: SemanticTransitionExpectation | None = None
    schema_version: str = AI_ARCHITECTURE_SCHEMA_VERSION
    ontology_version: str = SHARED_AI_ONTOLOGY_VERSION
    signal_status: AiArchitectureSignalStatus = AiArchitectureSignalStatus.available
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.response_id:
            raise ValueError("response_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Planner response contracts must remain observe-only and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ResolverRequestContract:
    """Structured request scaffold for a future local visual resolver."""

    request_id: str
    summary: str
    snapshot_id: str
    target_candidate_binding: SharedCandidateOntologyBinding
    candidate_bindings: tuple[SharedCandidateOntologyBinding, ...]
    target_label: SharedTargetLabel = SharedTargetLabel.candidate_center
    scenario_id: str | None = None
    allowed_action_types: tuple[AiSuggestedActionType, ...] = (
        AiSuggestedActionType.candidate_select,
    )
    schema_version: str = AI_ARCHITECTURE_SCHEMA_VERSION
    ontology_version: str = SHARED_AI_ONTOLOGY_VERSION
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
        if not self.allowed_action_types:
            raise ValueError("allowed_action_types must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Resolver request contracts must remain observe-only and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ResolverResponseContract:
    """Structured resolver response scaffold bound to shared deterministic ontology."""

    response_id: str
    summary: str
    source_contract: LocalVisualResolverContract
    action_type: AiSuggestedActionType | None = None
    candidate_binding: SharedCandidateOntologyBinding | None = None
    target_label: SharedTargetLabel | None = None
    point: NormalizedPoint | None = None
    confidence: float | None = None
    schema_version: str = AI_ARCHITECTURE_SCHEMA_VERSION
    ontology_version: str = SHARED_AI_ONTOLOGY_VERSION
    signal_status: AiArchitectureSignalStatus = AiArchitectureSignalStatus.available
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.response_id:
            raise ValueError("response_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Resolver response contracts must remain observe-only and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class PlannerRequestBuildResult:
    """Failure-safe planner-request construction result."""

    builder_name: str
    success: bool
    request_contract: PlannerRequestContract | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.builder_name:
            raise ValueError("builder_name must not be empty.")
        if self.success and self.request_contract is None:
            raise ValueError("Successful planner-request results must include request_contract.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed planner-request results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful planner-request results must not include error details.")
        if not self.success and self.request_contract is not None:
            raise ValueError("Failed planner-request results must not include request_contract.")

    @classmethod
    def ok(
        cls,
        *,
        builder_name: str,
        request_contract: PlannerRequestContract,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            builder_name=builder_name,
            success=True,
            request_contract=request_contract,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        builder_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            builder_name=builder_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class PlannerResponseBindResult:
    """Failure-safe planner-response binding result."""

    builder_name: str
    success: bool
    response_contract: PlannerResponseContract | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.builder_name:
            raise ValueError("builder_name must not be empty.")
        if self.success and self.response_contract is None:
            raise ValueError("Successful planner-response results must include response_contract.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed planner-response results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful planner-response results must not include error details.")
        if not self.success and self.response_contract is not None:
            raise ValueError("Failed planner-response results must not include response_contract.")

    @classmethod
    def ok(
        cls,
        *,
        builder_name: str,
        response_contract: PlannerResponseContract,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            builder_name=builder_name,
            success=True,
            response_contract=response_contract,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        builder_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            builder_name=builder_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class ResolverRequestBuildResult:
    """Failure-safe resolver-request construction result."""

    builder_name: str
    success: bool
    request_contract: ResolverRequestContract | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.builder_name:
            raise ValueError("builder_name must not be empty.")
        if self.success and self.request_contract is None:
            raise ValueError("Successful resolver-request results must include request_contract.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed resolver-request results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful resolver-request results must not include error details.")
        if not self.success and self.request_contract is not None:
            raise ValueError("Failed resolver-request results must not include request_contract.")

    @classmethod
    def ok(
        cls,
        *,
        builder_name: str,
        request_contract: ResolverRequestContract,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            builder_name=builder_name,
            success=True,
            request_contract=request_contract,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        builder_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            builder_name=builder_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class ResolverResponseBindResult:
    """Failure-safe resolver-response binding result."""

    builder_name: str
    success: bool
    response_contract: ResolverResponseContract | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.builder_name:
            raise ValueError("builder_name must not be empty.")
        if self.success and self.response_contract is None:
            raise ValueError("Successful resolver-response results must include response_contract.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed resolver-response results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful resolver-response results must not include error details.")
        if not self.success and self.response_contract is not None:
            raise ValueError("Failed resolver-response results must not include response_contract.")

    @classmethod
    def ok(
        cls,
        *,
        builder_name: str,
        response_contract: ResolverResponseContract,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            builder_name=builder_name,
            success=True,
            response_contract=response_contract,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        builder_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            builder_name=builder_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class _BindingArtifacts:
    bindings: tuple[SharedCandidateOntologyBinding, ...]
    partial_candidate_ids: tuple[str, ...] = ()
    failed_candidate_ids: tuple[str, ...] = ()

    @property
    def signal_status(self) -> AiArchitectureSignalStatus:
        if self.partial_candidate_ids or self.failed_candidate_ids:
            return AiArchitectureSignalStatus.partial
        if self.bindings:
            return AiArchitectureSignalStatus.available
        return AiArchitectureSignalStatus.absent


class ObserveOnlyPlannerContractBuilder:
    """Build observe-only planner requests and bind planner responses safely."""

    builder_name = "ObserveOnlyPlannerContractBuilder"

    def __init__(self, *, ontology_binder: ObserveOnlySharedOntologyBinder | None = None) -> None:
        self._ontology_binder = (
            ObserveOnlySharedOntologyBinder() if ontology_binder is None else ontology_binder
        )

    def build_request(
        self,
        snapshot: SemanticStateSnapshot,
        exposure_view: CandidateExposureView,
        *,
        summary: str,
        request_id: str,
        expected_transition: SemanticTransitionExpectation | None = None,
        scenario_id: str | None = None,
    ) -> PlannerRequestBuildResult:
        if exposure_view.snapshot_id != snapshot.snapshot_id:
            return PlannerRequestBuildResult.failure(
                builder_name=self.builder_name,
                error_code="planner_request_snapshot_mismatch",
                error_message="Exposure view must come from the same semantic snapshot as the planner request.",
                details={
                    "snapshot_id": snapshot.snapshot_id,
                    "exposure_snapshot_id": exposure_view.snapshot_id,
                },
            )
        try:
            artifacts = self._bind_exposure_candidates(exposure_view)
            signal_status = _merge_signal_status(
                exposure_signal_status=_signal_status_from_value(exposure_view.signal_status),
                binding_signal_status=artifacts.signal_status,
            )
            request_contract = PlannerRequestContract(
                request_id=request_id,
                summary=summary,
                snapshot_id=snapshot.snapshot_id,
                candidate_bindings=artifacts.bindings,
                scenario_id=scenario_id,
                expected_transition=expected_transition,
                signal_status=signal_status,
                metadata={
                    "candidate_ids": tuple(binding.candidate_id for binding in artifacts.bindings),
                    "candidate_binding_ids": tuple(binding.binding_id for binding in artifacts.bindings),
                    "partial_candidate_ids": artifacts.partial_candidate_ids,
                    "failed_candidate_ids": artifacts.failed_candidate_ids,
                    "exposure_signal_status": exposure_view.signal_status,
                    "exposed_candidate_count": exposure_view.exposed_candidate_count,
                    "expected_outcome_count": (
                        0
                        if expected_transition is None
                        else len(expected_transition.expected_outcomes)
                    ),
                    "scenario_id": scenario_id,
                    "observe_only": True,
                    "non_executing": True,
                },
            )
        except Exception as exc:  # noqa: BLE001 - contract building must remain failure-safe
            return PlannerRequestBuildResult.failure(
                builder_name=self.builder_name,
                error_code="planner_request_build_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return PlannerRequestBuildResult.ok(
            builder_name=self.builder_name,
            request_contract=request_contract,
            details={
                "signal_status": request_contract.signal_status.value,
                "candidate_count": len(request_contract.candidate_bindings),
            },
        )

    def bind_response(
        self,
        contract: CloudPlannerContract,
        *,
        exposure_view: CandidateExposureView | None = None,
    ) -> PlannerResponseBindResult:
        try:
            action_type: AiSuggestedActionType | None = None
            candidate_binding: SharedCandidateOntologyBinding | None = None
            target_label: SharedTargetLabel | None = None
            confidence: float | None = None
            signal_status = AiArchitectureSignalStatus.available
            missing_fields: list[str] = []

            if contract.action_suggestion is not None:
                action_type = _coerce_action_type(contract.action_suggestion.action_type)
                confidence = _coerce_confidence(contract.action_suggestion.confidence)
                if action_type is AiSuggestedActionType.candidate_select:
                    if exposure_view is None:
                        return PlannerResponseBindResult.failure(
                            builder_name=self.builder_name,
                            error_code="planner_response_missing_exposure_view",
                            error_message=(
                                "Candidate-targeted planner responses require an exposure view "
                                "for shared-ontology binding."
                            ),
                        )
                    candidate_binding = self._bind_one_exposed_candidate(
                        exposure_view,
                        contract.action_suggestion.candidate_id,
                    )
                    target_label = _coerce_target_label(contract.action_suggestion.target_label)
                    signal_status = _merge_signal_status(
                        exposure_signal_status=_signal_status_from_value(exposure_view.signal_status),
                        binding_signal_status=_binding_signal_status(candidate_binding),
                    )
                elif action_type is AiSuggestedActionType.observe_only:
                    target_label = None
                else:
                    missing_fields.append("action_type")
            if contract.action_suggestion is None and contract.expected_transition is None:
                signal_status = AiArchitectureSignalStatus.partial
                missing_fields.append("action_suggestion")

            response_contract = PlannerResponseContract(
                response_id=contract.decision_id,
                summary=contract.summary,
                source_contract=contract,
                action_type=action_type,
                candidate_binding=candidate_binding,
                target_label=target_label,
                confidence=confidence,
                dry_run_only=(
                    True if contract.action_suggestion is None else contract.action_suggestion.dry_run_only
                ),
                live_execution_requested=(
                    False
                    if contract.action_suggestion is None
                    else contract.action_suggestion.live_execution_requested
                ),
                expected_transition=contract.expected_transition,
                signal_status=signal_status,
                metadata={
                    **dict(contract.metadata),
                    "missing_fields": tuple(missing_fields),
                    "bound_candidate_id": (
                        None if candidate_binding is None else candidate_binding.candidate_id
                    ),
                    "planner_action_type": None if action_type is None else action_type.value,
                    "planner_target_label": None if target_label is None else target_label.value,
                    "observe_only": True,
                    "non_executing": True,
                },
            )
        except Exception as exc:  # noqa: BLE001 - response binding must remain failure-safe
            return PlannerResponseBindResult.failure(
                builder_name=self.builder_name,
                error_code="planner_response_bind_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return PlannerResponseBindResult.ok(
            builder_name=self.builder_name,
            response_contract=response_contract,
            details={"signal_status": response_contract.signal_status.value},
        )

    def _bind_exposure_candidates(self, exposure_view: CandidateExposureView) -> _BindingArtifacts:
        bindings: list[SharedCandidateOntologyBinding] = []
        partial_candidate_ids: list[str] = []
        failed_candidate_ids: list[str] = []
        for candidate in exposure_view.candidates:
            binding_result = self._ontology_binder.bind_exposed_candidate(candidate)
            if not binding_result.success or binding_result.binding is None:
                failed_candidate_ids.append(candidate.candidate_id)
                continue
            bindings.append(binding_result.binding)
            if binding_result.binding.completeness_status != "available":
                partial_candidate_ids.append(candidate.candidate_id)
        return _BindingArtifacts(
            bindings=tuple(bindings),
            partial_candidate_ids=tuple(partial_candidate_ids),
            failed_candidate_ids=tuple(failed_candidate_ids),
        )

    def _bind_one_exposed_candidate(
        self,
        exposure_view: CandidateExposureView,
        candidate_id: str | None,
    ) -> SharedCandidateOntologyBinding:
        if not candidate_id:
            raise ValueError("Planner candidate-targeted responses must include candidate_id.")
        candidate = _find_exposed_candidate(exposure_view, candidate_id)
        if candidate is None:
            raise ValueError(
                f"Planner response referenced candidate '{candidate_id}' which is not exposed."
            )
        binding_result = self._ontology_binder.bind_exposed_candidate(candidate)
        if not binding_result.success or binding_result.binding is None:
            raise ValueError(
                f"Planner response candidate '{candidate_id}' could not be bound to the shared ontology."
            )
        return binding_result.binding


class ObserveOnlyResolverContractBuilder:
    """Build observe-only resolver requests and bind resolver responses safely."""

    builder_name = "ObserveOnlyResolverContractBuilder"

    def __init__(self, *, ontology_binder: ObserveOnlySharedOntologyBinder | None = None) -> None:
        self._ontology_binder = (
            ObserveOnlySharedOntologyBinder() if ontology_binder is None else ontology_binder
        )

    def build_request(
        self,
        snapshot: SemanticStateSnapshot,
        exposure_view: CandidateExposureView,
        *,
        candidate_id: str,
        summary: str,
        target_label: SharedTargetLabel = SharedTargetLabel.candidate_center,
        request_id: str | None = None,
        scenario_id: str | None = None,
    ) -> ResolverRequestBuildResult:
        if exposure_view.snapshot_id != snapshot.snapshot_id:
            return ResolverRequestBuildResult.failure(
                builder_name=self.builder_name,
                error_code="resolver_request_snapshot_mismatch",
                error_message="Exposure view must come from the same semantic snapshot as the resolver request.",
                details={
                    "snapshot_id": snapshot.snapshot_id,
                    "exposure_snapshot_id": exposure_view.snapshot_id,
                },
            )
        try:
            artifacts = self._bind_exposure_candidates(exposure_view)
            target_binding = next(
                (binding for binding in artifacts.bindings if binding.candidate_id == candidate_id),
                None,
            )
            if target_binding is None:
                return ResolverRequestBuildResult.failure(
                    builder_name=self.builder_name,
                    error_code="resolver_request_candidate_unavailable",
                    error_message=(
                        f"Resolver request candidate '{candidate_id}' is not available in the "
                        "current exposed-candidate view."
                    ),
                    details={
                        "candidate_id": candidate_id,
                        "available_candidate_ids": tuple(
                            binding.candidate_id for binding in artifacts.bindings
                        ),
                    },
                )
            signal_status = _merge_signal_status(
                exposure_signal_status=_signal_status_from_value(exposure_view.signal_status),
                binding_signal_status=artifacts.signal_status,
            )
            request_contract = ResolverRequestContract(
                request_id=request_id or f"{candidate_id}:resolver_request",
                summary=summary,
                snapshot_id=snapshot.snapshot_id,
                target_candidate_binding=target_binding,
                candidate_bindings=artifacts.bindings,
                target_label=target_label,
                scenario_id=scenario_id,
                signal_status=signal_status,
                metadata={
                    "candidate_ids": tuple(binding.candidate_id for binding in artifacts.bindings),
                    "partial_candidate_ids": artifacts.partial_candidate_ids,
                    "failed_candidate_ids": artifacts.failed_candidate_ids,
                    "target_candidate_id": candidate_id,
                    "target_label": target_label.value,
                    "exposure_signal_status": exposure_view.signal_status,
                    "scenario_id": scenario_id,
                    "observe_only": True,
                    "non_executing": True,
                },
            )
        except Exception as exc:  # noqa: BLE001 - contract building must remain failure-safe
            return ResolverRequestBuildResult.failure(
                builder_name=self.builder_name,
                error_code="resolver_request_build_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return ResolverRequestBuildResult.ok(
            builder_name=self.builder_name,
            request_contract=request_contract,
            details={
                "signal_status": request_contract.signal_status.value,
                "candidate_count": len(request_contract.candidate_bindings),
            },
        )

    def bind_response(
        self,
        contract: LocalVisualResolverContract,
        *,
        exposure_view: CandidateExposureView | None = None,
    ) -> ResolverResponseBindResult:
        try:
            if exposure_view is None:
                return ResolverResponseBindResult.failure(
                    builder_name=self.builder_name,
                    error_code="resolver_response_missing_exposure_view",
                    error_message=(
                        "Resolver responses require an exposure view for shared-ontology binding."
                    ),
                )
            action_type = _coerce_action_type(contract.action_type)
            candidate_binding = self._bind_one_exposed_candidate(exposure_view, contract.candidate_id)
            target_label = _coerce_target_label(contract.target_label)
            point = _coerce_point(contract.point.x, contract.point.y)
            confidence = _coerce_confidence(contract.confidence)
            signal_status = _merge_signal_status(
                exposure_signal_status=_signal_status_from_value(exposure_view.signal_status),
                binding_signal_status=_binding_signal_status(candidate_binding),
            )
            response_contract = ResolverResponseContract(
                response_id=contract.resolution_id,
                summary=contract.summary,
                source_contract=contract,
                action_type=action_type,
                candidate_binding=candidate_binding,
                target_label=target_label,
                point=point,
                confidence=confidence,
                signal_status=signal_status,
                metadata={
                    **dict(contract.metadata),
                    "bound_candidate_id": candidate_binding.candidate_id,
                    "resolver_action_type": action_type.value,
                    "resolver_target_label": target_label.value,
                    "observe_only": True,
                    "non_executing": True,
                },
            )
        except Exception as exc:  # noqa: BLE001 - response binding must remain failure-safe
            return ResolverResponseBindResult.failure(
                builder_name=self.builder_name,
                error_code="resolver_response_bind_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return ResolverResponseBindResult.ok(
            builder_name=self.builder_name,
            response_contract=response_contract,
            details={"signal_status": response_contract.signal_status.value},
        )

    def _bind_exposure_candidates(self, exposure_view: CandidateExposureView) -> _BindingArtifacts:
        return ObserveOnlyPlannerContractBuilder(
            ontology_binder=self._ontology_binder
        )._bind_exposure_candidates(exposure_view)

    def _bind_one_exposed_candidate(
        self,
        exposure_view: CandidateExposureView,
        candidate_id: str | None,
    ) -> SharedCandidateOntologyBinding:
        return ObserveOnlyPlannerContractBuilder(
            ontology_binder=self._ontology_binder
        )._bind_one_exposed_candidate(exposure_view, candidate_id)


def _find_exposed_candidate(
    exposure_view: CandidateExposureView,
    candidate_id: str,
) -> ExposedCandidate | None:
    return next(
        (candidate for candidate in exposure_view.candidates if candidate.candidate_id == candidate_id),
        None,
    )


def _signal_status_from_value(value: str) -> AiArchitectureSignalStatus:
    try:
        return AiArchitectureSignalStatus(value)
    except ValueError:
        return AiArchitectureSignalStatus.partial


def _merge_signal_status(
    *,
    exposure_signal_status: AiArchitectureSignalStatus,
    binding_signal_status: AiArchitectureSignalStatus,
) -> AiArchitectureSignalStatus:
    if (
        exposure_signal_status is AiArchitectureSignalStatus.partial
        or binding_signal_status is AiArchitectureSignalStatus.partial
    ):
        return AiArchitectureSignalStatus.partial
    if (
        exposure_signal_status is AiArchitectureSignalStatus.absent
        and binding_signal_status is AiArchitectureSignalStatus.absent
    ):
        return AiArchitectureSignalStatus.absent
    return AiArchitectureSignalStatus.available


def _binding_signal_status(
    binding: SharedCandidateOntologyBinding | None,
) -> AiArchitectureSignalStatus:
    if binding is None:
        return AiArchitectureSignalStatus.absent
    if binding.completeness_status != "available":
        return AiArchitectureSignalStatus.partial
    return AiArchitectureSignalStatus.available


def _coerce_action_type(value: str | None) -> AiSuggestedActionType:
    if not value:
        raise ValueError("action_type must not be empty.")
    try:
        return AiSuggestedActionType(value)
    except ValueError as exc:
        raise ValueError(f"Unsupported action_type '{value}'.") from exc


def _coerce_target_label(value: str | None) -> SharedTargetLabel:
    if not value:
        raise ValueError("target_label must not be empty.")
    try:
        return SharedTargetLabel(value)
    except ValueError as exc:
        raise ValueError(f"Unsupported target_label '{value}'.") from exc


def _coerce_confidence(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("confidence must be numeric.")
    confidence = float(value)
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")
    return confidence


def _coerce_point(x: object, y: object) -> NormalizedPoint:
    if isinstance(x, bool) or not isinstance(x, int | float):
        raise ValueError("point.x must be numeric.")
    if isinstance(y, bool) or not isinstance(y, int | float):
        raise ValueError("point.y must be numeric.")
    return NormalizedPoint(x=float(x), y=float(y))
