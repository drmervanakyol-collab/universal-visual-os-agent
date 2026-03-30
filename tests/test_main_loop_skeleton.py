from __future__ import annotations

import asyncio

from universal_visual_os_agent.actions.models import ActionIntent
from universal_visual_os_agent.app import (
    AsyncMainLoopOrchestrator,
    FrameDiff,
    LoopPlan,
    LoopRequest,
    LoopStage,
    LoopStatus,
    RetryPolicy,
    RuntimeEvent,
    RuntimeDispatchMode,
    RuntimeEventType,
    RuntimeEventSource,
    RuntimeInvalidationSignal,
    RuntimeInvalidationScope,
)
from universal_visual_os_agent.app.interfaces import LoopActionExecutor
from universal_visual_os_agent.config import AgentMode, RunConfig
from universal_visual_os_agent.perception.models import CapturedFrame
from universal_visual_os_agent.persistence.models import CheckpointRecord, TaskRecord
from universal_visual_os_agent.planning.models import PlannerDecision
from universal_visual_os_agent.policy import (
    PolicyContextCompleteness,
    PolicyEvaluationContext,
    PolicyRule,
    PolicyRuleSet,
    ProtectedContextAssessment,
    ProtectedContextStatus,
    RuleBasedPolicyEngine,
    StaticProtectedContextDetector,
)
from universal_visual_os_agent.recovery.models import ReconciliationResult, RecoverySnapshot
from universal_visual_os_agent.semantics import SemanticStateSnapshot
from universal_visual_os_agent.verification import (
    SemanticTransitionExpectation,
    VerificationResult,
    VerificationStatus,
)


class RecordingObserver:
    def __init__(self, calls: list[str], *, delay: float = 0.0, fail_once: bool = False, always_fail: bool = False) -> None:
        self._calls = calls
        self._delay = delay
        self._fail_once = fail_once
        self._always_fail = always_fail

    async def observe(self, request: LoopRequest, *, config: RunConfig) -> CapturedFrame:
        del request, config
        self._calls.append("observe")
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._always_fail:
            raise RuntimeError("observe failed")
        if self._fail_once:
            self._fail_once = False
            raise RuntimeError("observe failed once")
        return CapturedFrame(frame_id=f"frame-{len(self._calls)}", width=100, height=100)


class RecordingDiffer:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def diff(self, previous: CapturedFrame | None, current: CapturedFrame) -> FrameDiff:
        del previous, current
        self._calls.append("diff")
        return FrameDiff(changed=True, summary="changed")


class RecordingSemanticRebuilder:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def rebuild(self, frame: CapturedFrame, diff: FrameDiff) -> SemanticStateSnapshot:
        del frame, diff
        self._calls.append("semantic_rebuild")
        return SemanticStateSnapshot()


class RecordingPlanner:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def plan(
        self,
        semantic_state: SemanticStateSnapshot,
        *,
        mode: AgentMode,
        recovery_snapshot: RecoverySnapshot | None = None,
        reconciliation_result: ReconciliationResult | None = None,
    ) -> LoopPlan:
        del semantic_state, mode, recovery_snapshot, reconciliation_result
        self._calls.append("plan")
        return LoopPlan(
            decision=PlannerDecision(goal="inspect", rationale="skeleton"),
            proposed_action=ActionIntent(action_type="click"),
            expectation=SemanticTransitionExpectation(summary="state checked"),
        )


class RecordingVerifier:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def verify(
        self,
        expectation: SemanticTransitionExpectation,
        transition,
    ) -> VerificationResult:
        del expectation, transition
        self._calls.append("verify")
        return VerificationResult(status=VerificationStatus.satisfied, summary="verified")


class RecordingRecoveryLoader:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def load_latest(self, task_id: str) -> RecoverySnapshot | None:
        self._calls.append(f"recovery_load:{task_id}")
        return RecoverySnapshot(
            task=TaskRecord(
                task_id=task_id,
                goal="recover",
            ),
            checkpoint=CheckpointRecord(
                checkpoint_id="cp-1",
                task_id=task_id,
            ),
        )


class RecordingReconciler:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def reconcile(
        self,
        snapshot: RecoverySnapshot,
        observed_state: dict[str, object] | None = None,
    ) -> ReconciliationResult:
        del snapshot, observed_state
        self._calls.append("recovery_reconcile")
        return ReconciliationResult(safe_to_resume=True, summary="reconciled")


class CountingExecutor(LoopActionExecutor):
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, action: ActionIntent):
        del action
        self.calls += 1
        raise AssertionError("executor should not be called in safe defaults")


def _policy_engine() -> RuleBasedPolicyEngine:
    return RuleBasedPolicyEngine(
        ruleset=PolicyRuleSet(
            allowlist=(
                PolicyRule(rule_id="allow-loop", description="Allow loop", action_types=("orchestration_step",)),
            ),
        ),
        protected_context_detector=StaticProtectedContextDetector(
            assessment=ProtectedContextAssessment(status=ProtectedContextStatus.clear, reason="clear")
        ),
    )


def _build_orchestrator(
    *,
    config: RunConfig,
    calls: list[str],
    observer: RecordingObserver | None = None,
    recovery_loader: RecordingRecoveryLoader | None = None,
    recovery_reconciler: RecordingReconciler | None = None,
    action_executor: LoopActionExecutor | None = None,
) -> AsyncMainLoopOrchestrator:
    return AsyncMainLoopOrchestrator(
        config=config,
        observation_provider=observer or RecordingObserver(calls),
        frame_differ=RecordingDiffer(calls),
        semantic_rebuilder=RecordingSemanticRebuilder(calls),
        policy_engine=_policy_engine(),
        planner=RecordingPlanner(calls),
        verifier=RecordingVerifier(calls),
        recovery_loader=recovery_loader,
        recovery_reconciler=recovery_reconciler,
        action_executor=action_executor,
    )


