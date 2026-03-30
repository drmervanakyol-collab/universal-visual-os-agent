"""Safety-first dry-run evaluation for scaffolded action intents."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.actions.models import (
    ActionIntent,
    ActionIntentStatus,
    ActionPrecondition,
    ActionRequirementStatus,
    ActionResult,
    ActionSafetyGate,
    ActionTargetValidation,
)
from universal_visual_os_agent.actions.scaffolding import ActionIntentScaffoldView
from universal_visual_os_agent.semantics.state import SemanticCandidate, SemanticStateSnapshot


class DryRunActionDisposition(StrEnum):
    """Stable dispositions produced by the dry-run action engine."""

    would_execute = "would_execute"
    would_block = "would_block"
    incomplete = "incomplete"
    rejected = "rejected"


@dataclass(slots=True, frozen=True, kw_only=True)
class DryRunActionCheckOutcome:
    """One evaluated precondition, target validation, or safety gate."""

    check_id: str
    summary: str
    status: ActionRequirementStatus
    reason: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.check_id:
            raise ValueError("check_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.reason:
            raise ValueError("reason must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class DryRunActionEvaluation:
    """Structured dry-run evaluation for a single action intent."""

    intent_id: str
    action_type: str
    disposition: DryRunActionDisposition
    summary: str
    source_intent_status: ActionIntentStatus
    candidate_id: str | None = None
    would_execute: bool = False
    simulated: bool = True
    non_executing: bool = True
    blocking_reasons: tuple[str, ...] = ()
    missing_precondition_ids: tuple[str, ...] = ()
    failed_target_validation_ids: tuple[str, ...] = ()
    blocked_safety_gate_ids: tuple[str, ...] = ()
    pending_safety_gate_ids: tuple[str, ...] = ()
    precondition_outcomes: tuple[DryRunActionCheckOutcome, ...] = ()
    target_validation_outcomes: tuple[DryRunActionCheckOutcome, ...] = ()
    safety_gate_outcomes: tuple[DryRunActionCheckOutcome, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.intent_id:
            raise ValueError("intent_id must not be empty.")
        if not self.action_type:
            raise ValueError("action_type must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.would_execute != (self.disposition is DryRunActionDisposition.would_execute):
            raise ValueError("would_execute must match whether disposition is would_execute.")
        if not self.simulated:
            raise ValueError("Dry-run evaluations must remain simulated.")
        if not self.non_executing:
            raise ValueError("Dry-run evaluations must remain non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class DryRunActionEvaluationResult:
    """Single-intent result from the dry-run action engine."""

    engine_name: str
    success: bool
    source_intent: ActionIntent | None = None
    source_snapshot: SemanticStateSnapshot | None = None
    evaluation: DryRunActionEvaluation | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.engine_name:
            raise ValueError("engine_name must not be empty.")
        if self.success and (self.source_intent is None or self.evaluation is None):
            raise ValueError("Successful dry-run evaluation must include source_intent and evaluation.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed dry-run evaluation must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful dry-run evaluation must not include error details.")
        if not self.success and self.evaluation is not None:
            raise ValueError("Failed dry-run evaluation must not include evaluation.")

    @classmethod
    def ok(
        cls,
        *,
        engine_name: str,
        source_intent: ActionIntent,
        source_snapshot: SemanticStateSnapshot | None,
        evaluation: DryRunActionEvaluation,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            engine_name=engine_name,
            success=True,
            source_intent=source_intent,
            source_snapshot=source_snapshot,
            evaluation=evaluation,
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


@dataclass(slots=True, frozen=True, kw_only=True)
class DryRunActionEvaluationView:
    """Stable downstream-facing view of evaluated scaffolded intents."""

    snapshot_id: str
    evaluations: tuple[DryRunActionEvaluation, ...]
    total_intent_count: int
    would_execute_count: int
    would_block_count: int
    incomplete_count: int
    rejected_count: int
    signal_status: str = "absent"
    sort_order: str = "candidate_rank_then_intent_id"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            raise ValueError("snapshot_id must not be empty.")
        if self.total_intent_count != len(self.evaluations):
            raise ValueError("total_intent_count must match len(evaluations).")
        if (
            self.would_execute_count
            + self.would_block_count
            + self.incomplete_count
            + self.rejected_count
            != len(self.evaluations)
        ):
            raise ValueError("Disposition counts must match len(evaluations).")
        if self.signal_status not in {"available", "partial", "absent"}:
            raise ValueError("signal_status must be available, partial, or absent.")


@dataclass(slots=True, frozen=True, kw_only=True)
class DryRunActionBatchResult:
    """Structured batch result for dry-run evaluation of scaffolded intents."""

    engine_name: str
    success: bool
    source_snapshot: SemanticStateSnapshot | None = None
    scaffold_view: ActionIntentScaffoldView | None = None
    evaluation_view: DryRunActionEvaluationView | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.engine_name:
            raise ValueError("engine_name must not be empty.")
        if self.success and (self.scaffold_view is None or self.evaluation_view is None):
            raise ValueError("Successful dry-run batch results must include scaffold_view and evaluation_view.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed dry-run batch results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful dry-run batch results must not include error details.")
        if not self.success and self.evaluation_view is not None:
            raise ValueError("Failed dry-run batch results must not include evaluation_view.")

    @classmethod
    def ok(
        cls,
        *,
        engine_name: str,
        source_snapshot: SemanticStateSnapshot | None,
        scaffold_view: ActionIntentScaffoldView,
        evaluation_view: DryRunActionEvaluationView,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            engine_name=engine_name,
            success=True,
            source_snapshot=source_snapshot,
            scaffold_view=scaffold_view,
            evaluation_view=evaluation_view,
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


class ObserveOnlyDryRunActionEngine:
    """Evaluate scaffolded action intents without ever performing OS input."""

    engine_name = "ObserveOnlyDryRunActionEngine"
    supported_action_types = frozenset({"candidate_select"})

    def evaluate_intent(
        self,
        intent: ActionIntent,
        *,
        snapshot: SemanticStateSnapshot | None = None,
    ) -> DryRunActionEvaluationResult:
        try:
            evaluation = self._evaluate_intent(intent, snapshot=snapshot)
        except Exception as exc:  # noqa: BLE001 - dry-run evaluation must remain failure-safe
            return DryRunActionEvaluationResult.failure(
                engine_name=self.engine_name,
                error_code="dry_run_action_engine_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return DryRunActionEvaluationResult.ok(
            engine_name=self.engine_name,
            source_intent=intent,
            source_snapshot=snapshot,
            evaluation=evaluation,
            details={
                "disposition": evaluation.disposition.value,
                "would_execute": evaluation.would_execute,
            },
        )

    def evaluate_scaffold(
        self,
        scaffold_view: ActionIntentScaffoldView,
        *,
        snapshot: SemanticStateSnapshot | None = None,
    ) -> DryRunActionBatchResult:
        if (
            scaffold_view.metadata.get("observe_only") is not True
            or scaffold_view.metadata.get("dry_run_only") is not True
            or scaffold_view.metadata.get("non_executing") is not True
        ):
            return DryRunActionBatchResult.failure(
                engine_name=self.engine_name,
                error_code="action_intent_scaffold_unavailable",
                error_message="Dry-run action evaluation requires an observe-only non-executing scaffold view.",
            )

        try:
            evaluations = tuple(
                self._evaluate_intent(intent, snapshot=snapshot)
                for intent in scaffold_view.intents
            )
            disposition_counts = Counter(evaluation.disposition.value for evaluation in evaluations)
            evaluation_view = DryRunActionEvaluationView(
                snapshot_id=snapshot.snapshot_id if snapshot is not None else scaffold_view.snapshot_id,
                evaluations=evaluations,
                total_intent_count=len(evaluations),
                would_execute_count=disposition_counts.get(
                    DryRunActionDisposition.would_execute.value,
                    0,
                ),
                would_block_count=disposition_counts.get(
                    DryRunActionDisposition.would_block.value,
                    0,
                ),
                incomplete_count=disposition_counts.get(
                    DryRunActionDisposition.incomplete.value,
                    0,
                ),
                rejected_count=disposition_counts.get(
                    DryRunActionDisposition.rejected.value,
                    0,
                ),
                signal_status=_view_signal_status(scaffold_view, evaluations=evaluations),
                metadata={
                    "observe_only": True,
                    "analysis_only": True,
                    "non_executing": True,
                    "simulated": True,
                    "source_scaffold_snapshot_id": scaffold_view.snapshot_id,
                    "evaluation_snapshot_id": (
                        snapshot.snapshot_id if snapshot is not None else scaffold_view.snapshot_id
                    ),
                    "sorted_intent_ids": tuple(
                        evaluation.intent_id for evaluation in evaluations
                    ),
                    "would_execute_intent_ids": tuple(
                        evaluation.intent_id
                        for evaluation in evaluations
                        if evaluation.disposition is DryRunActionDisposition.would_execute
                    ),
                    "would_block_intent_ids": tuple(
                        evaluation.intent_id
                        for evaluation in evaluations
                        if evaluation.disposition is DryRunActionDisposition.would_block
                    ),
                    "incomplete_intent_ids": tuple(
                        evaluation.intent_id
                        for evaluation in evaluations
                        if evaluation.disposition is DryRunActionDisposition.incomplete
                    ),
                    "rejected_intent_ids": tuple(
                        evaluation.intent_id
                        for evaluation in evaluations
                        if evaluation.disposition is DryRunActionDisposition.rejected
                    ),
                    "input_signal_status": scaffold_view.signal_status,
                    "evaluated_with_snapshot": snapshot is not None,
                },
            )
        except Exception as exc:  # noqa: BLE001 - dry-run evaluation must remain failure-safe
            return DryRunActionBatchResult.failure(
                engine_name=self.engine_name,
                error_code="dry_run_action_engine_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return DryRunActionBatchResult.ok(
            engine_name=self.engine_name,
            source_snapshot=snapshot,
            scaffold_view=scaffold_view,
            evaluation_view=evaluation_view,
            details={
                "evaluated_intent_count": len(evaluations),
                "signal_status": evaluation_view.signal_status,
            },
        )

    def execute(self, action: ActionIntent) -> ActionResult:
        """Adapt dry-run evaluation to the generic executor contract."""

        result = self.evaluate_intent(action)
        if not result.success or result.evaluation is None:
            return ActionResult(
                accepted=False,
                simulated=True,
                details={
                    "dry_run_engine": self.engine_name,
                    "success": False,
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                },
            )

        evaluation = result.evaluation
        return ActionResult(
            accepted=evaluation.would_execute,
            simulated=True,
            details={
                "dry_run_engine": self.engine_name,
                "success": True,
                "disposition": evaluation.disposition.value,
                "summary": evaluation.summary,
                "blocking_reasons": evaluation.blocking_reasons,
                "non_executing": evaluation.non_executing,
            },
        )

    def _evaluate_intent(
        self,
        intent: ActionIntent,
        *,
        snapshot: SemanticStateSnapshot | None,
    ) -> DryRunActionEvaluation:
        rejection_reasons = _rejection_reasons(
            intent,
            supported_action_types=self.supported_action_types,
        )
        snapshot_candidate = _lookup_snapshot_candidate(snapshot, intent.candidate_id)
        precondition_outcomes = _evaluate_preconditions(
            intent.precondition_requirements,
            intent=intent,
            snapshot_candidate=snapshot_candidate,
            snapshot=snapshot,
        )
        target_validation_outcomes = _evaluate_target_validations(
            intent.target_validation_requirements,
            intent=intent,
            snapshot_candidate=snapshot_candidate,
            snapshot=snapshot,
        )
        safety_gate_outcomes = _evaluate_safety_gates(intent.safety_gating_requirements, intent=intent)

        missing_precondition_ids = tuple(
            outcome.check_id
            for outcome in precondition_outcomes
            if outcome.status is ActionRequirementStatus.blocked
        )
        failed_target_validation_ids = tuple(
            outcome.check_id
            for outcome in target_validation_outcomes
            if outcome.status is ActionRequirementStatus.blocked
        )
        blocked_safety_gate_ids = tuple(
            outcome.check_id
            for outcome in safety_gate_outcomes
            if outcome.status is ActionRequirementStatus.blocked
        )
        pending_safety_gate_ids = tuple(
            outcome.check_id
            for outcome in safety_gate_outcomes
            if outcome.status is ActionRequirementStatus.pending
        )

        disposition, blocking_reasons = _determine_disposition(
            intent=intent,
            rejection_reasons=rejection_reasons,
            missing_precondition_ids=missing_precondition_ids,
            failed_target_validation_ids=failed_target_validation_ids,
            blocked_safety_gate_ids=blocked_safety_gate_ids,
            precondition_outcomes=precondition_outcomes,
            target_validation_outcomes=target_validation_outcomes,
            safety_gate_outcomes=safety_gate_outcomes,
        )

        return DryRunActionEvaluation(
            intent_id=intent.intent_id,
            action_type=intent.action_type,
            disposition=disposition,
            summary=_evaluation_summary(disposition, blocking_reasons=blocking_reasons),
            source_intent_status=intent.status,
            candidate_id=intent.candidate_id,
            would_execute=disposition is DryRunActionDisposition.would_execute,
            simulated=True,
            non_executing=True,
            blocking_reasons=blocking_reasons,
            missing_precondition_ids=missing_precondition_ids,
            failed_target_validation_ids=failed_target_validation_ids,
            blocked_safety_gate_ids=blocked_safety_gate_ids,
            pending_safety_gate_ids=pending_safety_gate_ids,
            precondition_outcomes=precondition_outcomes,
            target_validation_outcomes=target_validation_outcomes,
            safety_gate_outcomes=safety_gate_outcomes,
            metadata={
                **dict(intent.metadata),
                "dry_run_evaluated": True,
                "dry_run_engine_name": self.engine_name,
                "dry_run_disposition": disposition.value,
                "evaluated_with_snapshot": snapshot is not None,
                "evaluation_snapshot_id": snapshot.snapshot_id if snapshot is not None else None,
                "source_intent_status": intent.status.value,
                "would_execute": disposition is DryRunActionDisposition.would_execute,
                "non_executing": True,
                "simulated": True,
            },
        )


def _view_signal_status(
    scaffold_view: ActionIntentScaffoldView,
    *,
    evaluations: tuple[DryRunActionEvaluation, ...],
) -> str:
    if not evaluations:
        return "absent"
    if scaffold_view.signal_status == "partial":
        return "partial"
    if any(
        evaluation.disposition in {DryRunActionDisposition.incomplete, DryRunActionDisposition.rejected}
        for evaluation in evaluations
    ):
        return "partial"
    return "available"


def _rejection_reasons(
    intent: ActionIntent,
    *,
    supported_action_types: frozenset[str],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if intent.action_type not in supported_action_types:
        reasons.append("Action type is not supported by the dry-run action engine.")
    if intent.metadata.get("action_intent_scaffolded") is not True:
        reasons.append("Intent did not originate from the Phase 5A action-intent scaffold.")
    if intent.metadata.get("observe_only") is not True:
        reasons.append("Intent metadata did not preserve observe-only provenance.")
    if intent.metadata.get("non_executing") is not True:
        reasons.append("Intent metadata did not preserve non-executing dry-run semantics.")
    if not intent.dry_run_only or intent.executable or not intent.observe_only_source:
        reasons.append("Intent violated the dry-run safety contract.")
    return tuple(reasons)


def _lookup_snapshot_candidate(
    snapshot: SemanticStateSnapshot | None,
    candidate_id: str | None,
) -> SemanticCandidate | None:
    if snapshot is None or candidate_id is None:
        return None
    return snapshot.get_candidate(candidate_id)


def _evaluate_preconditions(
    requirements: tuple[ActionPrecondition, ...],
    *,
    intent: ActionIntent,
    snapshot_candidate: SemanticCandidate | None,
    snapshot: SemanticStateSnapshot | None,
) -> tuple[DryRunActionCheckOutcome, ...]:
    outcomes: list[DryRunActionCheckOutcome] = []
    for requirement in requirements:
        status = requirement.status
        if (
            requirement.requirement_id == "candidate_visible"
            and snapshot is not None
            and status is ActionRequirementStatus.satisfied
        ):
            status = (
                ActionRequirementStatus.satisfied
                if snapshot_candidate is not None and snapshot_candidate.visible
                else ActionRequirementStatus.blocked
            )
        elif (
            requirement.requirement_id == "candidate_score_available"
            and status is ActionRequirementStatus.satisfied
        ):
            score = intent.candidate_score
            if snapshot_candidate is not None and snapshot_candidate.confidence is not None:
                score = snapshot_candidate.confidence
            status = (
                ActionRequirementStatus.satisfied
                if score is not None
                else ActionRequirementStatus.blocked
            )
        elif (
            requirement.requirement_id == "snapshot_candidate_present"
            and snapshot is not None
            and status is ActionRequirementStatus.satisfied
        ):
            status = (
                ActionRequirementStatus.satisfied
                if snapshot_candidate is not None
                else ActionRequirementStatus.blocked
            )
        outcomes.append(
            DryRunActionCheckOutcome(
                check_id=requirement.requirement_id,
                summary=requirement.summary,
                status=status,
                reason=_status_reason(
                    category="Precondition",
                    summary=requirement.summary,
                    status=status,
                ),
                metadata=requirement.metadata,
            )
        )
    return tuple(outcomes)


def _evaluate_target_validations(
    validations: tuple[ActionTargetValidation, ...],
    *,
    intent: ActionIntent,
    snapshot_candidate: SemanticCandidate | None,
    snapshot: SemanticStateSnapshot | None,
) -> tuple[DryRunActionCheckOutcome, ...]:
    layout_region_ids = (
        {region.region_id for region in snapshot.layout_regions}
        if snapshot is not None
        else set()
    )
    source_layout_region_id = intent.metadata.get("source_layout_region_id")
    completeness_status = intent.metadata.get("candidate_exposure_completeness_status")
    outcomes: list[DryRunActionCheckOutcome] = []
    for validation in validations:
        status = validation.status
        if (
            validation.validation_id == "candidate_id_consistency"
            and snapshot is not None
            and status is ActionRequirementStatus.satisfied
        ):
            status = (
                ActionRequirementStatus.satisfied
                if snapshot_candidate is not None
                else ActionRequirementStatus.blocked
            )
        elif (
            validation.validation_id == "source_layout_region_consistency"
            and snapshot is not None
            and status is ActionRequirementStatus.satisfied
        ):
            status = (
                ActionRequirementStatus.satisfied
                if isinstance(source_layout_region_id, str) and source_layout_region_id in layout_region_ids
                else ActionRequirementStatus.blocked
            )
        elif (
            validation.validation_id == "candidate_completeness"
            and status is ActionRequirementStatus.satisfied
        ):
            status = (
                ActionRequirementStatus.satisfied
                if completeness_status == "available"
                else ActionRequirementStatus.blocked
            )
        outcomes.append(
            DryRunActionCheckOutcome(
                check_id=validation.validation_id,
                summary=validation.summary,
                status=status,
                reason=_status_reason(
                    category="Target validation",
                    summary=validation.summary,
                    status=status,
                ),
                metadata=validation.metadata,
            )
        )
    return tuple(outcomes)


def _evaluate_safety_gates(
    gates: tuple[ActionSafetyGate, ...],
    *,
    intent: ActionIntent,
) -> tuple[DryRunActionCheckOutcome, ...]:
    outcomes: list[DryRunActionCheckOutcome] = []
    for gate in gates:
        status = gate.status
        if gate.gate_id == "observe_only_origin_confirmed":
            status = (
                ActionRequirementStatus.blocked
                if gate.status is ActionRequirementStatus.blocked
                else (
                    ActionRequirementStatus.satisfied
                    if intent.observe_only_source and intent.metadata.get("observe_only") is True
                    else ActionRequirementStatus.blocked
                )
            )
        elif gate.gate_id == "dry_run_only_enforced":
            status = (
                ActionRequirementStatus.blocked
                if gate.status is ActionRequirementStatus.blocked
                else (
                    ActionRequirementStatus.satisfied
                    if intent.dry_run_only and not intent.executable
                    else ActionRequirementStatus.blocked
                )
            )
        elif gate.gate_id == "explicit_execution_enablement_required":
            status = (
                ActionRequirementStatus.blocked
                if gate.status is ActionRequirementStatus.blocked
                else ActionRequirementStatus.pending
            )
        outcomes.append(
            DryRunActionCheckOutcome(
                check_id=gate.gate_id,
                summary=gate.summary,
                status=status,
                reason=_status_reason(
                    category="Safety gate",
                    summary=gate.summary,
                    status=status,
                ),
                metadata=gate.metadata,
            )
        )
    return tuple(outcomes)


def _determine_disposition(
    *,
    intent: ActionIntent,
    rejection_reasons: tuple[str, ...],
    missing_precondition_ids: tuple[str, ...],
    failed_target_validation_ids: tuple[str, ...],
    blocked_safety_gate_ids: tuple[str, ...],
    precondition_outcomes: tuple[DryRunActionCheckOutcome, ...],
    target_validation_outcomes: tuple[DryRunActionCheckOutcome, ...],
    safety_gate_outcomes: tuple[DryRunActionCheckOutcome, ...],
) -> tuple[DryRunActionDisposition, tuple[str, ...]]:
    if rejection_reasons:
        return DryRunActionDisposition.rejected, rejection_reasons
    if intent.status is ActionIntentStatus.blocked or blocked_safety_gate_ids:
        return (
            DryRunActionDisposition.would_block,
            tuple(
                outcome.reason
                for outcome in safety_gate_outcomes
                if outcome.status is ActionRequirementStatus.blocked
            ),
        )
    if failed_target_validation_ids:
        return (
            DryRunActionDisposition.would_block,
            tuple(
                outcome.reason
                for outcome in target_validation_outcomes
                if outcome.status is ActionRequirementStatus.blocked
            ),
        )
    if (
        intent.status is ActionIntentStatus.incomplete
        or missing_precondition_ids
        or any(outcome.status is ActionRequirementStatus.pending for outcome in precondition_outcomes)
        or any(outcome.status is ActionRequirementStatus.pending for outcome in target_validation_outcomes)
    ):
        return (
            DryRunActionDisposition.incomplete,
            tuple(
                outcome.reason
                for outcome in (*precondition_outcomes, *target_validation_outcomes)
                if outcome.status is not ActionRequirementStatus.satisfied
            ),
        )
    return DryRunActionDisposition.would_execute, (
        "Dry-run checks passed; the engine would accept this intent for simulated handling only.",
    )


def _evaluation_summary(
    disposition: DryRunActionDisposition,
    *,
    blocking_reasons: tuple[str, ...],
) -> str:
    if disposition is DryRunActionDisposition.would_execute:
        return "Dry-run would accept this intent without performing any real OS action."
    if disposition is DryRunActionDisposition.would_block:
        return "Dry-run would block this intent because safety or target validation checks failed."
    if disposition is DryRunActionDisposition.incomplete:
        return "Dry-run could not fully evaluate this intent because required inputs were incomplete."
    return "Dry-run rejected this intent because it did not satisfy the scaffold-only safety contract."


def _status_reason(
    *,
    category: str,
    summary: str,
    status: ActionRequirementStatus,
) -> str:
    if status is ActionRequirementStatus.satisfied:
        return f"{category} satisfied: {summary}"
    if status is ActionRequirementStatus.pending:
        return f"{category} pending: {summary}"
    return f"{category} blocked: {summary}"
