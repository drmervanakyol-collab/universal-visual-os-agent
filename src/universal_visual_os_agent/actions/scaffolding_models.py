"""Public result models for observe-only action-intent scaffolding."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Self

from universal_visual_os_agent.semantics.candidate_exposure import CandidateExposureView
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot

from .models import ActionIntent


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionIntentScaffoldView:
    """Stable downstream-facing view of scaffolded action intents."""

    snapshot_id: str
    intents: tuple[ActionIntent, ...]
    total_exposed_candidate_count: int
    scaffolded_intent_count: int
    incomplete_intent_count: int
    blocked_intent_count: int
    signal_status: str = "absent"
    sort_order: str = "candidate_rank_then_candidate_id"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            raise ValueError("snapshot_id must not be empty.")
        if self.total_exposed_candidate_count < 0:
            raise ValueError("total_exposed_candidate_count must not be negative.")
        if self.scaffolded_intent_count < 0:
            raise ValueError("scaffolded_intent_count must not be negative.")
        if self.incomplete_intent_count < 0:
            raise ValueError("incomplete_intent_count must not be negative.")
        if self.blocked_intent_count < 0:
            raise ValueError("blocked_intent_count must not be negative.")
        if self.total_exposed_candidate_count != len(self.intents):
            raise ValueError("total_exposed_candidate_count must match len(intents).")
        if (
            self.scaffolded_intent_count
            + self.incomplete_intent_count
            + self.blocked_intent_count
            != len(self.intents)
        ):
            raise ValueError("Intent status counts must match len(intents).")
        if self.signal_status not in {"available", "partial", "absent"}:
            raise ValueError("signal_status must be available, partial, or absent.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionIntentScaffoldingResult:
    """Structured result for observe-only action-intent scaffolding."""

    scaffolder_name: str
    success: bool
    source_snapshot: SemanticStateSnapshot | None = None
    exposure_view: CandidateExposureView | None = None
    scaffold_view: ActionIntentScaffoldView | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scaffolder_name:
            raise ValueError("scaffolder_name must not be empty.")
        if self.success and (
            self.source_snapshot is None or self.exposure_view is None or self.scaffold_view is None
        ):
            raise ValueError(
                "Successful action scaffolding must include source_snapshot, exposure_view, and scaffold_view."
            )
        if not self.success and self.error_code is None:
            raise ValueError("Failed action scaffolding must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful action scaffolding must not include error details.")
        if not self.success and self.scaffold_view is not None:
            raise ValueError("Failed action scaffolding must not include scaffold_view.")

    @classmethod
    def ok(
        cls,
        *,
        scaffolder_name: str,
        source_snapshot: SemanticStateSnapshot,
        exposure_view: CandidateExposureView,
        scaffold_view: ActionIntentScaffoldView,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            scaffolder_name=scaffolder_name,
            success=True,
            source_snapshot=source_snapshot,
            exposure_view=exposure_view,
            scaffold_view=scaffold_view,
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


__all__ = ["ActionIntentScaffoldView", "ActionIntentScaffoldingResult"]
