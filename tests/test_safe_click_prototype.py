from __future__ import annotations

from dataclasses import replace

from test_semantic_candidate_exposure import _scored_snapshot

from universal_visual_os_agent.actions import (
    ObserveOnlyActionIntentScaffolder,
    SafeClickPrototypeExecutor,
    SafeClickPrototypeStatus,
)
from universal_visual_os_agent.config import AgentMode, RunConfig
from universal_visual_os_agent.geometry import ScreenMetrics, VirtualDesktopMetrics
from universal_visual_os_agent.policy import (
    ProtectedContextAssessment,
    ProtectedContextStatus,
    RuleBasedPolicyEngine,
    StaticProtectedContextDetector,
)
from universal_visual_os_agent.semantics import (
    CandidateExposureOptions,
    ObserveOnlyCandidateExposer,
    SemanticCandidateClass,
)


class _RecordingClickTransport:
    def __init__(self) -> None:
        self.points = []

    def click(self, point) -> None:
        self.points.append(point)


class _ExplodingClickTransport:
    def click(self, point) -> None:
        del point
        raise RuntimeError("safe click transport exploded")


def _policy_engine(*, protected_status: ProtectedContextStatus = ProtectedContextStatus.clear):
    return RuleBasedPolicyEngine(
        protected_context_detector=StaticProtectedContextDetector(
            assessment=ProtectedContextAssessment(
                status=protected_status,
                reason="protected" if protected_status is ProtectedContextStatus.protected else "clear",
            )
        )
    )


def _virtual_metrics() -> VirtualDesktopMetrics:
    return VirtualDesktopMetrics(
        displays=(
            ScreenMetrics(
                width_px=1920,
                height_px=1080,
                display_id="primary",
                is_primary=True,
            ),
        )
    )


def _eligible_button_intent():
    snapshot = _scored_snapshot()
    exposure_result = ObserveOnlyCandidateExposer().expose(
        snapshot,
        options=CandidateExposureOptions(
            minimum_score=0.9,
            candidate_classes=(SemanticCandidateClass.button_like,),
            limit=1,
            include_only_visible=True,
        ),
    )
    assert exposure_result.success is True
    assert exposure_result.exposure_view is not None
    assert exposure_result.exposure_view.candidates
    scaffolding_result = ObserveOnlyActionIntentScaffolder().scaffold(
        snapshot,
        exposure_view=exposure_result.exposure_view,
    )
    assert scaffolding_result.success is True
    assert scaffolding_result.scaffold_view is not None
    return snapshot, scaffolding_result.scaffold_view.intents[0]


def test_safe_click_prototype_stays_dry_run_only_when_flag_is_off() -> None:
    snapshot, intent = _eligible_button_intent()
    transport = _RecordingClickTransport()
    executor = SafeClickPrototypeExecutor(
        policy_engine=_policy_engine(),
        click_transport=transport,
    )

    result = executor.handle(
        intent,
        config=RunConfig(mode=AgentMode.safe_action_mode),
        metrics=_virtual_metrics(),
        snapshot=snapshot,
        execute=True,
    )

    assert result.success is True
    assert result.execution is not None
    assert result.execution.status is SafeClickPrototypeStatus.dry_run_only
    assert "real_click_mode_enabled" in result.execution.blocked_gate_ids
    assert result.execution.executed is False
    assert result.execution.simulated is True
    assert transport.points == []


def test_safe_click_prototype_blocks_when_safety_gates_fail() -> None:
    snapshot, intent = _eligible_button_intent()
    transport = _RecordingClickTransport()
    executor = SafeClickPrototypeExecutor(
        policy_engine=_policy_engine(protected_status=ProtectedContextStatus.protected),
        click_transport=transport,
    )

    result = executor.handle(
        intent,
        config=RunConfig(mode=AgentMode.safe_action_mode, allow_live_input=True),
        metrics=_virtual_metrics(),
        snapshot=snapshot,
        execute=True,
    )

    assert result.success is True
    assert result.execution is not None
    assert result.execution.status is SafeClickPrototypeStatus.blocked
    assert "policy_allow" in result.execution.blocked_gate_ids
    assert result.execution.policy_decision is not None
    assert result.execution.policy_decision.reason == "Protected context detected."
    assert transport.points == []


def test_safe_click_prototype_blocks_unsupported_candidate_action_types() -> None:
    snapshot, intent = _eligible_button_intent()
    unsupported_intent = replace(intent, action_type="hover")
    transport = _RecordingClickTransport()
    executor = SafeClickPrototypeExecutor(
        policy_engine=_policy_engine(),
        click_transport=transport,
    )

    result = executor.handle(
        unsupported_intent,
        config=RunConfig(mode=AgentMode.safe_action_mode, allow_live_input=True),
        metrics=_virtual_metrics(),
        snapshot=snapshot,
        execute=True,
    )

    assert result.success is True
    assert result.execution is not None
    assert result.execution.status is SafeClickPrototypeStatus.blocked
    assert "supported_action_type" in result.execution.blocked_gate_ids
    assert transport.points == []


def test_safe_click_prototype_preserves_simulated_allowed_path() -> None:
    snapshot, intent = _eligible_button_intent()
    transport = _RecordingClickTransport()
    executor = SafeClickPrototypeExecutor(
        policy_engine=_policy_engine(),
        click_transport=transport,
    )

    result = executor.handle(
        intent,
        config=RunConfig(mode=AgentMode.safe_action_mode, allow_live_input=True),
        metrics=_virtual_metrics(),
        snapshot=snapshot,
        execute=False,
    )

    assert result.success is True
    assert result.execution is not None
    assert result.execution.status is SafeClickPrototypeStatus.real_click_allowed
    assert result.execution.executed is False
    assert result.execution.simulated is True
    assert result.execution.target_screen_point is not None
    assert transport.points == []


def test_safe_click_prototype_executes_one_narrowly_scoped_real_click() -> None:
    snapshot, intent = _eligible_button_intent()
    transport = _RecordingClickTransport()
    executor = SafeClickPrototypeExecutor(
        policy_engine=_policy_engine(),
        click_transport=transport,
    )

    result = executor.handle(
        intent,
        config=RunConfig(mode=AgentMode.safe_action_mode, allow_live_input=True),
        metrics=_virtual_metrics(),
        snapshot=snapshot,
        execute=True,
    )

    assert result.success is True
    assert result.execution is not None
    assert result.execution.status is SafeClickPrototypeStatus.real_click_executed
    assert result.execution.executed is True
    assert result.execution.simulated is False
    assert result.execution.blocked_gate_ids == ()
    assert len(transport.points) == 1
    assert result.execution.target_screen_point == transport.points[0]


def test_safe_click_prototype_does_not_propagate_unhandled_exceptions() -> None:
    snapshot, intent = _eligible_button_intent()
    executor = SafeClickPrototypeExecutor(
        policy_engine=_policy_engine(),
        click_transport=_ExplodingClickTransport(),
    )

    result = executor.handle(
        intent,
        config=RunConfig(mode=AgentMode.safe_action_mode, allow_live_input=True),
        metrics=_virtual_metrics(),
        snapshot=snapshot,
        execute=True,
    )

    assert result.success is False
    assert result.error_code == "safe_click_execution_exception"
    assert result.error_message == "safe click transport exploded"
