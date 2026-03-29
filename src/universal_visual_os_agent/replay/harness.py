"""Replay harness built on top of the async loop skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field

from universal_visual_os_agent.app import AsyncMainLoopOrchestrator, FrameDiff, LoopStatus, RetryPolicy
from universal_visual_os_agent.app.interfaces import LoopActionExecutor, LoopPlanner, TransitionVerifier
from universal_visual_os_agent.config.models import RunConfig
from universal_visual_os_agent.perception.models import CapturedFrame
from universal_visual_os_agent.policy.interfaces import PolicyEngine
from universal_visual_os_agent.recovery.interfaces import RecoverySnapshotLoader, StateReconciler
from universal_visual_os_agent.replay.models import ReplayEntry, ReplayHarnessResult, ReplaySession
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot


class MissingReplayDataError(ValueError):
    """Raised when required replay data is missing."""


@dataclass(slots=True)
class ReplayHarness:
    """Drive the async main-loop skeleton from replay session data."""

    config: RunConfig
    session: ReplaySession
    policy_engine: PolicyEngine
    planner: LoopPlanner
    verifier: TransitionVerifier
    recovery_loader: RecoverySnapshotLoader | None = None
    recovery_reconciler: StateReconciler | None = None
    action_executor: LoopActionExecutor | None = None
    timeout_seconds: float = 1.0
    retry_policy: RetryPolicy = RetryPolicy(max_attempts=1)
    _cursor: "_ReplayCursor" = field(init=False, repr=False)
    _orchestrator: AsyncMainLoopOrchestrator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._cursor = _ReplayCursor(self.session)
        self._orchestrator = AsyncMainLoopOrchestrator(
            config=self.config,
            observation_provider=ReplayObservationProvider(self._cursor),
            frame_differ=ReplayFrameDiffer(self._cursor),
            semantic_rebuilder=ReplaySemanticRebuilder(self._cursor),
            policy_engine=self.policy_engine,
            planner=self.planner,
            verifier=self.verifier,
            recovery_loader=self.recovery_loader,
            recovery_reconciler=self.recovery_reconciler,
            action_executor=self.action_executor,
            timeout_seconds=self.timeout_seconds,
            retry_policy=self.retry_policy,
        )

    async def run(self) -> ReplayHarnessResult:
        """Run the full replay session through the async orchestrator."""

        if not self.session.entries:
            return ReplayHarnessResult(
                status=LoopStatus.aborted,
                safe_abort_reason="Replay session has no entries.",
                missing_replay_data=True,
                live_execution_attempted=False,
            )

        results = []
        for entry in self.session.entries:
            result = await self._orchestrator.run_once(entry.request)
            results.append(result)
            if result.status is not LoopStatus.completed:
                return ReplayHarnessResult(
                    status=result.status,
                    results=tuple(results),
                    missing_replay_data=result.error_type == "MissingReplayDataError",
                    safe_abort_reason=_safe_abort_reason_for_result(result),
                    live_execution_attempted=any(item.live_execution_attempted for item in results),
                )

        return ReplayHarnessResult(
            status=LoopStatus.completed,
            results=tuple(results),
            live_execution_attempted=any(item.live_execution_attempted for item in results),
        )


@dataclass(slots=True)
class _ReplayCursor:
    session: ReplaySession
    index: int = 0
    active_entry: ReplayEntry | None = None

    def next_entry(self) -> ReplayEntry:
        if self.index >= len(self.session.entries):
            raise MissingReplayDataError("Replay session is exhausted.")
        entry = self.session.entries[self.index]
        self.index += 1
        self.active_entry = entry
        return entry

    def current_entry(self) -> ReplayEntry:
        if self.active_entry is None:
            raise MissingReplayDataError("Replay session has no active entry.")
        return self.active_entry


@dataclass(slots=True, frozen=True)
class ReplayObservationProvider:
    cursor: _ReplayCursor

    def observe(self, request, *, config: RunConfig) -> CapturedFrame:
        del request, config
        entry = self.cursor.next_entry()
        if entry.frame is None:
            raise MissingReplayDataError("Replay entry is missing frame data.")
        return entry.frame


@dataclass(slots=True, frozen=True)
class ReplayFrameDiffer:
    cursor: _ReplayCursor

    def diff(self, previous: CapturedFrame | None, current: CapturedFrame) -> FrameDiff:
        del previous, current
        entry = self.cursor.current_entry()
        if entry.diff is not None:
            return entry.diff
        return FrameDiff(changed=True, summary="Replay diff synthesized.")


@dataclass(slots=True, frozen=True)
class ReplaySemanticRebuilder:
    cursor: _ReplayCursor

    def rebuild(self, frame: CapturedFrame, diff: FrameDiff) -> SemanticStateSnapshot:
        del frame, diff
        entry = self.cursor.current_entry()
        if entry.semantic_snapshot is None:
            raise MissingReplayDataError("Replay entry is missing semantic snapshot data.")
        return entry.semantic_snapshot


def _safe_abort_reason_for_result(result) -> str | None:
    if result.error_type == "MissingReplayDataError":
        return "Replay session contains missing data."
    return result.safe_abort_reason
