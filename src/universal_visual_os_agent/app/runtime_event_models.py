"""Event-first runtime models for safe, non-executing orchestration scaffolding."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self
from uuid import uuid4


class RuntimeEventType(StrEnum):
    """Typed runtime triggers for the event-first architecture."""

    observation_invalidated = "observation_invalidated"
    semantic_reanalysis_requested = "semantic_reanalysis_requested"
    verification_requested = "verification_requested"
    scenario_requested = "scenario_requested"
    polling_fallback_tick = "polling_fallback_tick"


class RuntimeEventSource(StrEnum):
    """Stable source labels for runtime events."""

    capture_runtime = "capture_runtime"
    semantic_pipeline = "semantic_pipeline"
    verification_layer = "verification_layer"
    scenario_runtime = "scenario_runtime"
    polling_fallback = "polling_fallback"
    test_scaffold = "test_scaffold"


class RuntimeInvalidationScope(StrEnum):
    """Invalidation scopes that drive selective recapture and re-analysis."""

    frame = "frame"
    semantic_snapshot = "semantic_snapshot"
    ocr_regions = "ocr_regions"
    layout_regions = "layout_regions"
    candidates = "candidates"
    verification = "verification"
    scenario = "scenario"


class RuntimeCaptureTarget(StrEnum):
    """Modeled recapture targets for event-driven runtime handling."""

    full_desktop = "full_desktop"
    foreground_window = "foreground_window"
    affected_regions = "affected_regions"


class RuntimeAnalysisTarget(StrEnum):
    """Modeled re-analysis targets for event-driven runtime handling."""

    frame_diff = "frame_diff"
    semantic_state = "semantic_state"
    ocr = "ocr"
    layout = "layout"
    candidate_set = "candidate_set"
    verification = "verification"
    scenario_state = "scenario_state"


class RuntimeEventCoalescingMode(StrEnum):
    """Supported debounce/coalescing behaviors for queued runtime events."""

    none = "none"
    debounce_replace = "debounce_replace"
    merge = "merge"


class RuntimeDispatchMode(StrEnum):
    """Dispatch mode for runtime event handling."""

    event_first = "event_first"
    polling_fallback = "polling_fallback"


class RuntimeEventDisposition(StrEnum):
    """Stable outcomes for runtime event submission."""

    accepted = "accepted"
    coalesced = "coalesced"
    blocked = "blocked"
    unsupported = "unsupported"


class RuntimeQueueStatus(StrEnum):
    """Queue state summary for runtime event scaffolding."""

    empty = "empty"
    pending = "pending"


@dataclass(slots=True, frozen=True, kw_only=True)
class RuntimeInvalidationSignal:
    """One invalidation signal that can drive selective runtime handling."""

    scope: RuntimeInvalidationScope
    summary: str
    affected_ids: tuple[str, ...] = ()
    full_refresh_required: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if len(set(self.affected_ids)) != len(self.affected_ids):
            raise ValueError("affected_ids must not contain duplicates.")


@dataclass(slots=True, frozen=True, kw_only=True)
class RuntimeSelectiveTrigger:
    """Selective capture and analysis hints for an event-driven runtime."""

    capture_targets: tuple[RuntimeCaptureTarget, ...] = ()
    analysis_targets: tuple[RuntimeAnalysisTarget, ...] = ()
    affected_ids: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(set(self.capture_targets)) != len(self.capture_targets):
            raise ValueError("capture_targets must not contain duplicates.")
        if len(set(self.analysis_targets)) != len(self.analysis_targets):
            raise ValueError("analysis_targets must not contain duplicates.")
        if len(set(self.affected_ids)) != len(self.affected_ids):
            raise ValueError("affected_ids must not contain duplicates.")


@dataclass(slots=True, frozen=True, kw_only=True)
class RuntimeEvent:
    """Structured non-executing runtime event."""

    event_type: RuntimeEventType
    source: RuntimeEventSource
    summary: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    invalidation_signals: tuple[RuntimeInvalidationSignal, ...] = ()
    selective_trigger: RuntimeSelectiveTrigger = field(default_factory=RuntimeSelectiveTrigger)
    coalescing_mode: RuntimeEventCoalescingMode = RuntimeEventCoalescingMode.none
    debounce_key: str | None = None
    debounce_window_ms: int = 0
    polling_fallback_allowed: bool = True
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.debounce_window_ms < 0:
            raise ValueError("debounce_window_ms must not be negative.")
        if (
            self.coalescing_mode is not RuntimeEventCoalescingMode.none
            and (self.debounce_key is None or not self.debounce_key)
        ):
            raise ValueError("debounce_key is required when coalescing is enabled.")
        if (
            self.event_type is RuntimeEventType.polling_fallback_tick
            and self.source is not RuntimeEventSource.polling_fallback
        ):
            raise ValueError(
                "polling_fallback_tick events must use the polling_fallback source."
            )
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Runtime events must remain safety-first and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class RuntimeEventQueueSnapshot:
    """Deterministic snapshot of the queued runtime-event state."""

    queue_depth: int
    pending_event_ids: tuple[str, ...]
    pending_debounce_keys: tuple[str, ...] = ()
    status: RuntimeQueueStatus = RuntimeQueueStatus.empty
    event_first_enabled: bool = True
    polling_fallback_secondary: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.queue_depth < 0:
            raise ValueError("queue_depth must not be negative.")
        if self.queue_depth != len(self.pending_event_ids):
            raise ValueError("queue_depth must match len(pending_event_ids).")


@dataclass(slots=True, frozen=True, kw_only=True)
class RuntimeEventDispatchPlan:
    """Resolved runtime dispatch plan derived from one or more queued events."""

    plan_id: str = field(default_factory=lambda: str(uuid4()))
    source_event_ids: tuple[str, ...]
    dispatch_mode: RuntimeDispatchMode
    summary: str
    invalidation_scopes: tuple[RuntimeInvalidationScope, ...] = ()
    capture_targets: tuple[RuntimeCaptureTarget, ...] = ()
    analysis_targets: tuple[RuntimeAnalysisTarget, ...] = ()
    coalesced_event_count: int = 1
    requires_capture: bool = False
    requires_semantic_rebuild: bool = False
    requires_candidate_refresh: bool = False
    requires_verification_refresh: bool = False
    requires_scenario_refresh: bool = False
    polling_fallback_allowed: bool = True
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_event_ids:
            raise ValueError("source_event_ids must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.coalesced_event_count <= 0:
            raise ValueError("coalesced_event_count must be positive.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Runtime dispatch plans must remain safety-first and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class RuntimeEventSubmissionResult:
    """Failure-safe result for runtime-event submission."""

    coordinator_name: str
    success: bool
    disposition: RuntimeEventDisposition
    queue_snapshot: RuntimeEventQueueSnapshot
    event: RuntimeEvent | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.coordinator_name:
            raise ValueError("coordinator_name must not be empty.")
        if self.success and self.event is None:
            raise ValueError("Successful submission results must include event.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed submission results must include error_code.")

    @classmethod
    def ok(
        cls,
        *,
        coordinator_name: str,
        disposition: RuntimeEventDisposition,
        queue_snapshot: RuntimeEventQueueSnapshot,
        event: RuntimeEvent,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            coordinator_name=coordinator_name,
            success=True,
            disposition=disposition,
            queue_snapshot=queue_snapshot,
            event=event,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        coordinator_name: str,
        disposition: RuntimeEventDisposition,
        queue_snapshot: RuntimeEventQueueSnapshot,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            coordinator_name=coordinator_name,
            success=False,
            disposition=disposition,
            queue_snapshot=queue_snapshot,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class RuntimeEventDispatchResult:
    """Failure-safe result for runtime-event dispatch planning."""

    coordinator_name: str
    success: bool
    queue_snapshot: RuntimeEventQueueSnapshot
    dispatch_plan: RuntimeEventDispatchPlan | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.coordinator_name:
            raise ValueError("coordinator_name must not be empty.")
        if self.success and self.dispatch_plan is None:
            raise ValueError("Successful dispatch results must include dispatch_plan.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed dispatch results must include error_code.")

    @classmethod
    def ok(
        cls,
        *,
        coordinator_name: str,
        queue_snapshot: RuntimeEventQueueSnapshot,
        dispatch_plan: RuntimeEventDispatchPlan,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            coordinator_name=coordinator_name,
            success=True,
            queue_snapshot=queue_snapshot,
            dispatch_plan=dispatch_plan,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        coordinator_name: str,
        queue_snapshot: RuntimeEventQueueSnapshot,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            coordinator_name=coordinator_name,
            success=False,
            queue_snapshot=queue_snapshot,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


RuntimeEventQueueStatus = RuntimeQueueStatus


__all__ = [
    "RuntimeAnalysisTarget",
    "RuntimeCaptureTarget",
    "RuntimeDispatchMode",
    "RuntimeEvent",
    "RuntimeEventCoalescingMode",
    "RuntimeEventDispatchPlan",
    "RuntimeEventDispatchResult",
    "RuntimeEventDisposition",
    "RuntimeEventQueueSnapshot",
    "RuntimeEventQueueStatus",
    "RuntimeEventSource",
    "RuntimeEventSubmissionResult",
    "RuntimeEventType",
    "RuntimeInvalidationScope",
    "RuntimeInvalidationSignal",
    "RuntimeQueueStatus",
    "RuntimeSelectiveTrigger",
]
