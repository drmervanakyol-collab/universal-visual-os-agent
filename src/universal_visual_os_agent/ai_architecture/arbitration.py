"""Observe-only arbitration and escalation scaffolding for future hybrid AI flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from itertools import combinations
import logging
from typing import Mapping, Self

from universal_visual_os_agent.ai_architecture.contracts import (
    AiArchitectureSignalStatus,
    PlannerResponseContract,
    ResolverResponseContract,
)
from universal_visual_os_agent.ai_architecture.ontology import (
    SharedCandidateOntologyBinding,
    SharedTargetLabel,
)
from universal_visual_os_agent.ai_boundary.models import AiSuggestedActionType
from universal_visual_os_agent.semantics.ontology import CandidateSelectionRiskLevel


_LOGGER = logging.getLogger(__name__)


class ArbitrationSource(StrEnum):
    """Stable sources that can participate in future hybrid AI arbitration."""

    deterministic_pipeline = "deterministic_pipeline"
    local_visual_resolver = "local_visual_resolver"
    cloud_planner = "cloud_planner"


class ArbitrationConflictKind(StrEnum):
    """Stable disagreement kinds between deterministic and future AI sources."""

    missing_contract = "missing_contract"
    incomplete_contract = "incomplete_contract"
    candidate_reference_mismatch = "candidate_reference_mismatch"
    label_mismatch = "label_mismatch"
    target_label_mismatch = "target_label_mismatch"
    action_mismatch = "action_mismatch"
    confidence_disagreement = "confidence_disagreement"
    safety_ineligibility = "safety_ineligibility"


class EscalationAction(StrEnum):
    """Next-step scaffolding decisions for hybrid arbitration."""

    stay_deterministic = "stay_deterministic"
    ask_local_resolver = "ask_local_resolver"
    escalate_to_cloud_planner = "escalate_to_cloud_planner"
    block_for_user_confirmation = "block_for_user_confirmation"


class ArbitrationStatus(StrEnum):
    """High-level arbitration outcome status."""

    resolved = "resolved"
    escalated = "escalated"
    blocked = "blocked"
    partial = "partial"


@dataclass(slots=True, frozen=True, kw_only=True)
class EscalationPolicy:
    """Conservative escalation-policy scaffolding for future two-AI routing."""

    deterministic_confidence_threshold: float = 0.9
    local_resolver_confidence_threshold: float = 0.75
    cloud_planner_confidence_threshold: float = 0.7
    confidence_disagreement_tolerance: float = 0.15
    local_resolver_for_high_risk: bool = True
    cloud_planner_for_source_conflict: bool = True
    block_on_incomplete_contracts: bool = True
    block_on_unresolved_disagreement: bool = True
    require_user_confirmation_for_conflicting_high_risk: bool = True
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "deterministic_confidence_threshold",
            "local_resolver_confidence_threshold",
            "cloud_planner_confidence_threshold",
            "confidence_disagreement_tolerance",
        ):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0 inclusive.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Escalation policies must remain observe-only and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ArbitrationConflict:
    """Structured disagreement or incompleteness record for arbitration."""

    kind: ArbitrationConflictKind
    summary: str
    sources: tuple[ArbitrationSource, ...]
    candidate_ids: tuple[str, ...] = ()
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.sources:
            raise ValueError("sources must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Arbitration conflicts must remain observe-only and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class EscalationDecision:
    """Structured escalation recommendation from the arbitration policy."""

    action: EscalationAction
    summary: str
    preferred_source: ArbitrationSource | None = None
    reason_codes: tuple[str, ...] = ()
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Escalation decisions must remain observe-only and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ArbitrationOutcome:
    """Structured arbitration outcome for deterministic and future AI sources."""

    status: ArbitrationStatus
    summary: str
    selected_source: ArbitrationSource | None
    escalation_decision: EscalationDecision
    selected_candidate_id: str | None = None
    selected_candidate_label: str | None = None
    selected_target_label: SharedTargetLabel | None = None
    selected_action_type: AiSuggestedActionType | None = None
    selected_confidence: float | None = None
    signal_status: AiArchitectureSignalStatus = AiArchitectureSignalStatus.available
    conflicts: tuple[ArbitrationConflict, ...] = ()
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.selected_confidence is not None and not 0.0 <= self.selected_confidence <= 1.0:
            raise ValueError("selected_confidence must be between 0.0 and 1.0 inclusive.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Arbitration outcomes must remain observe-only and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ArbitrationEvaluationResult:
    """Failure-safe arbitration result wrapper."""

    arbitrator_name: str
    success: bool
    outcome: ArbitrationOutcome | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.arbitrator_name:
            raise ValueError("arbitrator_name must not be empty.")
        if self.success and self.outcome is None:
            raise ValueError("Successful arbitration results must include outcome.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed arbitration results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful arbitration results must not include error details.")
        if not self.success and self.outcome is not None:
            raise ValueError("Failed arbitration results must not include outcome.")

    @classmethod
    def ok(
        cls,
        *,
        arbitrator_name: str,
        outcome: ArbitrationOutcome,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            arbitrator_name=arbitrator_name,
            success=True,
            outcome=outcome,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        arbitrator_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            arbitrator_name=arbitrator_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


class ObserveOnlyEscalationPolicyDecider:
    """Make conservative escalation recommendations without executing anything."""

    decider_name = "ObserveOnlyEscalationPolicyDecider"

    def decide(
        self,
        *,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        resolver_response: ResolverResponseContract | None = None,
        planner_response: PlannerResponseContract | None = None,
        conflicts: tuple[ArbitrationConflict, ...] = (),
        policy: EscalationPolicy | None = None,
    ) -> EscalationDecision:
        try:
            active_policy = EscalationPolicy() if policy is None else policy
            high_risk = _is_high_risk(deterministic_binding)
            reason_codes: list[str] = []
            preliminary_decision = (
                self._missing_binding_decision(
                    deterministic_binding=deterministic_binding,
                    policy=active_policy,
                    reason_codes=reason_codes,
                )
                or self._incomplete_binding_decision(
                    deterministic_binding=deterministic_binding,
                    policy=active_policy,
                    reason_codes=reason_codes,
                )
                or self._source_conflict_decision(
                    deterministic_binding=deterministic_binding,
                    policy=active_policy,
                    reason_codes=reason_codes,
                )
                or self._local_resolver_needed_decision(
                    deterministic_binding=deterministic_binding,
                    policy=active_policy,
                    high_risk=high_risk,
                    reason_codes=reason_codes,
                )
            )
            if preliminary_decision is not None:
                return preliminary_decision

            conflict_decision = self._conflict_decision(
                conflicts=conflicts,
                resolver_response=resolver_response,
                planner_response=planner_response,
                policy=active_policy,
                high_risk=high_risk,
                reason_codes=reason_codes,
            )
            if conflict_decision is not None:
                return conflict_decision

            return _decision(
                action=EscalationAction.stay_deterministic,
                preferred_source=ArbitrationSource.deterministic_pipeline,
                summary="Deterministic pipeline remains the safe source of truth for this candidate.",
                reason_codes=tuple(reason_codes),
                rule_id="stay_deterministic",
                metadata={
                    "conflict_count": len(conflicts),
                    "high_risk": high_risk,
                    "resolver_response_present": resolver_response is not None,
                    "planner_response_present": planner_response is not None,
                },
            )
        except Exception as exc:  # noqa: BLE001 - policy decisions must remain failure-safe
            _LOGGER.exception("Escalation policy decision fell back to blocked mode.")
            return _decision(
                action=EscalationAction.block_for_user_confirmation,
                preferred_source=None,
                summary="Escalation policy fell back to a blocked decision after an internal error.",
                reason_codes=("policy_exception",),
                rule_id="policy_exception_fallback",
                metadata={
                    "exception_type": type(exc).__name__,
                    "error_message": str(exc),
                    "exception_stage": "decide",
                },
            )

    def _missing_binding_decision(
        self,
        *,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        policy: EscalationPolicy,
        reason_codes: list[str],
    ) -> EscalationDecision | None:
        if deterministic_binding is not None:
            return None
        reason_codes.append("deterministic_binding_missing")
        if policy.block_on_incomplete_contracts:
            return _decision(
                action=EscalationAction.block_for_user_confirmation,
                preferred_source=None,
                summary="Deterministic candidate context is missing, so arbitration stays blocked.",
                reason_codes=reason_codes,
                rule_id="missing_binding_block",
            )
        return _decision(
            action=EscalationAction.ask_local_resolver,
            preferred_source=ArbitrationSource.local_visual_resolver,
            summary="Deterministic candidate context is missing, so the next safe step is a local resolver request.",
            reason_codes=reason_codes,
            rule_id="missing_binding_local_resolver",
        )

    def _incomplete_binding_decision(
        self,
        *,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        policy: EscalationPolicy,
        reason_codes: list[str],
    ) -> EscalationDecision | None:
        if (
            deterministic_binding is None
            or deterministic_binding.completeness_status == "available"
        ):
            return None
        reason_codes.append("deterministic_binding_partial")
        if not policy.block_on_incomplete_contracts:
            return None
        return _decision(
            action=EscalationAction.block_for_user_confirmation,
            preferred_source=None,
            summary="Deterministic candidate metadata is incomplete, so arbitration stays blocked.",
            reason_codes=reason_codes,
            rule_id="partial_binding_block",
        )

    def _source_conflict_decision(
        self,
        *,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        policy: EscalationPolicy,
        reason_codes: list[str],
    ) -> EscalationDecision | None:
        if deterministic_binding is None or not deterministic_binding.source_conflict_present:
            return None
        reason_codes.append("deterministic_source_conflict")
        if not policy.cloud_planner_for_source_conflict:
            return None
        return _decision(
            action=EscalationAction.escalate_to_cloud_planner,
            preferred_source=ArbitrationSource.cloud_planner,
            summary="Deterministic source conflict requires cloud-planner arbitration scaffolding.",
            reason_codes=reason_codes,
            rule_id="source_conflict_cloud_planner",
        )

    def _local_resolver_needed_decision(
        self,
        *,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        policy: EscalationPolicy,
        high_risk: bool,
        reason_codes: list[str],
    ) -> EscalationDecision | None:
        if deterministic_binding is None:
            return None
        if deterministic_binding.requires_local_resolver:
            reason_codes.append("deterministic_requires_local_resolver")
            return _decision(
                action=EscalationAction.ask_local_resolver,
                preferred_source=ArbitrationSource.local_visual_resolver,
                summary="Candidate metadata explicitly requires local visual resolution.",
                reason_codes=reason_codes,
                rule_id="requires_local_resolver",
            )
        if deterministic_binding.disambiguation_needed:
            reason_codes.append("deterministic_disambiguation_needed")
            return _decision(
                action=EscalationAction.ask_local_resolver,
                preferred_source=ArbitrationSource.local_visual_resolver,
                summary="Candidate ambiguity requires local visual resolution before continuing.",
                reason_codes=reason_codes,
                rule_id="disambiguation_needed",
            )
        if high_risk and policy.local_resolver_for_high_risk:
            reason_codes.append("high_selection_risk")
            return _decision(
                action=EscalationAction.ask_local_resolver,
                preferred_source=ArbitrationSource.local_visual_resolver,
                summary="High-risk candidate selection should be checked by the local resolver first.",
                reason_codes=reason_codes,
                rule_id="high_risk_local_resolver",
            )
        if (
            deterministic_binding.confidence is not None
            and deterministic_binding.confidence < policy.deterministic_confidence_threshold
        ):
            reason_codes.append("deterministic_confidence_below_threshold")
            return _decision(
                action=EscalationAction.ask_local_resolver,
                preferred_source=ArbitrationSource.local_visual_resolver,
                summary="Deterministic confidence is below threshold, so local resolver escalation is preferred.",
                reason_codes=reason_codes,
                rule_id="low_confidence_local_resolver",
            )
        return None

    def _conflict_decision(
        self,
        *,
        conflicts: tuple[ArbitrationConflict, ...],
        resolver_response: ResolverResponseContract | None,
        planner_response: PlannerResponseContract | None,
        policy: EscalationPolicy,
        high_risk: bool,
        reason_codes: list[str],
    ) -> EscalationDecision | None:
        if not conflicts:
            return None
        reason_codes.extend(
            sorted(dict.fromkeys(f"conflict:{conflict.kind.value}" for conflict in conflicts))
        )
        if high_risk and policy.require_user_confirmation_for_conflicting_high_risk:
            return _decision(
                action=EscalationAction.block_for_user_confirmation,
                preferred_source=None,
                summary="High-risk conflicting signals require user confirmation scaffolding.",
                reason_codes=reason_codes,
                rule_id="conflicting_high_risk_block",
            )
        if not policy.block_on_unresolved_disagreement:
            return None
        if resolver_response is None:
            return _decision(
                action=EscalationAction.ask_local_resolver,
                preferred_source=ArbitrationSource.local_visual_resolver,
                summary="Conflicting signals require a local resolver arbitration step.",
                reason_codes=reason_codes,
                rule_id="conflict_local_resolver",
            )
        if planner_response is None:
            return _decision(
                action=EscalationAction.escalate_to_cloud_planner,
                preferred_source=ArbitrationSource.cloud_planner,
                summary="Conflicting deterministic and local signals require cloud-planner escalation scaffolding.",
                reason_codes=reason_codes,
                rule_id="conflict_cloud_planner",
            )
        return _decision(
            action=EscalationAction.block_for_user_confirmation,
            preferred_source=None,
            summary="Conflicting deterministic, local, and planner signals remain blocked pending user confirmation.",
            reason_codes=reason_codes,
            rule_id="conflict_user_confirmation",
        )


class ObserveOnlyAiArbitrator:
    """Conservative arbitration scaffolding for deterministic, local, and planner signals."""

    arbitrator_name = "ObserveOnlyAiArbitrator"

    def __init__(
        self,
        *,
        policy_decider: ObserveOnlyEscalationPolicyDecider | None = None,
    ) -> None:
        self._policy_decider = (
            ObserveOnlyEscalationPolicyDecider()
            if policy_decider is None
            else policy_decider
        )

    def arbitrate(
        self,
        *,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        resolver_response: ResolverResponseContract | None = None,
        planner_response: PlannerResponseContract | None = None,
        policy: EscalationPolicy | None = None,
    ) -> ArbitrationEvaluationResult:
        try:
            active_policy = EscalationPolicy() if policy is None else policy
            source_bindings = _source_bindings(
                deterministic_binding=deterministic_binding,
                resolver_response=resolver_response,
                planner_response=planner_response,
            )
            conflicts = self._collect_conflicts(
                deterministic_binding=deterministic_binding,
                resolver_response=resolver_response,
                planner_response=planner_response,
                policy=active_policy,
            )
            escalation_decision = self._policy_decider.decide(
                deterministic_binding=deterministic_binding,
                resolver_response=resolver_response,
                planner_response=planner_response,
                conflicts=conflicts,
                policy=active_policy,
            )
            selection = self._select_resolution(
                escalation_decision=escalation_decision,
                deterministic_binding=deterministic_binding,
                resolver_response=resolver_response,
                planner_response=planner_response,
            )
            signal_status = self._signal_status(
                deterministic_binding=deterministic_binding,
                resolver_response=resolver_response,
                planner_response=planner_response,
            )
            outcome = ArbitrationOutcome(
                status=_arbitration_status(
                    escalation_decision=escalation_decision,
                    selected_source=selection[0],
                    signal_status=signal_status,
                ),
                summary=escalation_decision.summary,
                selected_source=selection[0],
                escalation_decision=escalation_decision,
                selected_candidate_id=selection[1],
                selected_candidate_label=selection[2],
                selected_target_label=selection[3],
                selected_action_type=selection[4],
                selected_confidence=selection[5],
                signal_status=signal_status,
                conflicts=conflicts,
                metadata={
                    "conflict_kinds": tuple(conflict.kind.value for conflict in conflicts),
                    "conflict_count": len(conflicts),
                    "reason_codes": escalation_decision.reason_codes,
                    "selected_rule_id": escalation_decision.metadata.get("selected_rule_id"),
                    "preferred_source": (
                        None
                        if escalation_decision.preferred_source is None
                        else escalation_decision.preferred_source.value
                    ),
                    "evaluated_sources": tuple(source.value for source in source_bindings),
                    "evaluated_source_pairs": tuple(
                        f"{left_source.value}->{right_source.value}"
                        for left_source, right_source in _source_pairs(source_bindings)
                    ),
                    "observe_only": True,
                    "non_executing": True,
                },
            )
        except Exception as exc:  # noqa: BLE001 - arbitration must remain failure-safe
            _LOGGER.exception("AI arbitration failed and returned a failure-safe result.")
            return ArbitrationEvaluationResult.failure(
                arbitrator_name=self.arbitrator_name,
                error_code="ai_arbitration_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__, "exception_stage": "arbitrate"},
            )
        return ArbitrationEvaluationResult.ok(
            arbitrator_name=self.arbitrator_name,
            outcome=outcome,
            details={
                "status": outcome.status.value,
                "signal_status": outcome.signal_status.value,
                "selected_source": None if outcome.selected_source is None else outcome.selected_source.value,
                "selected_rule_id": outcome.escalation_decision.metadata.get("selected_rule_id"),
            },
        )

    def _collect_conflicts(
        self,
        *,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        resolver_response: ResolverResponseContract | None,
        planner_response: PlannerResponseContract | None,
        policy: EscalationPolicy,
    ) -> tuple[ArbitrationConflict, ...]:
        conflicts: list[ArbitrationConflict] = []
        if deterministic_binding is None:
            conflicts.append(
                _conflict(
                    kind=ArbitrationConflictKind.missing_contract,
                    summary="Deterministic candidate binding is unavailable for arbitration.",
                    sources=(ArbitrationSource.deterministic_pipeline,),
                )
            )
        elif deterministic_binding.completeness_status != "available":
            conflicts.append(
                _conflict(
                    kind=ArbitrationConflictKind.incomplete_contract,
                    summary="Deterministic candidate binding is incomplete.",
                    sources=(ArbitrationSource.deterministic_pipeline,),
                    candidate_ids=(deterministic_binding.candidate_id,),
                )
            )

        if resolver_response is not None and resolver_response.signal_status is not AiArchitectureSignalStatus.available:
            conflicts.append(
                _conflict(
                    kind=ArbitrationConflictKind.incomplete_contract,
                    summary="Resolver response binding is incomplete.",
                    sources=(ArbitrationSource.local_visual_resolver,),
                    candidate_ids=_candidate_ids_from_response(resolver_response),
                )
            )
        if planner_response is not None and planner_response.signal_status is not AiArchitectureSignalStatus.available:
            conflicts.append(
                _conflict(
                    kind=ArbitrationConflictKind.incomplete_contract,
                    summary="Planner response binding is incomplete.",
                    sources=(ArbitrationSource.cloud_planner,),
                    candidate_ids=_candidate_ids_from_response(planner_response),
                )
            )
        if planner_response is not None and planner_response.live_execution_requested:
            conflicts.append(
                _conflict(
                    kind=ArbitrationConflictKind.safety_ineligibility,
                    summary="Planner response requested live execution in a non-executing architecture phase.",
                    sources=(ArbitrationSource.cloud_planner,),
                    candidate_ids=_candidate_ids_from_response(planner_response),
                )
            )

        source_bindings = _source_bindings(
            deterministic_binding=deterministic_binding,
            resolver_response=resolver_response,
            planner_response=planner_response,
        )
        for left_source, right_source in _source_pairs(source_bindings):
            conflicts.extend(
                _candidate_pair_conflicts(
                    left_source=left_source,
                    left_binding=source_bindings[left_source],
                    right_source=right_source,
                    right_binding=source_bindings[right_source],
                )
            )

        response_entries = _response_entries(
            resolver_response=resolver_response,
            planner_response=planner_response,
        )
        conflicts.extend(
            _response_attribute_conflicts(
                response_entries,
                attribute_name="target_label",
                conflict_kind=ArbitrationConflictKind.target_label_mismatch,
                summary="AI sources selected different target labels.",
            )
        )
        conflicts.extend(
            _response_attribute_conflicts(
                response_entries,
                attribute_name="action_type",
                conflict_kind=ArbitrationConflictKind.action_mismatch,
                summary="AI sources selected different action types.",
            )
        )

        conflicts.extend(
            _confidence_conflicts(
                deterministic_binding=deterministic_binding,
                resolver_response=resolver_response,
                planner_response=planner_response,
                tolerance=policy.confidence_disagreement_tolerance,
            )
        )
        return tuple(sorted(conflicts, key=_conflict_sort_key))

    def _select_resolution(
        self,
        *,
        escalation_decision: EscalationDecision,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        resolver_response: ResolverResponseContract | None,
        planner_response: PlannerResponseContract | None,
    ) -> tuple[
        ArbitrationSource | None,
        str | None,
        str | None,
        SharedTargetLabel | None,
        AiSuggestedActionType | None,
        float | None,
    ]:
        if (
            escalation_decision.action is EscalationAction.stay_deterministic
            and deterministic_binding is not None
        ):
            return (
                ArbitrationSource.deterministic_pipeline,
                deterministic_binding.candidate_id,
                deterministic_binding.candidate_label,
                SharedTargetLabel.candidate_center,
                AiSuggestedActionType.candidate_select,
                deterministic_binding.confidence,
            )
        if (
            escalation_decision.action is EscalationAction.ask_local_resolver
            and resolver_response is not None
            and resolver_response.signal_status is AiArchitectureSignalStatus.available
            and resolver_response.candidate_binding is not None
        ):
            return (
                ArbitrationSource.local_visual_resolver,
                resolver_response.candidate_binding.candidate_id,
                resolver_response.candidate_binding.candidate_label,
                resolver_response.target_label,
                resolver_response.action_type,
                resolver_response.confidence,
            )
        if (
            escalation_decision.action is EscalationAction.escalate_to_cloud_planner
            and planner_response is not None
            and planner_response.signal_status is AiArchitectureSignalStatus.available
            and planner_response.candidate_binding is not None
        ):
            return (
                ArbitrationSource.cloud_planner,
                planner_response.candidate_binding.candidate_id,
                planner_response.candidate_binding.candidate_label,
                planner_response.target_label,
                planner_response.action_type,
                planner_response.confidence,
            )
        return None, None, None, None, None, None

    def _signal_status(
        self,
        *,
        deterministic_binding: SharedCandidateOntologyBinding | None,
        resolver_response: ResolverResponseContract | None,
        planner_response: PlannerResponseContract | None,
    ) -> AiArchitectureSignalStatus:
        signal_statuses: list[AiArchitectureSignalStatus] = []
        if deterministic_binding is None:
            signal_statuses.append(AiArchitectureSignalStatus.absent)
        elif deterministic_binding.completeness_status != "available":
            signal_statuses.append(AiArchitectureSignalStatus.partial)
        else:
            signal_statuses.append(AiArchitectureSignalStatus.available)
        if resolver_response is not None:
            signal_statuses.append(resolver_response.signal_status)
        if planner_response is not None:
            signal_statuses.append(planner_response.signal_status)
        if any(status is AiArchitectureSignalStatus.partial for status in signal_statuses):
            return AiArchitectureSignalStatus.partial
        if any(status is AiArchitectureSignalStatus.absent for status in signal_statuses):
            return AiArchitectureSignalStatus.partial
        return AiArchitectureSignalStatus.available


def _decision(
    *,
    action: EscalationAction,
    preferred_source: ArbitrationSource | None,
    summary: str,
    reason_codes: tuple[str, ...] | list[str],
    rule_id: str,
    metadata: Mapping[str, object] | None = None,
) -> EscalationDecision:
    return EscalationDecision(
        action=action,
        summary=summary,
        preferred_source=preferred_source,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        metadata={
            "selected_rule_id": rule_id,
            **({} if metadata is None else dict(metadata)),
        },
    )


def _conflict(
    *,
    kind: ArbitrationConflictKind,
    summary: str,
    sources: tuple[ArbitrationSource, ...],
    candidate_ids: tuple[str, ...] = (),
    metadata: Mapping[str, object] | None = None,
) -> ArbitrationConflict:
    return ArbitrationConflict(
        kind=kind,
        summary=summary,
        sources=sources,
        candidate_ids=candidate_ids,
        metadata={} if metadata is None else metadata,
    )


def _candidate_pair_conflicts(
    *,
    left_source: ArbitrationSource,
    left_binding: SharedCandidateOntologyBinding | None,
    right_source: ArbitrationSource,
    right_binding: SharedCandidateOntologyBinding | None,
) -> tuple[ArbitrationConflict, ...]:
    if left_binding is None or right_binding is None:
        return ()
    conflicts: list[ArbitrationConflict] = []
    if left_binding.candidate_id != right_binding.candidate_id:
        conflicts.append(
            _conflict(
                kind=ArbitrationConflictKind.candidate_reference_mismatch,
                summary="Arbitration sources referenced different candidate identifiers.",
                sources=(left_source, right_source),
                candidate_ids=(left_binding.candidate_id, right_binding.candidate_id),
            )
        )
    if left_binding.shared_candidate_label != right_binding.shared_candidate_label:
        conflicts.append(
            _conflict(
                kind=ArbitrationConflictKind.label_mismatch,
                summary="Arbitration sources mapped the target to different shared candidate labels.",
                sources=(left_source, right_source),
                candidate_ids=(left_binding.candidate_id, right_binding.candidate_id),
            )
        )
    return tuple(conflicts)


def _response_attribute_conflicts(
    response_entries: Mapping[
        ArbitrationSource,
        PlannerResponseContract | ResolverResponseContract,
    ],
    *,
    attribute_name: str,
    conflict_kind: ArbitrationConflictKind,
    summary: str,
) -> tuple[ArbitrationConflict, ...]:
    conflicts: list[ArbitrationConflict] = []
    for left_source, right_source in _source_pairs(response_entries):
        left_response = response_entries[left_source]
        right_response = response_entries[right_source]
        left_value = getattr(left_response, attribute_name)
        right_value = getattr(right_response, attribute_name)
        if left_value is None or right_value is None or left_value is right_value:
            continue
        conflicts.append(
            _conflict(
                kind=conflict_kind,
                summary=summary,
                sources=(left_source, right_source),
                candidate_ids=tuple(
                    dict.fromkeys(
                        _candidate_ids_from_response(left_response)
                        + _candidate_ids_from_response(right_response)
                    )
                ),
                metadata={
                    "attribute_name": attribute_name,
                    "left_value": getattr(left_value, "value", left_value),
                    "right_value": getattr(right_value, "value", right_value),
                },
            )
        )
    return tuple(conflicts)


def _confidence_conflicts(
    *,
    deterministic_binding: SharedCandidateOntologyBinding | None,
    resolver_response: ResolverResponseContract | None,
    planner_response: PlannerResponseContract | None,
    tolerance: float,
) -> tuple[ArbitrationConflict, ...]:
    confidence_entries = _confidence_entries(
        deterministic_binding=deterministic_binding,
        resolver_response=resolver_response,
        planner_response=planner_response,
    )
    conflicts: list[ArbitrationConflict] = []
    for left_source, right_source in _source_pairs(confidence_entries):
        left_confidence, left_candidate_id = confidence_entries[left_source]
        right_confidence, right_candidate_id = confidence_entries[right_source]
        if (
            left_confidence is None
            or right_confidence is None
            or abs(left_confidence - right_confidence) <= tolerance
        ):
            continue
        conflicts.append(
            _conflict(
                kind=ArbitrationConflictKind.confidence_disagreement,
                summary="Arbitration sources disagreed materially on confidence.",
                sources=(left_source, right_source),
                candidate_ids=tuple(
                    candidate_id
                    for candidate_id in (left_candidate_id, right_candidate_id)
                    if candidate_id is not None
                ),
                metadata={
                    "left_confidence": left_confidence,
                    "right_confidence": right_confidence,
                    "tolerance": tolerance,
                },
            )
        )
    return tuple(conflicts)


def _source_bindings(
    *,
    deterministic_binding: SharedCandidateOntologyBinding | None,
    resolver_response: ResolverResponseContract | None,
    planner_response: PlannerResponseContract | None,
) -> Mapping[ArbitrationSource, SharedCandidateOntologyBinding]:
    bindings: dict[ArbitrationSource, SharedCandidateOntologyBinding] = {}
    if deterministic_binding is not None:
        bindings[ArbitrationSource.deterministic_pipeline] = deterministic_binding
    if resolver_response is not None and resolver_response.candidate_binding is not None:
        bindings[ArbitrationSource.local_visual_resolver] = resolver_response.candidate_binding
    if planner_response is not None and planner_response.candidate_binding is not None:
        bindings[ArbitrationSource.cloud_planner] = planner_response.candidate_binding
    return bindings


def _response_entries(
    *,
    resolver_response: ResolverResponseContract | None,
    planner_response: PlannerResponseContract | None,
) -> Mapping[ArbitrationSource, PlannerResponseContract | ResolverResponseContract]:
    entries: dict[ArbitrationSource, PlannerResponseContract | ResolverResponseContract] = {}
    if resolver_response is not None:
        entries[ArbitrationSource.local_visual_resolver] = resolver_response
    if planner_response is not None:
        entries[ArbitrationSource.cloud_planner] = planner_response
    return entries


def _confidence_entries(
    *,
    deterministic_binding: SharedCandidateOntologyBinding | None,
    resolver_response: ResolverResponseContract | None,
    planner_response: PlannerResponseContract | None,
) -> Mapping[ArbitrationSource, tuple[float | None, str | None]]:
    entries: dict[ArbitrationSource, tuple[float | None, str | None]] = {}
    if deterministic_binding is not None:
        entries[ArbitrationSource.deterministic_pipeline] = (
            deterministic_binding.confidence,
            deterministic_binding.candidate_id,
        )
    if resolver_response is not None:
        entries[ArbitrationSource.local_visual_resolver] = (
            resolver_response.confidence,
            None
            if resolver_response.candidate_binding is None
            else resolver_response.candidate_binding.candidate_id,
        )
    if planner_response is not None:
        entries[ArbitrationSource.cloud_planner] = (
            planner_response.confidence,
            None
            if planner_response.candidate_binding is None
            else planner_response.candidate_binding.candidate_id,
        )
    return entries


def _source_pairs(
    values: Mapping[ArbitrationSource, object],
) -> tuple[tuple[ArbitrationSource, ArbitrationSource], ...]:
    ordered_sources = tuple(_ordered_sources(values))
    return tuple(combinations(ordered_sources, 2))


def _ordered_sources(
    values: Mapping[ArbitrationSource, object],
) -> tuple[ArbitrationSource, ...]:
    ordered: list[ArbitrationSource] = []
    seen: set[ArbitrationSource] = set()
    for source in ArbitrationSource:
        if source in values:
            ordered.append(source)
            seen.add(source)
    extras = sorted((source for source in values if source not in seen), key=lambda item: item.value)
    ordered.extend(extras)
    return tuple(ordered)


def _candidate_ids_from_response(
    response: PlannerResponseContract | ResolverResponseContract,
) -> tuple[str, ...]:
    if response.candidate_binding is None:
        return ()
    return (response.candidate_binding.candidate_id,)


def _arbitration_status(
    *,
    escalation_decision: EscalationDecision,
    selected_source: ArbitrationSource | None,
    signal_status: AiArchitectureSignalStatus,
) -> ArbitrationStatus:
    if escalation_decision.action is EscalationAction.block_for_user_confirmation:
        return ArbitrationStatus.blocked
    if selected_source is not None:
        return ArbitrationStatus.resolved
    if signal_status is AiArchitectureSignalStatus.partial:
        return ArbitrationStatus.partial
    return ArbitrationStatus.escalated


def _is_high_risk(binding: SharedCandidateOntologyBinding | None) -> bool:
    return (
        binding is not None
        and binding.selection_risk_level is CandidateSelectionRiskLevel.high
    )


def _conflict_sort_key(conflict: ArbitrationConflict) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    return (
        conflict.kind.value,
        tuple(source.value for source in conflict.sources),
        conflict.candidate_ids,
    )
