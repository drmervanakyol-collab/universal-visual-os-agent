"""Observe-only runtime event coordination for event-first orchestration scaffolding."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from universal_visual_os_agent.app.runtime_event_models import (
    RuntimeAnalysisTarget,
    RuntimeCaptureTarget,
    RuntimeDispatchMode,
    RuntimeEvent,
    RuntimeEventCoalescingMode,
    RuntimeEventDispatchPlan,
    RuntimeEventDispatchResult,
    RuntimeEventDisposition,
    RuntimeEventQueueSnapshot,
    RuntimeEventQueueStatus,
    RuntimeEventSource,
    RuntimeEventSubmissionResult,
    RuntimeEventType,
    RuntimeInvalidationScope,
    RuntimeInvalidationSignal,
    RuntimeSelectiveTrigger,
)


@dataclass(slots=True)
class _QueuedRuntimeEvent:
    """Internal queued runtime event entry."""

    event: RuntimeEvent
    source_event_ids: tuple[str, ...]
    coalesced_event_count: int = 1


@dataclass(slots=True)
class ObserveOnlyRuntimeEventCoordinator:
    """In-memory event-first coordinator that remains observe-only and non-executing."""

    coordinator_name: str = "observe_only_runtime_event_coordinator"
    _queue: list[_QueuedRuntimeEvent] = field(default_factory=list, init=False, repr=False)

    @property
    def pending_count(self) -> int:
        """Return the number of queued runtime events."""

        return len(self._queue)

    def submit(self, event: RuntimeEvent) -> RuntimeEventSubmissionResult:
        """Submit one runtime event for later dispatch planning."""

        try:
            completeness_error = self._validate_event_completeness(event)
            if completeness_error is not None:
                return RuntimeEventSubmissionResult.failure(
                    coordinator_name=self.coordinator_name,
                    disposition=RuntimeEventDisposition.blocked,
                    queue_snapshot=self._queue_snapshot(),
                    error_code="runtime_event_incomplete",
                    error_message=completeness_error,
                    details={"event_id": event.event_id},
                )

            queued_event = _QueuedRuntimeEvent(event=event, source_event_ids=(event.event_id,))
            index = self._find_coalescible_index(event)
            if index is None:
                self._queue.append(queued_event)
                return RuntimeEventSubmissionResult.ok(
                    coordinator_name=self.coordinator_name,
                    disposition=RuntimeEventDisposition.accepted,
                    queue_snapshot=self._queue_snapshot(),
                    event=event,
                )

            coalesced_event = self._coalesce_events(self._queue[index], queued_event)
            self._queue[index] = coalesced_event
            return RuntimeEventSubmissionResult.ok(
                coordinator_name=self.coordinator_name,
                disposition=RuntimeEventDisposition.coalesced,
                queue_snapshot=self._queue_snapshot(),
                event=coalesced_event.event,
                details={
                    "source_event_ids": coalesced_event.source_event_ids,
                    "coalesced_event_count": coalesced_event.coalesced_event_count,
                },
            )
        except Exception as exc:  # noqa: BLE001 - safe failure wrapper
            return RuntimeEventSubmissionResult.failure(
                coordinator_name=self.coordinator_name,
                disposition=RuntimeEventDisposition.blocked,
                queue_snapshot=self._queue_snapshot(),
                error_code="runtime_event_submission_failed",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

    def dispatch_next(self) -> RuntimeEventDispatchResult:
        """Build a dispatch plan for the next queued runtime event."""

        if not self._queue:
            return RuntimeEventDispatchResult.failure(
                coordinator_name=self.coordinator_name,
                queue_snapshot=self._queue_snapshot(),
                error_code="runtime_event_queue_empty",
                error_message="No runtime events are pending.",
            )

        queued_event = self._queue[0]
        try:
            dispatch_plan = self._build_dispatch_plan(queued_event)
        except Exception as exc:  # noqa: BLE001 - safe failure wrapper
            return RuntimeEventDispatchResult.failure(
                coordinator_name=self.coordinator_name,
                queue_snapshot=self._queue_snapshot(),
                error_code="runtime_event_dispatch_failed",
                error_message=str(exc),
                details={
                    "event_id": queued_event.event.event_id,
                    "exception_type": type(exc).__name__,
                },
            )

        self._queue.pop(0)
        return RuntimeEventDispatchResult.ok(
            coordinator_name=self.coordinator_name,
            queue_snapshot=self._queue_snapshot(),
            dispatch_plan=dispatch_plan,
            details={
                "source_event_ids": dispatch_plan.source_event_ids,
                "coalesced_event_count": dispatch_plan.coalesced_event_count,
            },
        )

    def _validate_event_completeness(self, event: RuntimeEvent) -> str | None:
        if (
            event.event_type is RuntimeEventType.polling_fallback_tick
            and event.source is not RuntimeEventSource.polling_fallback
        ):
            return "Polling fallback events must originate from the polling_fallback source."
        if event.event_type is RuntimeEventType.polling_fallback_tick:
            return None
        if event.invalidation_signals:
            return None
        if event.selective_trigger.capture_targets or event.selective_trigger.analysis_targets:
            return None
        return "Runtime events must include invalidation signals or selective trigger targets."

    def _find_coalescible_index(self, event: RuntimeEvent) -> int | None:
        if event.coalescing_mode is RuntimeEventCoalescingMode.none or event.debounce_key is None:
            return None
        for index, queued_event in enumerate(self._queue):
            if (
                queued_event.event.debounce_key == event.debounce_key
                and queued_event.event.coalescing_mode is event.coalescing_mode
                and queued_event.event.event_type is event.event_type
            ):
                return index
        return None

    def _coalesce_events(
        self,
        existing: _QueuedRuntimeEvent,
        incoming: _QueuedRuntimeEvent,
    ) -> _QueuedRuntimeEvent:
        if incoming.event.coalescing_mode is RuntimeEventCoalescingMode.debounce_replace:
            event = RuntimeEvent(
                event_type=incoming.event.event_type,
                source=incoming.event.source,
                summary=incoming.event.summary,
                event_id=incoming.event.event_id,
                invalidation_signals=incoming.event.invalidation_signals,
                selective_trigger=incoming.event.selective_trigger,
                coalescing_mode=incoming.event.coalescing_mode,
                debounce_key=incoming.event.debounce_key,
                debounce_window_ms=max(
                    existing.event.debounce_window_ms,
                    incoming.event.debounce_window_ms,
                ),
                polling_fallback_allowed=(
                    existing.event.polling_fallback_allowed and incoming.event.polling_fallback_allowed
                ),
                metadata=self._merge_metadata(existing.event.metadata, incoming.event.metadata),
            )
            return _QueuedRuntimeEvent(
                event=event,
                source_event_ids=existing.source_event_ids + incoming.source_event_ids,
                coalesced_event_count=existing.coalesced_event_count + incoming.coalesced_event_count,
            )

        merged_signals = self._merge_invalidation_signals(
            existing.event.invalidation_signals,
            incoming.event.invalidation_signals,
        )
        merged_trigger = self._merge_selective_trigger(
            existing.event.selective_trigger,
            incoming.event.selective_trigger,
        )
        event = RuntimeEvent(
            event_type=existing.event.event_type,
            source=existing.event.source,
            summary=existing.event.summary,
            event_id=existing.event.event_id,
            invalidation_signals=merged_signals,
            selective_trigger=merged_trigger,
            coalescing_mode=existing.event.coalescing_mode,
            debounce_key=existing.event.debounce_key,
            debounce_window_ms=max(
                existing.event.debounce_window_ms,
                incoming.event.debounce_window_ms,
            ),
            polling_fallback_allowed=(
                existing.event.polling_fallback_allowed and incoming.event.polling_fallback_allowed
            ),
            metadata=self._merge_metadata(existing.event.metadata, incoming.event.metadata),
        )
        return _QueuedRuntimeEvent(
            event=event,
            source_event_ids=existing.source_event_ids + incoming.source_event_ids,
            coalesced_event_count=existing.coalesced_event_count + incoming.coalesced_event_count,
        )

    def _build_dispatch_plan(self, queued_event: _QueuedRuntimeEvent) -> RuntimeEventDispatchPlan:
        event = queued_event.event
        invalidation_scopes = self._ordered_invalidation_scopes(event.invalidation_signals)
        capture_targets = self._derive_capture_targets(event, invalidation_scopes)
        analysis_targets = self._derive_analysis_targets(event, invalidation_scopes)

        return RuntimeEventDispatchPlan(
            source_event_ids=queued_event.source_event_ids,
            dispatch_mode=(
                RuntimeDispatchMode.polling_fallback
                if event.event_type is RuntimeEventType.polling_fallback_tick
                else RuntimeDispatchMode.event_first
            ),
            summary=event.summary,
            invalidation_scopes=invalidation_scopes,
            capture_targets=capture_targets,
            analysis_targets=analysis_targets,
            coalesced_event_count=queued_event.coalesced_event_count,
            requires_capture=bool(capture_targets),
            requires_semantic_rebuild=RuntimeAnalysisTarget.semantic_state in analysis_targets,
            requires_candidate_refresh=RuntimeAnalysisTarget.candidate_set in analysis_targets,
            requires_verification_refresh=RuntimeAnalysisTarget.verification in analysis_targets,
            requires_scenario_refresh=RuntimeAnalysisTarget.scenario_state in analysis_targets,
            polling_fallback_allowed=event.polling_fallback_allowed,
            metadata={
                "event_first_enabled": True,
                "polling_fallback_secondary": True,
                "event_type": event.event_type,
                "event_source": event.source,
                "coalescing_mode": event.coalescing_mode,
            },
        )

    def _derive_capture_targets(
        self,
        event: RuntimeEvent,
        invalidation_scopes: tuple[RuntimeInvalidationScope, ...],
    ) -> tuple[RuntimeCaptureTarget, ...]:
        targets = list(event.selective_trigger.capture_targets)
        if not targets and (
            RuntimeInvalidationScope.frame in invalidation_scopes
            or event.event_type is RuntimeEventType.polling_fallback_tick
        ):
            targets.append(RuntimeCaptureTarget.full_desktop)
        return self._dedupe_in_enum_order(RuntimeCaptureTarget, targets)

    def _derive_analysis_targets(
        self,
        event: RuntimeEvent,
        invalidation_scopes: tuple[RuntimeInvalidationScope, ...],
    ) -> tuple[RuntimeAnalysisTarget, ...]:
        targets = list(event.selective_trigger.analysis_targets)
        scope_mapping = {
            RuntimeInvalidationScope.frame: (
                RuntimeAnalysisTarget.frame_diff,
                RuntimeAnalysisTarget.semantic_state,
            ),
            RuntimeInvalidationScope.semantic_snapshot: (RuntimeAnalysisTarget.semantic_state,),
            RuntimeInvalidationScope.ocr_regions: (
                RuntimeAnalysisTarget.ocr,
                RuntimeAnalysisTarget.semantic_state,
            ),
            RuntimeInvalidationScope.layout_regions: (
                RuntimeAnalysisTarget.layout,
                RuntimeAnalysisTarget.semantic_state,
            ),
            RuntimeInvalidationScope.candidates: (RuntimeAnalysisTarget.candidate_set,),
            RuntimeInvalidationScope.verification: (RuntimeAnalysisTarget.verification,),
            RuntimeInvalidationScope.scenario: (RuntimeAnalysisTarget.scenario_state,),
        }
        for scope in invalidation_scopes:
            targets.extend(scope_mapping.get(scope, ()))
        if event.event_type is RuntimeEventType.polling_fallback_tick:
            targets.extend(
                (
                    RuntimeAnalysisTarget.frame_diff,
                    RuntimeAnalysisTarget.semantic_state,
                )
            )
        return self._dedupe_in_enum_order(RuntimeAnalysisTarget, targets)

    def _ordered_invalidation_scopes(
        self,
        signals: tuple[RuntimeInvalidationSignal, ...],
    ) -> tuple[RuntimeInvalidationScope, ...]:
        present = {signal.scope for signal in signals}
        return tuple(scope for scope in RuntimeInvalidationScope if scope in present)

    def _merge_invalidation_signals(
        self,
        first: tuple[RuntimeInvalidationSignal, ...],
        second: tuple[RuntimeInvalidationSignal, ...],
    ) -> tuple[RuntimeInvalidationSignal, ...]:
        merged: dict[RuntimeInvalidationScope, RuntimeInvalidationSignal] = {
            signal.scope: signal for signal in first
        }
        for signal in second:
            existing = merged.get(signal.scope)
            if existing is None:
                merged[signal.scope] = signal
                continue
            merged[signal.scope] = RuntimeInvalidationSignal(
                scope=signal.scope,
                summary=existing.summary,
                affected_ids=tuple(dict.fromkeys(existing.affected_ids + signal.affected_ids)),
                full_refresh_required=existing.full_refresh_required or signal.full_refresh_required,
                metadata=self._merge_metadata(existing.metadata, signal.metadata),
            )
        return tuple(
            merged[scope]
            for scope in RuntimeInvalidationScope
            if scope in merged
        )

    def _merge_selective_trigger(
        self,
        first: RuntimeSelectiveTrigger,
        second: RuntimeSelectiveTrigger,
    ) -> RuntimeSelectiveTrigger:
        return RuntimeSelectiveTrigger(
            capture_targets=self._dedupe_in_enum_order(
                RuntimeCaptureTarget,
                first.capture_targets + second.capture_targets,
            ),
            analysis_targets=self._dedupe_in_enum_order(
                RuntimeAnalysisTarget,
                first.analysis_targets + second.analysis_targets,
            ),
            affected_ids=tuple(dict.fromkeys(first.affected_ids + second.affected_ids)),
            metadata=self._merge_metadata(first.metadata, second.metadata),
        )

    def _queue_snapshot(self) -> RuntimeEventQueueSnapshot:
        pending_event_ids = tuple(queued_event.event.event_id for queued_event in self._queue)
        pending_debounce_keys = tuple(
            queued_event.event.debounce_key
            for queued_event in self._queue
            if queued_event.event.debounce_key is not None
        )
        return RuntimeEventQueueSnapshot(
            queue_depth=len(self._queue),
            pending_event_ids=pending_event_ids,
            pending_debounce_keys=pending_debounce_keys,
            status=(
                RuntimeEventQueueStatus.pending
                if self._queue
                else RuntimeEventQueueStatus.empty
            ),
            metadata={
                "event_first_enabled": True,
                "polling_fallback_secondary": True,
            },
        )

    @staticmethod
    def _dedupe_in_enum_order[T: object](enum_type: type[T], values: tuple[T, ...] | list[T]) -> tuple[T, ...]:
        present = set(values)
        return tuple(value for value in enum_type if value in present)

    @staticmethod
    def _merge_metadata(
        first: Mapping[str, object] | object,
        second: Mapping[str, object] | object,
    ) -> dict[str, object]:
        merged: dict[str, object] = {}
        if isinstance(first, Mapping):
            merged.update(first)
        if isinstance(second, Mapping):
            merged.update(second)
        return merged


__all__ = ["ObserveOnlyRuntimeEventCoordinator"]
