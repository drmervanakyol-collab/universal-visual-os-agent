from __future__ import annotations

from universal_visual_os_agent.app.runtime_event_models import (
    RuntimeAnalysisTarget,
    RuntimeCaptureTarget,
    RuntimeDispatchMode,
    RuntimeEvent,
    RuntimeEventCoalescingMode,
    RuntimeEventDisposition,
    RuntimeEventQueueStatus,
    RuntimeEventSource,
    RuntimeEventType,
    RuntimeInvalidationScope,
    RuntimeInvalidationSignal,
)
from universal_visual_os_agent.app.runtime_events import ObserveOnlyRuntimeEventCoordinator


def test_runtime_event_coordinator_accepts_valid_event_and_builds_event_first_dispatch_plan() -> None:
    coordinator = ObserveOnlyRuntimeEventCoordinator()
    event = RuntimeEvent(
        event_type=RuntimeEventType.observation_invalidated,
        source=RuntimeEventSource.capture_runtime,
        summary="Desktop frame changed.",
        invalidation_signals=(
            RuntimeInvalidationSignal(
                scope=RuntimeInvalidationScope.frame,
                summary="Frame invalidated.",
            ),
        ),
    )

    submission_result = coordinator.submit(event)
    dispatch_result = coordinator.dispatch_next()

    assert submission_result.success is True
    assert submission_result.disposition is RuntimeEventDisposition.accepted
    assert dispatch_result.success is True
    assert dispatch_result.dispatch_plan is not None
    assert dispatch_result.dispatch_plan.dispatch_mode is RuntimeDispatchMode.event_first
    assert dispatch_result.dispatch_plan.requires_capture is True
    assert dispatch_result.dispatch_plan.requires_semantic_rebuild is True
    assert dispatch_result.dispatch_plan.capture_targets == (RuntimeCaptureTarget.full_desktop,)
    assert dispatch_result.dispatch_plan.analysis_targets == (
        RuntimeAnalysisTarget.frame_diff,
        RuntimeAnalysisTarget.semantic_state,
    )
    assert dispatch_result.dispatch_plan.observe_only is True
    assert dispatch_result.dispatch_plan.read_only is True
    assert dispatch_result.dispatch_plan.non_executing is True


def test_runtime_event_coordinator_coalesces_matching_events() -> None:
    coordinator = ObserveOnlyRuntimeEventCoordinator()
    first_event = RuntimeEvent(
        event_type=RuntimeEventType.observation_invalidated,
        source=RuntimeEventSource.test_scaffold,
        summary="Initial invalidation.",
        invalidation_signals=(
            RuntimeInvalidationSignal(
                scope=RuntimeInvalidationScope.frame,
                summary="Frame changed.",
                affected_ids=("frame-1",),
            ),
        ),
        coalescing_mode=RuntimeEventCoalescingMode.merge,
        debounce_key="desktop-frame",
        debounce_window_ms=25,
    )
    second_event = RuntimeEvent(
        event_type=RuntimeEventType.observation_invalidated,
        source=RuntimeEventSource.test_scaffold,
        summary="Follow-up invalidation.",
        invalidation_signals=(
            RuntimeInvalidationSignal(
                scope=RuntimeInvalidationScope.candidates,
                summary="Candidates changed.",
                affected_ids=("candidate-1",),
            ),
        ),
        coalescing_mode=RuntimeEventCoalescingMode.merge,
        debounce_key="desktop-frame",
        debounce_window_ms=25,
    )

    first_submission = coordinator.submit(first_event)
    second_submission = coordinator.submit(second_event)
    dispatch_result = coordinator.dispatch_next()

    assert first_submission.disposition is RuntimeEventDisposition.accepted
    assert second_submission.success is True
    assert second_submission.disposition is RuntimeEventDisposition.coalesced
    assert second_submission.queue_snapshot.queue_depth == 1
    assert dispatch_result.success is True
    assert dispatch_result.dispatch_plan is not None
    assert dispatch_result.dispatch_plan.coalesced_event_count == 2
    assert dispatch_result.dispatch_plan.source_event_ids == (
        first_event.event_id,
        second_event.event_id,
    )
    assert dispatch_result.dispatch_plan.invalidation_scopes == (
        RuntimeInvalidationScope.frame,
        RuntimeInvalidationScope.candidates,
    )
    assert dispatch_result.dispatch_plan.analysis_targets == (
        RuntimeAnalysisTarget.frame_diff,
        RuntimeAnalysisTarget.semantic_state,
        RuntimeAnalysisTarget.candidate_set,
    )


def test_runtime_event_coordinator_marks_polling_fallback_as_secondary() -> None:
    coordinator = ObserveOnlyRuntimeEventCoordinator()
    event = RuntimeEvent(
        event_type=RuntimeEventType.polling_fallback_tick,
        source=RuntimeEventSource.polling_fallback,
        summary="Compatibility polling tick.",
    )

    submission_result = coordinator.submit(event)
    dispatch_result = coordinator.dispatch_next()

    assert submission_result.success is True
    assert dispatch_result.success is True
    assert dispatch_result.dispatch_plan is not None
    assert dispatch_result.dispatch_plan.dispatch_mode is RuntimeDispatchMode.polling_fallback
    assert dispatch_result.dispatch_plan.capture_targets == (RuntimeCaptureTarget.full_desktop,)
    assert dispatch_result.dispatch_plan.metadata["polling_fallback_secondary"] is True
    assert dispatch_result.queue_snapshot.status is RuntimeEventQueueStatus.empty


def test_runtime_event_coordinator_handles_incomplete_events_safely() -> None:
    coordinator = ObserveOnlyRuntimeEventCoordinator()
    event = RuntimeEvent(
        event_type=RuntimeEventType.semantic_reanalysis_requested,
        source=RuntimeEventSource.semantic_pipeline,
        summary="Reanalysis requested without signals.",
    )

    submission_result = coordinator.submit(event)

    assert submission_result.success is False
    assert submission_result.disposition is RuntimeEventDisposition.blocked
    assert submission_result.error_code == "runtime_event_incomplete"
    assert submission_result.queue_snapshot.queue_depth == 0


def test_runtime_event_coordinator_does_not_propagate_unhandled_exceptions() -> None:
    class ExplodingCoordinator(ObserveOnlyRuntimeEventCoordinator):
        def _build_dispatch_plan(self, queued_event):  # type: ignore[override]
            del queued_event
            raise RuntimeError("boom")

    coordinator = ExplodingCoordinator()
    event = RuntimeEvent(
        event_type=RuntimeEventType.observation_invalidated,
        source=RuntimeEventSource.test_scaffold,
        summary="Exploding dispatch path.",
        invalidation_signals=(
            RuntimeInvalidationSignal(
                scope=RuntimeInvalidationScope.frame,
                summary="Frame changed.",
            ),
        ),
    )

    submission_result = coordinator.submit(event)
    dispatch_result = coordinator.dispatch_next()

    assert submission_result.success is True
    assert dispatch_result.success is False
    assert dispatch_result.error_code == "runtime_event_dispatch_failed"
    assert dispatch_result.queue_snapshot.queue_depth == 1
