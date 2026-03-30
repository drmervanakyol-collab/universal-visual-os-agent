"""Public result models for safety-first dry-run action evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.semantics.state import SemanticStateSnapshot

from .models import (
    ActionIntent,
    ActionIntentStatus,
    ActionRequirementStatus,
)
from .scaffolding_models import ActionIntentScaffoldView


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
            raise ValueError(
                "Successful dry-run batch results must include scaffold_view and evaluation_view."
            )
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


__all__ = [
    "DryRunActionBatchResult",
    "DryRunActionCheckOutcome",
    "DryRunActionDisposition",
    "DryRunActionEvaluation",
    "DryRunActionEvaluationResult",
    "DryRunActionEvaluationView",
]
