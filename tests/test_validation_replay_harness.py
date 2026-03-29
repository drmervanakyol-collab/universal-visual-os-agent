from __future__ import annotations

import asyncio
from pathlib import Path

from universal_visual_os_agent.actions.models import ActionIntent, ActionResult
from universal_visual_os_agent.app import LoopPlan
from universal_visual_os_agent.app.interfaces import LoopActionExecutor, LoopPlanner, TransitionVerifier
from universal_visual_os_agent.app.models import LoopStage, LoopStatus
from universal_visual_os_agent.config import AgentMode
from universal_visual_os_agent.planning.models import PlannerDecision
from universal_visual_os_agent.policy import (
    PolicyRule,
    PolicyRuleSet,
    ProtectedContextAssessment,
    ProtectedContextStatus,
    RuleBasedPolicyEngine,
    StaticProtectedContextDetector,
)
from universal_visual_os_agent.recovery.interfaces import RecoverySnapshotLoader, StateReconciler
from universal_visual_os_agent.recovery.models import ReconciliationResult, RecoverySnapshot
from universal_visual_os_agent.replay import (
    DeterministicReplaySettings,
    ReplayEntry,
    ReplayHarness,
    ReplaySession,
    build_synthetic_replay_session,
)
from universal_visual_os_agent.semantics import SemanticStateSnapshot
from universal_visual_os_agent.testing import (
    ValidationReport,
    build_recovery_snapshot,
    make_environment_issue,
    summarize_module_safety,
)
from universal_visual_os_agent.verification import (
    SemanticTransitionExpectation,
    VerificationResult,
    VerificationStatus,
)


class AllowingPlanner(LoopPlanner):
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
            decision=PlannerDecision(goal="validate", rationale="replay"),
            proposed_action=ActionIntent(action_type="click"),
            expectation=SemanticTransitionExpectation(summary="snapshot verified"),
        )


class SatisfiedVerifier(TransitionVerifier):
    def verify(self, expectation, transition) -> VerificationResult:
        del expectation, transition
        return VerificationResult(status=VerificationStatus.satisfied, summary="verified")


class StaticRecoveryLoader(RecoverySnapshotLoader):
    def __init__(self, snapshot: RecoverySnapshot) -> None:
        self._snapshot = snapshot

    def load_latest(self, task_id: str) -> RecoverySnapshot | None:
        if task_id != self._snapshot.task.task_id:
            return None
        return self._snapshot


class StaticReconciler(StateReconciler):
    def reconcile(self, snapshot: RecoverySnapshot, observed_state=None) -> ReconciliationResult:
        del snapshot, observed_state
        return ReconciliationResult(safe_to_resume=True, summary="reconciled")


class CountingExecutor(LoopActionExecutor):
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, action: ActionIntent) -> ActionResult:
        del action
        self.calls += 1
        return ActionResult(accepted=False, simulated=True)


def _policy_engine() -> RuleBasedPolicyEngine:
    return RuleBasedPolicyEngine(
        ruleset=PolicyRuleSet(
            allowlist=(
                PolicyRule(
                    rule_id="allow-loop",
                    description="Allow orchestrator step",
                    action_types=("orchestration_step",),
                ),
            ),
        ),
        protected_context_detector=StaticProtectedContextDetector(
            assessment=ProtectedContextAssessment(status=ProtectedContextStatus.clear, reason="clear")
        ),
    )


def test_replay_harness_flow(replay_mode_config) -> None:
    session = build_synthetic_replay_session(
        ["Submit", "Confirm"],
        settings=DeterministicReplaySettings(seed=7),
    )
    harness = ReplayHarness(
        config=replay_mode_config,
        session=session,
        policy_engine=_policy_engine(),
        planner=AllowingPlanner(),
        verifier=SatisfiedVerifier(),
    )

    result = asyncio.run(harness.run())

    assert result.status is LoopStatus.completed
    assert len(result.results) == 2
    assert all(item.status is LoopStatus.completed for item in result.results)
    assert result.results[0].executed_stages == (
        LoopStage.observe,
        LoopStage.diff,
        LoopStage.semantic_rebuild,
        LoopStage.policy_check,
        LoopStage.plan,
        LoopStage.verify,
    )


