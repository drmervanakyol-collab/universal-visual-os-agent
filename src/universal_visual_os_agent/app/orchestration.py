"""Async event-driven main loop skeleton."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any

from universal_visual_os_agent.app.interfaces import (
    FrameDiffer,
    LoopActionExecutor,
    LoopPlanner,
    ObservationProvider,
    RecoveryLoader,
    RecoveryReconciler,
    SemanticRebuilder,
    TransitionVerifier,
)
from universal_visual_os_agent.app.models import (
    FrameDiff,
    LoopPlan,
    LoopRequest,
    LoopResult,
    LoopStage,
    LoopStatus,
    RetryPolicy,
)
from universal_visual_os_agent.config.modes import AgentMode
from universal_visual_os_agent.config.models import RunConfig
from universal_visual_os_agent.perception.models import CapturedFrame
from universal_visual_os_agent.policy.interfaces import PolicyEngine
from universal_visual_os_agent.policy.models import (
    PolicyContextCompleteness,
    PolicyEvaluationContext,
    PolicyVerdict,
)
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot
from universal_visual_os_agent.verification.models import (
    SemanticStateTransition,
    SemanticTransitionExpectation,
)


@dataclass(slots=True)
class AsyncMainLoopOrchestrator:
    """Queue-backed asyncio orchestration skeleton for safe modes only."""

    config: RunConfig
    observation_provider: ObservationProvider
    frame_differ: FrameDiffer
    semantic_rebuilder: SemanticRebuilder
    policy_engine: PolicyEngine
    planner: LoopPlanner
    verifier: TransitionVerifier
    recovery_loader: RecoveryLoader | None = None
    recovery_reconciler: RecoveryReconciler | None = None
    action_executor: LoopActionExecutor | None = None
    queue_maxsize: int = 16
    timeout_seconds: float = 1.0
    retry_policy: RetryPolicy = RetryPolicy()
    _queue: asyncio.Queue[LoopRequest] = field(init=False, repr=False)
    _previous_frame: CapturedFrame | None = field(init=False, default=None, repr=False)
    _previous_snapshot: SemanticStateSnapshot | None = field(init=False, default=None, repr=False)
    _current_task: asyncio.Task[LoopResult] | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        if self.queue_maxsize <= 0:
            raise ValueError("queue_maxsize must be positive.")
        if self.timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive.")
        self._queue = asyncio.Queue(maxsize=self.queue_maxsize)

    @property
    def pending_count(self) -> int:
        """Return the number of queued orchestration requests."""

        return self._queue.qsize()

    async def enqueue(self, request: LoopRequest | None = None) -> LoopRequest:
        """Queue an orchestration request."""

        queued_request = request or LoopRequest()
        await self._queue.put(queued_request)
        return queued_request

    async def run_once(self, request: LoopRequest | None = None) -> LoopResult:
        """Convenience wrapper that enqueues and executes one request."""

        await self.enqueue(request)
        return await self.run_next()

    async def run_next(self) -> LoopResult:
        """Execute the next queued request."""

        request = await self._queue.get()
        try:
            return await self._run_request(request)
        finally:
            self._queue.task_done()

    async def run_until_empty(self) -> tuple[LoopResult, ...]:
        """Drain the queue and return all results."""

        results: list[LoopResult] = []
        while not self._queue.empty():
            results.append(await self.run_next())
        return tuple(results)

    def cancel_current(self) -> None:
        """Cancel the currently running orchestration task, if any."""

        if self._current_task is not None and not self._current_task.done():
            self._current_task.cancel()

    async def _run_request(self, request: LoopRequest) -> LoopResult:
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            self._current_task = asyncio.current_task()
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    return await self._execute_attempt(request, attempt)
            except asyncio.CancelledError:
                return LoopResult(
                    status=LoopStatus.cancelled,
                    attempt_count=attempt,
                    request=request,
                    safe_abort_reason="Loop cancelled.",
                    error_type="CancelledError",
                )
            except TimeoutError:
                if attempt < self.retry_policy.max_attempts and self.retry_policy.retry_on_timeout:
                    continue
                return LoopResult(
                    status=LoopStatus.timed_out,
                    attempt_count=attempt,
                    request=request,
                    safe_abort_reason="Loop timed out.",
                    error_type="TimeoutError",
                )
            except Exception as exc:  # noqa: BLE001 - Phase 6 safe-abort scaffold
                if attempt < self.retry_policy.max_attempts and self.retry_policy.retry_on_exception:
                    continue
                return LoopResult(
                    status=LoopStatus.aborted,
                    attempt_count=attempt,
                    request=request,
                    safe_abort_reason="Loop aborted after retry exhaustion.",
                    error_type=type(exc).__name__,
                )
            finally:
                self._current_task = None

        return LoopResult(
            status=LoopStatus.aborted,
            attempt_count=self.retry_policy.max_attempts,
            request=request,
            safe_abort_reason="Loop aborted without a result.",
        )

    async def _execute_attempt(self, request: LoopRequest, attempt: int) -> LoopResult:
        executed_stages: list[LoopStage] = []

        executed_stages.append(LoopStage.observe)
        frame = await _resolve(self.observation_provider.observe(request, config=self.config))

        executed_stages.append(LoopStage.diff)
        diff = await _resolve(self.frame_differ.diff(self._previous_frame, frame))

        executed_stages.append(LoopStage.semantic_rebuild)
        semantic_snapshot = await _resolve(self.semantic_rebuilder.rebuild(frame, diff))

        recovery_snapshot = None
        reconciliation_result = None
        if self.config.mode is AgentMode.recovery_mode and request.task_id and self.recovery_loader is not None:
            executed_stages.append(LoopStage.recovery_load)
            recovery_snapshot = await _resolve(self.recovery_loader.load_latest(request.task_id))
            if recovery_snapshot is not None and self.recovery_reconciler is not None:
                executed_stages.append(LoopStage.recovery_reconcile)
                reconciliation_result = await _resolve(
                    self.recovery_reconciler.reconcile(
                        recovery_snapshot,
                        observed_state=_observed_state_payload(semantic_snapshot),
                    )
                )

        executed_stages.append(LoopStage.policy_check)
        policy_decision = self.policy_engine.evaluate(
            _policy_check_action(self.config.mode),
            context=request.policy_context or _default_policy_context(self.config),
        )
        if policy_decision.verdict is not PolicyVerdict.allow:
            return LoopResult(
                status=LoopStatus.aborted,
                executed_stages=tuple(executed_stages),
                attempt_count=attempt,
                request=request,
                frame=frame,
                diff=diff,
                semantic_snapshot=semantic_snapshot,
                recovery_snapshot=recovery_snapshot,
                reconciliation_result=reconciliation_result,
                policy_decision=policy_decision,
                safe_abort_reason=policy_decision.reason,
            )

        executed_stages.append(LoopStage.plan)
        plan = await _resolve(
            self.planner.plan(
                semantic_snapshot,
                mode=self.config.mode,
                recovery_snapshot=recovery_snapshot,
                reconciliation_result=reconciliation_result,
            )
        )

        executed_stages.append(LoopStage.verify)
        verification_result = await _resolve(
            self.verifier.verify(
                plan.expectation or SemanticTransitionExpectation(summary="Skeleton verification."),
                SemanticStateTransition(before=self._previous_snapshot, after=semantic_snapshot),
            )
        )

        self._previous_frame = frame
        self._previous_snapshot = semantic_snapshot

        return LoopResult(
            status=LoopStatus.completed,
            executed_stages=tuple(executed_stages),
            attempt_count=attempt,
            request=request,
            frame=frame,
            diff=diff,
            semantic_snapshot=semantic_snapshot,
            recovery_snapshot=recovery_snapshot,
            reconciliation_result=reconciliation_result,
            policy_decision=policy_decision,
            plan=plan,
            verification_result=verification_result,
            live_execution_attempted=False,
        )


async def _resolve(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _default_policy_context(config: RunConfig) -> PolicyEvaluationContext:
    return PolicyEvaluationContext(
        completeness=PolicyContextCompleteness.complete,
        live_execution_requested=False,
        live_execution_enabled=config.allow_live_input,
        metadata={"mode": config.mode},
    )


def _policy_check_action(mode: AgentMode) -> Any:
    from universal_visual_os_agent.actions.models import ActionIntent

    return ActionIntent(action_type="orchestration_step", metadata={"mode": mode})


def _observed_state_payload(snapshot: SemanticStateSnapshot) -> dict[str, object]:
    return {
        "snapshot_id": snapshot.snapshot_id,
        "candidate_ids": tuple(candidate.candidate_id for candidate in snapshot.candidates),
        "visible_candidate_ids": tuple(candidate.candidate_id for candidate in snapshot.visible_candidates),
    }
