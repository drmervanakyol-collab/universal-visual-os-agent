from __future__ import annotations

import asyncio
import threading

from universal_visual_os_agent.actions.models import ActionIntent
from universal_visual_os_agent.app import (
    AsyncMainLoopOrchestrator,
    FrameDiff,
    LoopPlan,
    LoopRequest,
    LoopStatus,
    ObserveOnlyRuntimeIoBoundary,
    RetryPolicy,
    RuntimeIoExecutionClass,
    RuntimeIoOperationKind,
)
from universal_visual_os_agent.config import AgentMode, RunConfig
from universal_visual_os_agent.perception.models import CapturedFrame
from universal_visual_os_agent.persistence import (
    CheckpointPersistenceService,
    CheckpointRecord,
    SqliteCheckpointRepository,
    SqliteTaskRepository,
    TaskRecord,
    connect_sqlite,
)
from universal_visual_os_agent.planning.models import PlannerDecision
from universal_visual_os_agent.policy import (
    PolicyRule,
    PolicyRuleSet,
    ProtectedContextAssessment,
    ProtectedContextStatus,
    RuleBasedPolicyEngine,
    StaticProtectedContextDetector,
)
from universal_visual_os_agent.recovery import (
    ReconciliationResult,
    RecoverySnapshot,
    RepositoryBackedRecoverySnapshotLoader,
)
from universal_visual_os_agent.semantics import SemanticStateSnapshot
from universal_visual_os_agent.verification import (
    SemanticTransitionExpectation,
    VerificationResult,
    VerificationStatus,
)


class _Observer:
    async def observe(self, request: LoopRequest, *, config: RunConfig) -> CapturedFrame:
        del request, config
        return CapturedFrame(frame_id="frame-1", width=100, height=100)


class _Differ:
    def diff(self, previous: CapturedFrame | None, current: CapturedFrame) -> FrameDiff:
        del previous, current
        return FrameDiff(changed=True, summary="changed")


class _SemanticRebuilder:
    def rebuild(self, frame: CapturedFrame, diff: FrameDiff) -> SemanticStateSnapshot:
        del frame, diff
        return SemanticStateSnapshot()


class _Planner:
    def plan(
        self,
        semantic_state: SemanticStateSnapshot,
        *,
        mode: AgentMode,
        recovery_snapshot: RecoverySnapshot | None = None,
        reconciliation_result: ReconciliationResult | None = None,
    ) -> LoopPlan:
        del semantic_state, mode, recovery_snapshot, reconciliation_result
        return LoopPlan(
            decision=PlannerDecision(goal="inspect", rationale="runtime io"),
            proposed_action=ActionIntent(action_type="click"),
            expectation=SemanticTransitionExpectation(summary="verify state"),
        )


class _Verifier:
    def verify(
        self,
        expectation: SemanticTransitionExpectation,
        transition,
    ) -> VerificationResult:
        del expectation, transition
        return VerificationResult(status=VerificationStatus.satisfied, summary="verified")


def _policy_engine() -> RuleBasedPolicyEngine:
    return RuleBasedPolicyEngine(
        ruleset=PolicyRuleSet(
            allowlist=(
                PolicyRule(
                    rule_id="allow-orchestration",
                    description="Allow orchestration steps.",
                    action_types=("orchestration_step",),
                ),
            ),
        ),
        protected_context_detector=StaticProtectedContextDetector(
            assessment=ProtectedContextAssessment(
                status=ProtectedContextStatus.clear,
                reason="clear",
            )
        ),
    )


def _orchestrator(
    *,
    config: RunConfig,
    recovery_loader=None,
    recovery_reconciler=None,
) -> AsyncMainLoopOrchestrator:
    return AsyncMainLoopOrchestrator(
        config=config,
        observation_provider=_Observer(),
        frame_differ=_Differ(),
        semantic_rebuilder=_SemanticRebuilder(),
        policy_engine=_policy_engine(),
        planner=_Planner(),
        verifier=_Verifier(),
        recovery_loader=recovery_loader,
        recovery_reconciler=recovery_reconciler,
    )


class _ThreadOffloadSafeRecoveryLoader:
    runtime_io_thread_offload_safe = True

    def __init__(self) -> None:
        self.thread_id: int | None = None

    def load_latest(self, task_id: str) -> RecoverySnapshot:
        self.thread_id = threading.get_ident()
        return RecoverySnapshot(
            task=TaskRecord(task_id=task_id, goal="recover"),
            checkpoint=CheckpointRecord(checkpoint_id="cp-offload", task_id=task_id),
        )


class _ThreadOffloadSafeReconciler:
    runtime_io_thread_offload_safe = True

    def __init__(self) -> None:
        self.thread_id: int | None = None

    def reconcile(
        self,
        snapshot: RecoverySnapshot,
        observed_state: dict[str, object] | None = None,
    ) -> ReconciliationResult:
        del snapshot, observed_state
        self.thread_id = threading.get_ident()
        return ReconciliationResult(safe_to_resume=True, summary="reconciled")


