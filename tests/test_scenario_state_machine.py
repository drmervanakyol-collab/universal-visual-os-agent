from __future__ import annotations

from dataclasses import replace

from test_scenario_action_flow import (
    _button_candidate_id,
    _policy_engine,
    _real_click_step,
    _runner as _action_runner,
    _virtual_metrics,
)
from test_scenario_loop import (
    _runner as _observe_runner,
    _step_for_candidate,
)

from universal_visual_os_agent.actions import SafeClickPrototypeExecutor
from universal_visual_os_agent.config import AgentMode, RunConfig
from universal_visual_os_agent.policy import ProtectedContextStatus
from universal_visual_os_agent.scenarios import (
    ScenarioActionDisposition,
    ScenarioActionStepStage,
    ScenarioDefinition,
    ScenarioFlowState,
    ScenarioStepStage,
)
from universal_visual_os_agent.semantics.semantic_delta import SemanticDeltaCategory
from universal_visual_os_agent.verification.models import (
    ExpectedSemanticChange,
    ExpectedSemanticOutcome,
    SemanticTransitionExpectation,
)
from test_semantic_candidate_generation import _capture_result, _payload


def _assert_transition_telemetry(trace) -> None:
    assert trace is not None
    assert trace.transitions
    assert trace.transitions[0].from_state is None
    assert trace.transitions[0].to_state is ScenarioFlowState.started
    assert trace.state_history[0] is ScenarioFlowState.started
    assert tuple(transition.transition_index for transition in trace.transitions) == tuple(
        range(1, len(trace.transitions) + 1)
    )
    assert tuple(transition.transition_id for transition in trace.transitions) == tuple(
        f"{trace.trace_id}:{index}"
        for index in range(1, len(trace.transitions) + 1)
    )
    assert all(transition.occurred_at.tzinfo is not None for transition in trace.transitions)
    assert all(transition.latency_ms >= 0.0 for transition in trace.transitions)


def test_state_machine_records_successful_observe_understand_verify_transitions() -> None:
    candidate_id = _button_candidate_id()
    scenario = ScenarioDefinition(
        scenario_id="fsm-observe-success",
        title="FSM Observe Success",
        summary="Successful observe-understand-verify steps should emit explicit FSM states.",
        steps=(_step_for_candidate(candidate_id),),
    )

    result = _observe_runner(_capture_result(_payload())).run(scenario)

    assert result.success is True
    assert result.scenario_run is not None
    step_run = result.scenario_run.step_runs[0]
    trace = step_run.state_machine_trace
    _assert_transition_telemetry(trace)
    assert trace.current_state is ScenarioFlowState.verification_passed
    assert trace.state_history == (
        ScenarioFlowState.started,
        ScenarioFlowState.observed,
        ScenarioFlowState.understood,
        ScenarioFlowState.verification_passed,
    )
    assert trace.transitions[1].next_expected_signal == "semantic_understanding"
    assert trace.transitions[2].next_expected_signal == "verification_result"
    assert trace.transitions[3].next_expected_signal == "scenario_step_complete"
    assert step_run.final_stage is ScenarioStepStage.verified
    assert step_run.metadata["state_machine_current_state"] == "verification_passed"


def test_state_machine_records_blocked_action_transition_path() -> None:
    candidate_id = _button_candidate_id()
    scenario = ScenarioDefinition(
        scenario_id="fsm-blocked-action",
        title="FSM Blocked Action",
        summary="Blocked safe-click attempts should end in the blocked FSM state.",
        steps=(_real_click_step(candidate_id),),
        real_click_eligible=True,
    )
    runner = _action_runner(
        _capture_result(_payload()),
        safe_click_executor=SafeClickPrototypeExecutor(
            policy_engine=_policy_engine(
                protected_status=ProtectedContextStatus.protected
            )
        ),
    )

    result = runner.run(
        scenario,
        config=RunConfig(mode=AgentMode.safe_action_mode, allow_live_input=True),
        metrics=_virtual_metrics(),
        execute=True,
    )

    assert result.success is True
    assert result.scenario_run is not None
    step_run = result.scenario_run.step_runs[0]
    trace = step_run.state_machine_trace
    _assert_transition_telemetry(trace)
    assert step_run.action_disposition is ScenarioActionDisposition.blocked
    assert step_run.final_stage is ScenarioActionStepStage.failed
    assert trace.current_state is ScenarioFlowState.blocked
    assert trace.state_history == (
        ScenarioFlowState.started,
        ScenarioFlowState.observed,
        ScenarioFlowState.understood,
        ScenarioFlowState.candidate_selected,
        ScenarioFlowState.intent_built,
        ScenarioFlowState.dry_run_passed,
        ScenarioFlowState.blocked,
    )
    assert trace.transitions[-1].block_reason == step_run.reason
    assert trace.transitions[-1].recovery_hint