def test_deterministic_mode_behavior() -> None:
    settings = DeterministicReplaySettings(seed=42, disable_noise=True)

    session_a = build_synthetic_replay_session(["A", "B"], settings=settings)
    session_b = build_synthetic_replay_session(["A", "B"], settings=settings)

    assert session_a == session_b
    assert session_a.metadata["noise_disabled"] is True
    assert session_a.entries[0].semantic_snapshot is not None
    assert session_a.entries[0].semantic_snapshot.metadata["noise_disabled"] is True


def test_validation_report_formatting_and_content() -> None:
    report = ValidationReport(
        task="Phase 7 validation",
        files_changed=("src/replay/harness.py",),
        executed_checks=("pytest",),
        static_reasoning_only=("No live capture executed.",),
        environment_issues=(
            make_environment_issue("Temp directory permissions restricted", details="Switched to workspace fixture."),
        ),
        module_summary=summarize_module_safety(
            safe_modules=("universal_visual_os_agent.replay",),
            unsafe_modules=("universal_visual_os_agent.integrations.windows",),
        ),
        actually_executed=("pytest -q tests",),
        simulated=("replay session execution",),
    )

    markdown = report.to_markdown()

    assert "## Executed Checks" in markdown
    assert "## Static Reasoning Only" in markdown
    assert "## Environment Issues" in markdown
    assert "Temp directory permissions restricted" in markdown
    assert "universal_visual_os_agent.replay" in markdown
    assert "universal_visual_os_agent.integrations.windows" in markdown


def test_safe_handling_of_missing_replay_data(replay_mode_config) -> None:
    session = ReplaySession(
        session_id="missing-semantic",
        entries=(
            ReplayEntry(
                request=build_synthetic_replay_session(["Only"], settings=DeterministicReplaySettings(seed=1)).entries[0].request,
                frame=build_synthetic_replay_session(["Only"], settings=DeterministicReplaySettings(seed=1)).entries[0].frame,
                semantic_snapshot=None,
            ),
        ),
    )
    harness = ReplayHarness(
        config=replay_mode_config,
        session=session,
        policy_engine=_policy_engine(),
        planner=AllowingPlanner(),
        verifier=SatisfiedVerifier(),
    )

    result = asyncio.run(harness.run())

    assert result.status is LoopStatus.aborted
    assert result.missing_replay_data is True
    assert result.safe_abort_reason == "Replay session contains missing data."


def test_recovery_mode_replay_setup(recovery_mode_config, recovery_mode_request) -> None:
    snapshot = build_recovery_snapshot(recovery_mode_request.task_id or "task-recovery")
    entry = build_synthetic_replay_session(["Recover"], settings=DeterministicReplaySettings(seed=5)).entries[0]
    session = ReplaySession(
        session_id="recovery-session",
        entries=(ReplayEntry(request=recovery_mode_request, frame=entry.frame, semantic_snapshot=entry.semantic_snapshot, diff=entry.diff),),
    )
    harness = ReplayHarness(
        config=recovery_mode_config,
        session=session,
        policy_engine=_policy_engine(),
        planner=AllowingPlanner(),
        verifier=SatisfiedVerifier(),
        recovery_loader=StaticRecoveryLoader(snapshot),
        recovery_reconciler=StaticReconciler(),
    )

    result = asyncio.run(harness.run())

    assert result.status is LoopStatus.completed
    assert LoopStage.recovery_load in result.results[0].executed_stages
    assert LoopStage.recovery_reconcile in result.results[0].executed_stages


def test_no_live_execution_in_validation_paths(replay_mode_config) -> None:
    session = build_synthetic_replay_session(["Validate"], settings=DeterministicReplaySettings(seed=9))
    executor = CountingExecutor()
    harness = ReplayHarness(
        config=replay_mode_config,
        session=session,
        policy_engine=_policy_engine(),
        planner=AllowingPlanner(),
        verifier=SatisfiedVerifier(),
        action_executor=executor,
    )

    result = asyncio.run(harness.run())

    assert result.status is LoopStatus.completed
    assert result.live_execution_attempted is False
    assert executor.calls == 0