class _ExplodingThreadOffloadSafeRecoveryLoader:
    runtime_io_thread_offload_safe = True

    def load_latest(self, task_id: str) -> RecoverySnapshot:
        del task_id
        raise RuntimeError("recovery load exploded")


def test_runtime_io_boundary_treats_async_callable_as_event_loop_safe() -> None:
    boundary = ObserveOnlyRuntimeIoBoundary()

    async def load_async() -> str:
        return "ok"

    result = asyncio.run(
        boundary.call(
            operation_kind=RuntimeIoOperationKind.recovery_load,
            summary="Load asynchronously.",
            func=load_async,
        )
    )

    assert result.success is True
    assert result.value == "ok"
    assert result.trace_entry.execution_class is RuntimeIoExecutionClass.event_loop_safe
    assert result.trace_entry.thread_offloaded is False


def test_orchestrator_marks_repository_backed_recovery_load_as_sync_fallback_only(
    workspace_tmp_path,
) -> None:
    connection = connect_sqlite(workspace_tmp_path / "agent.sqlite3")
    task_repository = SqliteTaskRepository(connection)
    checkpoint_repository = SqliteCheckpointRepository(connection)
    service = CheckpointPersistenceService(
        task_repository=task_repository,
        checkpoint_repository=checkpoint_repository,
    )
    loader = RepositoryBackedRecoverySnapshotLoader(
        task_repository=task_repository,
        checkpoint_repository=checkpoint_repository,
    )
    task_repository.save(TaskRecord(task_id="task-io-1", goal="Recover safely"))
    service.write_checkpoint(
        CheckpointRecord(checkpoint_id="cp-io-1", task_id="task-io-1"),
    )
    orchestrator = _orchestrator(
        config=RunConfig(mode=AgentMode.recovery_mode),
        recovery_loader=loader,
    )

    result = asyncio.run(orchestrator.run_once(LoopRequest(task_id="task-io-1")))

    assert result.status is LoopStatus.completed
    recovery_entry = next(
        entry
        for entry in result.runtime_io_trace
        if entry.operation_kind is RuntimeIoOperationKind.recovery_load
    )
    assert recovery_entry.execution_class is RuntimeIoExecutionClass.synchronous_fallback_only
    assert recovery_entry.thread_offloaded is False
    assert recovery_entry.metadata["fallback_reason"] == "thread_offload_not_supported"


def test_orchestrator_offloads_opt_in_recovery_support_calls() -> None:
    loader = _ThreadOffloadSafeRecoveryLoader()
    reconciler = _ThreadOffloadSafeReconciler()
    orchestrator = _orchestrator(
        config=RunConfig(mode=AgentMode.recovery_mode),
        recovery_loader=loader,
        recovery_reconciler=reconciler,
    )
    main_thread_id = threading.get_ident()

    result = asyncio.run(orchestrator.run_once(LoopRequest(task_id="task-io-2")))

    assert result.status is LoopStatus.completed
    recovery_entries = tuple(
        entry
        for entry in result.runtime_io_trace
        if entry.operation_kind
        in {
            RuntimeIoOperationKind.recovery_load,
            RuntimeIoOperationKind.recovery_reconcile,
        }
    )
    assert len(recovery_entries) == 2
    assert all(
        entry.execution_class is RuntimeIoExecutionClass.thread_offloaded
        for entry in recovery_entries
    )
    assert all(entry.thread_offloaded is True for entry in recovery_entries)
    assert loader.thread_id is not None and loader.thread_id != main_thread_id
    assert reconciler.thread_id is not None and reconciler.thread_id != main_thread_id


def test_orchestrator_records_policy_evaluation_as_event_loop_safe() -> None:
    orchestrator = _orchestrator(config=RunConfig(mode=AgentMode.dry_run))

    result = asyncio.run(orchestrator.run_once())

    assert result.status is LoopStatus.completed
    policy_entry = next(
        entry
        for entry in result.runtime_io_trace
        if entry.operation_kind is RuntimeIoOperationKind.policy_evaluate
    )
    assert policy_entry.execution_class is RuntimeIoExecutionClass.event_loop_safe
    assert policy_entry.thread_offloaded is False


def test_orchestrator_preserves_runtime_io_failure_diagnostics() -> None:
    orchestrator = _orchestrator(
        config=RunConfig(mode=AgentMode.recovery_mode),
        recovery_loader=_ExplodingThreadOffloadSafeRecoveryLoader(),
    )
    orchestrator.retry_policy = RetryPolicy(max_attempts=1)

    result = asyncio.run(orchestrator.run_once(LoopRequest(task_id="task-io-fail")))

    assert result.status is LoopStatus.aborted
    assert result.error_type == "RuntimeError"
    assert len(result.runtime_io_trace) == 1
    failure_entry = result.runtime_io_trace[0]
    assert failure_entry.operation_kind is RuntimeIoOperationKind.recovery_load
    assert failure_entry.success is False
    assert failure_entry.execution_class is RuntimeIoExecutionClass.thread_offloaded
    assert failure_entry.error_type == "RuntimeError"
    assert failure_entry.error_message == "recovery load exploded"