def test_state_machine_records_verification_failed_transition_path() -> None:
    candidate_id = _button_candidate_id()
    failing_step = replace(
        _step_for_candidate(candidate_id),
        expected_outcome=SemanticTransitionExpectation(
            summary="The candidate should disappear, which will fail.",
            expected_outcomes=(
                ExpectedSemanticOutcome(
                    outcome_id=f"{candidate_id}-disappeared",
                    category=SemanticDeltaCategory.candidate,
                    item_id=candidate_id,
                    expected_change=ExpectedSemanticChange.disappeared,
                    summary=f"{candidate_id} disappears",
                ),
            ),
        ),
    )
    scenario = ScenarioDefinition(
        scenario_id="fsm-verification-failed",
        title="FSM Verification Failed",
        summary="Verification failures should end in the explicit verification_failed state.",
        steps=(failing_step,),
    )

    result = _observe_runner(_capture_result(_payload())).run(scenario)

    assert result.success is True
    assert result.scenario_run is not None
    step_run = result.scenario_run.step_runs[0]
    trace = step_run.state_machine_trace
    _assert_transition_telemetry(trace)
    assert step_run.final_stage is ScenarioStepStage.failed
    assert trace.current_state is ScenarioFlowState.verification_failed
    assert trace.state_history == (
        ScenarioFlowState.started,
        ScenarioFlowState.observed,
        ScenarioFlowState.understood,
        ScenarioFlowState.verification_failed,
    )
    assert trace.transitions[-1].block_reason == step_run.reason
    assert trace.transitions[-1].next_expected_signal == "verification_delta"


def test_state_machine_records_recovery_needed_for_incomplete_inputs() -> None:
    scenario = ScenarioDefinition(
        scenario_id="fsm-recovery-needed",
        title="FSM Recovery Needed",
        summary="Missing candidate matches should produce an explicit recovery-needed state.",
        steps=(_step_for_candidate("missing-candidate-id"),),
    )

    result = _observe_runner(_capture_result(_payload())).run(scenario)

    assert result.success is True
    assert result.scenario_run is not None
    step_run = result.scenario_run.step_runs[0]
    trace = step_run.state_machine_trace
    _assert_transition_telemetry(trace)
    assert step_run.final_stage is ScenarioStepStage.incomplete
    assert trace.current_state is ScenarioFlowState.recovery_needed
    assert trace.state_history == (
        ScenarioFlowState.started,
        ScenarioFlowState.observed,
        ScenarioFlowState.understood,
        ScenarioFlowState.recovery_needed,
    )
    assert trace.transitions[-1].block_reason == step_run.reason
    assert trace.transitions[-1].recovery_hint
    assert trace.transitions[-1].next_expected_signal == "candidate_matching"


def test_state_machine_transition_metadata_is_consistent_for_dry_run_action_flow() -> None:
    candidate_id = _button_candidate_id()
    scenario = ScenarioDefinition(
        scenario_id="fsm-dry-run-metadata",
        title="FSM Dry Run Metadata",
        summary="Dry-run action flow should expose stable FSM telemetry in step and run metadata.",
        steps=(_real_click_step(candidate_id),),
        real_click_eligible=True,
    )
    runner = _action_runner(
        _capture_result(_payload()),
        _capture_result(_payload()),
        safe_click_executor=SafeClickPrototypeExecutor(policy_engine=_policy_engine()),
    )

    result = runner.run(
        scenario,
        config=RunConfig(mode=AgentMode.safe_action_mode, allow_live_input=True),
        metrics=_virtual_metrics(),
        execute=False,
    )

    assert result.success is True
    assert result.scenario_run is not None
    scenario_run = result.scenario_run
    step_run = scenario_run.step_runs[0]
    trace = step_run.state_machine_trace
    _assert_transition_telemetry(trace)
    assert step_run.action_disposition is ScenarioActionDisposition.real_click_eligible
    assert trace.current_state is ScenarioFlowState.verification_passed
    assert trace.state_history == (
        ScenarioFlowState.started,
        ScenarioFlowState.observed,
        ScenarioFlowState.understood,
        ScenarioFlowState.candidate_selected,
        ScenarioFlowState.intent_built,
        ScenarioFlowState.dry_run_passed,
        ScenarioFlowState.execution_allowed,
        ScenarioFlowState.observed,
        ScenarioFlowState.understood,
        ScenarioFlowState.verification_passed,
    )
    assert scenario_run.metadata["state_transition_count"] == len(trace.transitions)
    assert scenario_run.metadata["step_terminal_states"] == (
        ("confirm-step", "verification_passed"),
    )
    assert step_run.metadata["state_machine_transition_count"] == len(trace.transitions)
    assert step_run.metadata["state_machine_state_history"] == tuple(
        state.value for state in trace.state_history
    )
