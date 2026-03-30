"""Deterministic escalation engine for future hybrid AI routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.ai_architecture.arbitration import (
    ArbitrationConflict,
    ArbitrationConflictKind,
    ArbitrationSource,
    EscalationPolicy,
)
from universal_visual_os_agent.ai_architecture.contracts import (
    AiArchitectureSignalStatus,
    PlannerResponseContract,
    ResolverResponseContract,
)
from universal_visual_os_agent.ai_architecture.ontology import (
    SharedCandidateOntologyBinding,
)
from universal_visual_os_agent.semantics.ontology import CandidateSelectionRiskLevel


class DeterministicEscalationDisposition(StrEnum):
    """Stable non-executing escalation paths for future hybrid AI routing."""

    deterministic_ok = "deterministic_ok"
    local_resolver_recommended = "local_resolver_recommended"
    cloud_planner_recommended = "cloud_planner_recommended"
    human_confirmation_required = "human_confirmation_required"
    blocked = "blocked"


class DeterministicEscalationReason(StrEnum):
    """Stable reason codes for deterministic escalation decisions."""

    deterministic_binding_missing = "deterministic_binding_missing"
    deterministic_binding_partial = "deterministic_binding_partial"
    deterministic_confidence_unavailable = "deterministic_confidence_unavailable"
    deterministic_confidence_below_threshold = "deterministic_confidence_below_threshold"
    resolver_response_partial = "resolver_response_partial"
    resolver_confidence_insufficient = "resolver_confidence_insufficient"
    planner_response_partial = "planner_response_partial"
    planner_confidence_insufficient = "planner_confidence_insufficient"
    planner_live_execution_requested = "planner_live_execution_requested"
    source_conflict_present = "source_conflict_present"
    disambiguation_needed = "disambiguation_needed"
    requires_local_resolver = "requires_local_resolver"
    high_selection_risk = "high_selection_risk"
    arbitration_conflict_present = "arbitration_conflict_present"
    incomplete_contract_conflict = "incomplete_contract_conflict"
    safety_ineligibility_conflict = "safety_ineligibility_conflict"
    multi_source_conflict = "multi_source_conflict"
    conflicting_high_risk_signals = "conflicting_high_risk_signals"
    deterministic_sufficient = "deterministic_sufficient"
    escalation_engine_exception = "escalation_engine_exception"


@dataclass(slots=True, frozen=True, kw_only=True)
class DeterministicEscalationDecision:
    """Structured deterministic escalation recommendation."""

    disposition: DeterministicEscalationDisposition
    summary: str
    signal_status: AiArchitectureSignalStatus
    recommended_source: ArbitrationSource | None = None
    reason_codes: tuple[DeterministicEscalationReason, ...] = ()
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError(
                "Deterministic escalation decisions must remain safety-first and non-executing."
            )


@dataclass(slots=True, frozen=True, kw_only=True)
class DeterministicEscalationEvaluationResult:
    """Failure-safe evaluation result for the deterministic escalation engine."""

    engine_name: str
    success: bool
    decision: DeterministicEscalationDecision | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.engine_name:
            raise ValueError("engine_name must not be empty.")
        if self.success and self.decision is None:
            raise ValueError("Successful evaluation results must include decision.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed evaluation results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful evaluation results must not include error details.")
        if not self.success and self.decision is not None:
            raise ValueError("Failed evaluation results must not include decision.")

    @classmethod
    def ok(
        cls,
        *,
        engine_name: str,
        decision: DeterministicEscalationDecision,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            engine_name=engine_name,
            success=True,
            decision=decision,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        engine_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            engine_name=engine_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


class ObserveOnlyDeterministicEscalationEngine:
    """Choose a conservative future escalation path without executing anything."""

    engine_name = "ObserveOnlyDeterministicEscalationEngine"

    def evaluate(
        self,
        *,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        resolver_response: ResolverResponseContract | None = None,
        planner_response: PlannerResponseContract | None = None,
        conflicts: tuple[ArbitrationConflict, ...] = (),
        policy: EscalationPolicy | None = None,
    ) -> DeterministicEscalationEvaluationResult:
        try:
            active_policy = EscalationPolicy() if policy is None else policy
            signal_status = _signal_status(
                deterministic_binding=deterministic_binding,
                resolver_response=resolver_response,
                planner_response=planner_response,
            )
            decision = self._build_decision(
                deterministic_binding=deterministic_binding,
                resolver_response=resolver_response,
                planner_response=planner_response,
                conflicts=conflicts,
                policy=active_policy,
                signal_status=signal_status,
            )
        except Exception as exc:  # noqa: BLE001 - escalation must remain failure-safe
            return DeterministicEscalationEvaluationResult.failure(
                engine_name=self.engine_name,
                error_code="deterministic_escalation_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return DeterministicEscalationEvaluationResult.ok(
            engine_name=self.engine_name,
            decision=decision,
            details={
                "disposition": decision.disposition.value,
                "signal_status": decision.signal_status.value,
                "recommended_source": (
                    None if decision.recommended_source is None else decision.recommended_source.value
                ),
            },
        )

    def _build_decision(
        self,
        *,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        resolver_response: ResolverResponseContract | None,
        planner_response: PlannerResponseContract | None,
        conflicts: tuple[ArbitrationConflict, ...],
        policy: EscalationPolicy,
        signal_status: AiArchitectureSignalStatus,
    ) -> DeterministicEscalationDecision:
        reasons: list[DeterministicEscalationReason] = []

        if deterministic_binding is None:
            return _decision(
                disposition=DeterministicEscalationDisposition.blocked,
                summary="Deterministic candidate context is missing, so escalation remains blocked.",
                signal_status=signal_status,
                recommended_source=None,
                reason_codes=(DeterministicEscalationReason.deterministic_binding_missing,),
                conflicts=conflicts,
                policy=policy,
            )

        if deterministic_binding.completeness_status != "available":
            return _decision(
                disposition=DeterministicEscalationDisposition.blocked,
                summary="Deterministic candidate metadata is incomplete, so escalation remains blocked.",
                signal_status=signal_status,
                recommended_source=None,
                reason_codes=(DeterministicEscalationReason.deterministic_binding_partial,),
                conflicts=conflicts,
                policy=policy,
            )

        if resolver_response is not None and resolver_response.signal_status is not AiArchitectureSignalStatus.available:
            return _decision(
                disposition=DeterministicEscalationDisposition.blocked,
                summary="Resolver metadata is incomplete, so escalation remains blocked.",
                signal_status=signal_status,
                recommended_source=None,
                reason_codes=(DeterministicEscalationReason.resolver_response_partial,),
                conflicts=conflicts,
                policy=policy,
            )

        if planner_response is not None and planner_response.signal_status is not AiArchitectureSignalStatus.available:
            return _decision(
                disposition=DeterministicEscalationDisposition.blocked,
                summary="Planner metadata is incomplete, so escalation remains blocked.",
                signal_status=signal_status,
                recommended_source=None,
                reason_codes=(DeterministicEscalationReason.planner_response_partial,),
                conflicts=conflicts,
                policy=policy,
            )

        if planner_response is not None and planner_response.live_execution_requested:
            return _decision(
                disposition=DeterministicEscalationDisposition.blocked,
                summary="Planner requested live execution in a safety-first non-executing phase.",
                signal_status=signal_status,
                recommended_source=None,
                reason_codes=(DeterministicEscalationReason.planner_live_execution_requested,),
                conflicts=conflicts,
                policy=policy,
            )

        if _contains_conflict(conflicts, ArbitrationConflictKind.safety_ineligibility):
            return _decision(
                disposition=DeterministicEscalationDisposition.blocked,
                summary="Unsafe AI disagreement signals keep the escalation path blocked.",
                signal_status=signal_status,
                recommended_source=None,
                reason_codes=(DeterministicEscalationReason.safety_ineligibility_conflict,),
                conflicts=conflicts,
                policy=policy,
            )

        if _contains_conflict(
            conflicts,
            ArbitrationConflictKind.missing_contract,
            ArbitrationConflictKind.incomplete_contract,
        ):
            return _decision(
                disposition=DeterministicEscalationDisposition.blocked,
                summary="Incomplete arbitration inputs keep the escalation path blocked.",
                signal_status=signal_status,
                recommended_source=None,
                reason_codes=(DeterministicEscalationReason.incomplete_contract_conflict,),
                conflicts=conflicts,
                policy=policy,
            )

        high_risk = deterministic_binding.selection_risk_level is CandidateSelectionRiskLevel.high
        deterministic_confidence_low = (
            deterministic_binding.confidence is not None
            and deterministic_binding.confidence < policy.deterministic_confidence_threshold
        )
        deterministic_confidence_missing = deterministic_binding.confidence is None

        local_resolver_needed = False
        if deterministic_binding.requires_local_resolver:
            local_resolver_needed = True
            reasons.append(DeterministicEscalationReason.requires_local_resolver)
        if deterministic_binding.disambiguation_needed:
            local_resolver_needed = True
            reasons.append(DeterministicEscalationReason.disambiguation_needed)
        if high_risk and policy.local_resolver_for_high_risk:
            local_resolver_needed = True
            reasons.append(DeterministicEscalationReason.high_selection_risk)
        if deterministic_confidence_low:
            local_resolver_needed = True
            reasons.append(DeterministicEscalationReason.deterministic_confidence_below_threshold)
        if deterministic_confidence_missing:
            local_resolver_needed = True
            reasons.append(DeterministicEscalationReason.deterministic_confidence_unavailable)

        material_conflicts_present = _contains_conflict(
            conflicts,
            ArbitrationConflictKind.candidate_reference_mismatch,
            ArbitrationConflictKind.label_mismatch,
            ArbitrationConflictKind.target_label_mismatch,
            ArbitrationConflictKind.action_mismatch,
            ArbitrationConflictKind.confidence_disagreement,
        )
        if material_conflicts_present:
            reasons.append(DeterministicEscalationReason.arbitration_conflict_present)
        if deterministic_binding.source_conflict_present:
            reasons.append(DeterministicEscalationReason.source_conflict_present)

        if local_resolver_needed:
            if resolver_response is None:
                return _decision(
                    disposition=DeterministicEscalationDisposition.local_resolver_recommended,
                    summary="Deterministic ambiguity or risk signals recommend a local resolver check.",
                    signal_status=signal_status,
                    recommended_source=ArbitrationSource.local_visual_resolver,
                    reason_codes=tuple(reasons),
                    conflicts=conflicts,
                    policy=policy,
                )
            if not _confidence_meets_threshold(
                resolver_response.confidence,
                threshold=policy.local_resolver_confidence_threshold,
            ):
                reasons.append(DeterministicEscalationReason.resolver_confidence_insufficient)
                if planner_response is None:
                    return _decision(
                        disposition=DeterministicEscalationDisposition.cloud_planner_recommended,
                        summary="Resolver evidence is insufficient, so cloud-planner escalation is recommended.",
                        signal_status=signal_status,
                        recommended_source=ArbitrationSource.cloud_planner,
                        reason_codes=tuple(reasons),
                        conflicts=conflicts,
                        policy=policy,
                    )
                return _decision(
                    disposition=DeterministicEscalationDisposition.human_confirmation_required,
                    summary="Resolver evidence remains insufficient after additional escalation, so human confirmation is required.",
                    signal_status=signal_status,
                    recommended_source=None,
                    reason_codes=tuple(
                        reasons + [DeterministicEscalationReason.multi_source_conflict]
                    ),
                    conflicts=conflicts,
                    policy=policy,
                )
            if material_conflicts_present:
                if planner_response is None:
                    return _decision(
                        disposition=DeterministicEscalationDisposition.cloud_planner_recommended,
                        summary="Resolver output still conflicts with deterministic signals, so cloud-planner escalation is recommended.",
                        signal_status=signal_status,
                        recommended_source=ArbitrationSource.cloud_planner,
                        reason_codes=tuple(reasons),
                        conflicts=conflicts,
                        policy=policy,
                    )
                return _decision(
                    disposition=DeterministicEscalationDisposition.human_confirmation_required,
                    summary="High-confidence deterministic and AI signals still conflict, so human confirmation is required.",
                    signal_status=signal_status,
                    recommended_source=None,
                    reason_codes=tuple(
                        reasons
                        + [
                            DeterministicEscalationReason.conflicting_high_risk_signals
                            if high_risk
                            else DeterministicEscalationReason.multi_source_conflict
                        ]
                    ),
                    conflicts=conflicts,
                    policy=policy,
                )
            reasons.append(DeterministicEscalationReason.deterministic_sufficient)
            return _decision(
                disposition=DeterministicEscalationDisposition.deterministic_ok,
                summary="Resolver-supported deterministic context is sufficient, so no further escalation is needed.",
                signal_status=signal_status,
                recommended_source=ArbitrationSource.deterministic_pipeline,
                reason_codes=tuple(reasons),
                conflicts=conflicts,
                policy=policy,
            )

        if deterministic_binding.source_conflict_present or material_conflicts_present:
            if planner_response is None:
                return _decision(
                    disposition=DeterministicEscalationDisposition.cloud_planner_recommended,
                    summary="Source conflict or unresolved arbitration disagreement recommends cloud-planner escalation.",
                    signal_status=signal_status,
                    recommended_source=ArbitrationSource.cloud_planner,
                    reason_codes=tuple(reasons),
                    conflicts=conflicts,
                    policy=policy,
                )
            if not _confidence_meets_threshold(
                planner_response.confidence,
                threshold=policy.cloud_planner_confidence_threshold,
            ):
                return _decision(
                    disposition=DeterministicEscalationDisposition.human_confirmation_required,
                    summary="Cloud-planner evidence is still insufficient, so human confirmation is required.",
                    signal_status=signal_status,
                    recommended_source=None,
                    reason_codes=tuple(
                        reasons + [DeterministicEscalationReason.planner_confidence_insufficient]
                    ),
                    conflicts=conflicts,
                    policy=policy,
                )
            if high_risk and material_conflicts_present:
                return _decision(
                    disposition=DeterministicEscalationDisposition.human_confirmation_required,
                    summary="High-risk multi-source disagreement remains unresolved, so human confirmation is required.",
                    signal_status=signal_status,
                    recommended_source=None,
                    reason_codes=tuple(
                        reasons + [DeterministicEscalationReason.conflicting_high_risk_signals]
                    ),
                    conflicts=conflicts,
                    policy=policy,
                )
            reasons.append(DeterministicEscalationReason.deterministic_sufficient)
            return _decision(
                disposition=DeterministicEscalationDisposition.deterministic_ok,
                summary="Current multi-source evidence is sufficient, so no further escalation is needed.",
                signal_status=signal_status,
                recommended_source=ArbitrationSource.deterministic_pipeline,
                reason_codes=tuple(reasons),
                conflicts=conflicts,
                policy=policy,
            )

        return _decision(
            disposition=DeterministicEscalationDisposition.deterministic_ok,
            summary="Deterministic candidate evidence is sufficient, so no escalation is needed.",
            signal_status=signal_status,
            recommended_source=ArbitrationSource.deterministic_pipeline,
            reason_codes=(DeterministicEscalationReason.deterministic_sufficient,),
            conflicts=conflicts,
            policy=policy,
        )


def _decision(
    *,
    disposition: DeterministicEscalationDisposition,
    summary: str,
    signal_status: AiArchitectureSignalStatus,
    recommended_source: ArbitrationSource | None,
    reason_codes: tuple[DeterministicEscalationReason, ...],
    conflicts: tuple[ArbitrationConflict, ...],
    policy: EscalationPolicy,
) -> DeterministicEscalationDecision:
    return DeterministicEscalationDecision(
        disposition=disposition,
        summary=summary,
        signal_status=signal_status,
        recommended_source=recommended_source,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        metadata={
            "conflict_kinds": tuple(conflict.kind.value for conflict in conflicts),
            "conflict_count": len(conflicts),
            "policy_thresholds": {
                "deterministic_confidence_threshold": policy.deterministic_confidence_threshold,
                "local_resolver_confidence_threshold": policy.local_resolver_confidence_threshold,
                "cloud_planner_confidence_threshold": policy.cloud_planner_confidence_threshold,
            },
            "observe_only": True,
            "read_only": True,
            "non_executing": True,
        },
    )


def _contains_conflict(
    conflicts: tuple[ArbitrationConflict, ...],
    *kinds: ArbitrationConflictKind,
) -> bool:
    expected = set(kinds)
    return any(conflict.kind in expected for conflict in conflicts)


def _confidence_meets_threshold(confidence: float | None, *, threshold: float) -> bool:
    return confidence is not None and confidence >= threshold


def _signal_status(
    *,
    deterministic_binding: SharedCandidateOntologyBinding | None,
    resolver_response: ResolverResponseContract | None,
    planner_response: PlannerResponseContract | None,
) -> AiArchitectureSignalStatus:
    statuses: list[AiArchitectureSignalStatus] = []
    if deterministic_binding is None:
        statuses.append(AiArchitectureSignalStatus.absent)
    elif deterministic_binding.completeness_status != "available":
        statuses.append(AiArchitectureSignalStatus.partial)
    else:
        statuses.append(AiArchitectureSignalStatus.available)
    if resolver_response is not None:
        statuses.append(resolver_response.signal_status)
    if planner_response is not None:
        statuses.append(planner_response.signal_status)
    if any(status is AiArchitectureSignalStatus.partial for status in statuses):
        return AiArchitectureSignalStatus.partial
    if any(status is AiArchitectureSignalStatus.absent for status in statuses):
        return AiArchitectureSignalStatus.partial
    return AiArchitectureSignalStatus.available