def test_loop_step_ordering() -> None:
    calls: list[str] = []
    orchestrator = _build_orchestrator(config=RunConfig(mode=AgentMode.dry_run), calls=calls)

    result = asyncio.run(orchestrator.run_once())

    assert result.status is LoopStatus.completed
    assert result.executed_stages == (
        LoopStage.observe,
        LoopStage.diff,
        LoopStage.semantic_rebuild,
        LoopStage.policy_check,
        LoopStage.plan,
        LoopStage.verify,
    )
    assert calls == ["observe", "diff", "semantic_rebuild", "plan", "verify"]


def test_mode_specific_gating_behavior_for_recovery_mode() -> None:
    calls: list[str] = []
    loader = RecordingRecoveryLoader(calls)
    reconciler = RecordingReconciler(calls)
    orchestrator = _build_orchestrator(
        config=RunConfig(mode=AgentMode.recovery_mode),
        calls=calls,
        recovery_loader=loader,
        recovery_reconciler=reconciler,
    )

    result = asyncio.run(orchestrator.run_once(LoopRequest(task_id="task-1")))

    assert result.status is LoopStatus.completed
    assert LoopStage.recovery_load in result.executed_stages
    assert LoopStage.recovery_reconcile in result.executed_stages
    assert "recovery_load:task-1" in calls
    assert "recovery_reconcile" in calls


def test_cancellation_handling_returns_cancelled_result() -> None:
    calls: list[str] = []
    orchestrator = _build_orchestrator(
        config=RunConfig(mode=AgentMode.dry_run),
        calls=calls,
        observer=RecordingObserver(calls, delay=0.2),
    )

    async def scenario() -> LoopStatus:
        await orchestrator.enqueue()
        task = asyncio.create_task(orchestrator.run_next())
        await asyncio.sleep(0.01)
        orchestrator.cancel_current()
        result = await task
        return result.status

    status = asyncio.run(scenario())

    assert status is LoopStatus.cancelled


def test_timeout_behavior_returns_timed_out_result() -> None:
    calls: list[str] = []
    orchestrator = _build_orchestrator(
        config=RunConfig(mode=AgentMode.dry_run),
        calls=calls,
        observer=RecordingObserver(calls, delay=0.05),
    )
    orchestrator.timeout_seconds = 0.01

    result = asyncio.run(orchestrator.run_once())

    assert result.status is LoopStatus.timed_out
    assert result.error_type == "TimeoutError"


def test_retry_and_safe_abort_behavior() -> None:
    retry_calls: list[str] = []
    retrying_orchestrator = _build_orchestrator(
        config=RunConfig(mode=AgentMode.dry_run),
        calls=retry_calls,
        observer=RecordingObserver(retry_calls, fail_once=True),
    )
    retrying_orchestrator.retry_policy = RetryPolicy(max_attempts=2)

    retry_result = asyncio.run(retrying_orchestrator.run_once())

    assert retry_result.status is LoopStatus.completed
    assert retry_result.attempt_count == 2

    abort_calls: list[str] = []
    aborting_orchestrator = _build_orchestrator(
        config=RunConfig(mode=AgentMode.dry_run),
        calls=abort_calls,
        observer=RecordingObserver(abort_calls, always_fail=True),
    )
    aborting_orchestrator.retry_policy = RetryPolicy(max_attempts=2)

    abort_result = asyncio.run(aborting_orchestrator.run_once())

    assert abort_result.status is LoopStatus.aborted
    assert abort_result.attempt_count == 2
    assert abort_result.safe_abort_reason == "Loop aborted after retry exhaustion."


def test_no_live_execution_in_observe_only_and_dry_run_defaults() -> None:
    for mode in (AgentMode.observe_only, AgentMode.dry_run):
        calls: list[str] = []
        executor = CountingExecutor()
        orchestrator = _build_orchestrator(
            config=RunConfig(mode=mode),
            calls=calls,
            action_executor=executor,
        )

        result = asyncio.run(orchestrator.run_once())

        assert result.status is LoopStatus.completed
        assert result.live_execution_attempted is False
        assert executor.calls == 0


def test_safe_handling_of_partial_policy_context() -> None:
    calls: list[str] = []
    orchestrator = _build_orchestrator(config=RunConfig(mode=AgentMode.dry_run), calls=calls)

    result = asyncio.run(
        orchestrator.run_once(
            LoopRequest(
                policy_context=PolicyEvaluationContext(
                    completeness=PolicyContextCompleteness.partial,
                )
            )
        )
    )

    assert result.status is LoopStatus.aborted
    assert result.safe_abort_reason == "Policy context is incomplete."


def test_orchestrator_can_run_next_runtime_event_without_live_execution() -> None:
    calls: list[str] = []
    orchestrator = _build_orchestrator(config=RunConfig(mode=AgentMode.dry_run), calls=calls)

    event = RuntimeEvent(
        event_type=RuntimeEventType.observation_invalidated,
        source=RuntimeEventSource.test_scaffold,
        summary="Observed frame invalidation.",
        invalidation_signals=(
            RuntimeInvalidationSignal(
                scope=RuntimeInvalidationScope.frame,
                summary="Frame changed.",
            ),
        ),
    )

    submission_result = asyncio.run(orchestrator.enqueue_runtime_event(event))
    result = asyncio.run(orchestrator.run_next_runtime_event())

    assert submission_result.success is True
    assert result.status is LoopStatus.completed
    assert result.executed_stages[0] is LoopStage.runtime_dispatch
    assert result.runtime_event_dispatch is not None
    assert result.runtime_event_dispatch.dispatch_mode is RuntimeDispatchMode.event_first
    assert result.live_execution_attempted is False
