from __future__ import annotations

from dataclasses import replace

from universal_visual_os_agent.actions import (
    ActionPrecondition,
    ActionRequirementStatus,
    ActionSafetyGate,
    ActionTargetValidation,
    SafeClickPrototypeExecutor,
)
from universal_visual_os_agent.config import AgentMode, RunConfig
from universal_visual_os_agent.geometry import ScreenMetrics, VirtualDesktopMetrics
from universal_visual_os_agent.policy import (
    ProtectedContextAssessment,
    ProtectedContextStatus,
    RuleBasedPolicyEngine,
    StaticProtectedContextDetector,
)
from universal_visual_os_agent.scenarios import (
    ObserveActVerifyScenarioRunner,
    ScenarioActionDisposition,
    ScenarioCandidateSelectionConstraint,
    ScenarioDefinition,
    ScenarioExecutionEligibility,
    ScenarioRunStatus,
    ScenarioStepDefinition,
    ScenarioActionStepStage,
)
from universal_visual_os_agent.semantics import (
    CandidateExposureOptions,
    FullDesktopCaptureSemanticInputAdapter,
    GeometricLayoutRegionAnalyzer,
    ObserveOnlyCandidateExposer,
    ObserveOnlyCandidateGenerator,
    ObserveOnlyCandidateScorer,
    OcrAwareSemanticLayoutEnricher,
    PreparedSemanticStateBuilder,
    PreparedSemanticTextExtractionAdapter,
    SemanticCandidateClass,
)
from universal_visual_os_agent.semantics.semantic_delta import SemanticDeltaCategory
from universal_visual_os_agent.recovery.models import RecoveryHandlingDisposition
from universal_visual_os_agent.verification.models import (
    ExpectedSemanticChange,
    ExpectedSemanticOutcome,
    SemanticTransitionExpectation,
)
from test_semantic_candidate_generation import (
    _StaticResponseBackend,
    _candidate_rich_response,
    _capture_result,
    _payload,
)


class _StaticCaptureProvider:
    def __init__(self, *results) -> None:
        self._results = list(results)
        self.calls = 0

    def capture_frame(self):
        if not self._results:
            raise RuntimeError("capture provider exhausted")
        self.calls += 1
        if len(self._results) == 1:
            return self._results[0]
        return self._results.pop(0)


class _RecordingClickTransport:
    def __init__(self) -> None:
        self.points = []

    def click(self, point) -> None:
        self.points.append(point)


class _ExplodingScenarioActionRunner(ObserveActVerifyScenarioRunner):
    def _resolve_action(
        self,
        step,
        *,
        snapshot,
        exposure_view,
        matched_candidate_ids,
        config,
        metrics,
        policy_context,
        execute,
        state_machine,
    ):
        del (
            step,
            snapshot,
            exposure_view,
            matched_candidate_ids,
            config,
            metrics,
            policy_context,
            execute,
            state_machine,
        )
        raise RuntimeError("scenario action runner exploded")


def _policy_engine(
    *,
    protected_status: ProtectedContextStatus = ProtectedContextStatus.clear,
) -> RuleBasedPolicyEngine:
    return RuleBasedPolicyEngine(
        protected_context_detector=StaticProtectedContextDetector(
            assessment=ProtectedContextAssessment(
                status=protected_status,
                reason=(
                    "protected"
                    if protected_status is ProtectedContextStatus.protected
                    else "clear"
                ),
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


def _text_adapter() -> PreparedSemanticTextExtractionAdapter:
    return PreparedSemanticTextExtractionAdapter(
        text_backend=_StaticResponseBackend(_candidate_rich_response)
    )


def _scored_snapshot():
    capture_result = _capture_result(_payload())
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(capture_result)
    state_result = PreparedSemanticStateBuilder().build(preparation)
    text_result = _text_adapter().extract(preparation, state_result)
    assert text_result.success is True
    assert text_result.enriched_snapshot is not None
    layout_result = GeometricLayoutRegionAnalyzer().analyze(text_result.enriched_snapshot)
    assert layout_result.success is True
    assert layout_result.snapshot is not None
    semantic_layout_result = OcrAwareSemanticLayoutEnricher().enrich(layout_result.snapshot)
    assert semantic_layout_result.success is True
    assert semantic_layout_result.snapshot is not None
    generation_result = ObserveOnlyCandidateGenerator().generate(semantic_layout_result.snapshot)
    assert generation_result.success is True
    assert generation_result.snapshot is not None
    scoring_result = ObserveOnlyCandidateScorer().score(generation_result.snapshot)
    assert scoring_result.success is True
    assert scoring_result.snapshot is not None
    return scoring_result.snapshot


def _button_candidate_id() -> str:
    snapshot = _scored_snapshot()
    exposure_result = ObserveOnlyCandidateExposer().expose(
        snapshot,
        options=CandidateExposureOptions(
            candidate_classes=(SemanticCandidateClass.button_like,),
            minimum_score=0.9,
            limit=1,
            include_only_visible=True,
        ),
    )
    assert exposure_result.success is True
    assert exposure_result.exposure_view is not None
    return exposure_result.exposure_view.candidates[0].candidate_id


def _expectation(candidate_id: str) -> SemanticTransitionExpectation:
    return SemanticTransitionExpectation(
        summary="The expected candidate should appear in the observed semantic state.",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id=f"{candidate_id}-appeared",
                category=SemanticDeltaCategory.candidate,
                item_id=candidate_id,
                expected_change=ExpectedSemanticChange.appeared,
                summary=f"{candidate_id} appears",
            ),
        ),
    )


def _preconditions() -> tuple[ActionPrecondition, ...]:
    return (
        ActionPrecondition(
            requirement_id="candidate_visible",
            summary="Candidate must be visible.",
            status=ActionRequirementStatus.satisfied,
        ),
    )


def _target_validations() -> tuple[ActionTargetValidation, ...]:
    return (
        ActionTargetValidation(
            validation_id="candidate_id_consistency",
            summary="Candidate id must remain stable.",
            status=ActionRequirementStatus.satisfied,
        ),
    )


def _safety_gates() -> tuple[ActionSafetyGate, ...]:
    return (
        ActionSafetyGate(
            gate_id="dry_run_only_enforced",
            summary="Scenario action flow remains safety-first.",
            status=ActionRequirementStatus.satisfied,
        ),
    )


def _dry_run_step(candidate_id: str) -> ScenarioStepDefinition:
    return ScenarioStepDefinition(
        step_id="confirm-step",
        summary="Observe, simulate, and verify the confirm button.",
        action_type="candidate_select",
        candidate_constraint=ScenarioCandidateSelectionConstraint(
            candidate_classes=(SemanticCandidateClass.button_like,),
            allowed_candidate_ids=(candidate_id,),
            minimum_score=0.9,
            maximum_candidate_rank=5,
        ),
        expected_outcome=_expectation(candidate_id),
        precondition_requirements=_preconditions(),
        target_validation_requirements=_target_validations(),
        safety_gating_requirements=_safety_gates(),
        execution_eligibility=ScenarioExecutionEligibility.dry_run_only,
    )


def _real_click_step(candidate_id: str) -> ScenarioStepDefinition:
    return replace(
        _dry_run_step(candidate_id),
        candidate_constraint=ScenarioCandidateSelectionConstraint(
            candidate_classes=(SemanticCandidateClass.button_like,),
            allowed_candidate_ids=(candidate_id,),
            minimum_score=0.9,
            maximum_candidate_rank=5,
            allow_real_click_prototype=True,
        ),
        execution_eligibility=ScenarioExecutionEligibility.real_click_eligible,
    )


def _runner(*capture_results, safe_click_executor=None):
    return ObserveActVerifyScenarioRunner(
        capture_provider=_StaticCaptureProvider(*capture_results),
        text_adapter=_text_adapter(),
        safe_click_executor=safe_click_executor,
    )


def test_scenario_action_flow_runs_successful_dry_run_only_path() -> None:
    candidate_id = _button_candidate_id()
    scenario = ScenarioDefinition(
        scenario_id="dry-run-confirm-button",
        title="Dry Run Confirm Button",
        summary="The scenario should stay dry-run only and still verify.",
        steps=(_dry_run_step(candidate_id),),
    )
    capture_provider = _StaticCaptureProvider(_capture_result(_payload()))
    runner = ObserveActVerifyScenarioRunner(
        capture_provider=capture_provider,
        text_adapter=_text_adapter(),
    )

    result = runner.run(
        scenario,
        config=RunConfig(mode=AgentMode.safe_action_mode, allow_live_input=True),
        metrics=_virtual_metrics(),
        execute=True,
    )

    assert result.success is True
    assert result.scenario_run is not None
    assert result.scenario_run.status is ScenarioRunStatus.completed
    assert result.scenario_run.dry_run_only_step_count == 1
    assert result.scenario_run.non_executing is True
    assert result.scenario_run.live_execution_attempted is False
    step_run = result.scenario_run.step_runs[0]
    assert step_run.final_stage is ScenarioActionStepStage.verified
    assert step_run.action_disposition is ScenarioActionDisposition.dry_run_only
    assert step_run.safe_click_execution is None
    assert step_run.selected_candidate_id == candidate_id
    assert step_run.selected_intent_id is not None
    assert step_run.stage_history == (
        ScenarioActionStepStage.started,
        ScenarioActionStepStage.observed,
        ScenarioActionStepStage.understood,
        ScenarioActionStepStage.intent_selected,
        ScenarioActionStepStage.dry_run_evaluated,
        ScenarioActionStepStage.action_resolved,
        ScenarioActionStepStage.post_observed,
        ScenarioActionStepStage.post_understood,
        ScenarioActionStepStage.verified,
    )
    assert step_run.verification_result is not None
    assert capture_provider.calls == 2


def test_scenario_action_flow_marks_blocked_real_click_path() -> None:
    candidate_id = _button_candidate_id()
    scenario = ScenarioDefinition(
        scenario_id="blocked-confirm-button",
        title="Blocked Confirm Button",
        summary="Protected context should block the real-click prototype path.",
        steps=(_real_click_step(candidate_id),),
        real_click_eligible=True,
    )
    runner = _runner(
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
    assert result.scenario_run.status is ScenarioRunStatus.failed
    step_run = result.scenario_run.step_runs[0]
    assert step_run.final_stage is ScenarioActionStepStage.failed
    assert step_run.action_disposition is ScenarioActionDisposition.blocked
    assert step_run.safe_click_execution is not None
    assert step_run.safe_click_execution.status.value == "blocked"
    assert "policy_allow" in step_run.safe_click_execution.blocked_gate_ids
    assert step_run.live_execution_attempted is False


def test_scenario_action_flow_marks_incomplete_when_no_candidates_match() -> None:
    scenario = ScenarioDefinition(
        scenario_id="missing-target",
        title="Missing Target",
        summary="The scenario should stay incomplete when no candidate matches.",
        steps=(_dry_run_step("missing-candidate-id"),),
    )

    result = _runner(_capture_result(_payload())).run(scenario)

    assert result.success is True
    assert result.scenario_run is not None
    assert result.scenario_run.status is ScenarioRunStatus.incomplete
    step_run = result.scenario_run.step_runs[0]
    assert step_run.final_stage is ScenarioActionStepStage.incomplete
    assert step_run.action_disposition is ScenarioActionDisposition.incomplete
    assert step_run.selected_candidate_id is None
    assert step_run.selected_intent_id is None
    assert step_run.stage_history == (
        ScenarioActionStepStage.started,
        ScenarioActionStepStage.observed,
        ScenarioActionStepStage.understood,
        ScenarioActionStepStage.incomplete,
    )


def test_scenario_action_flow_supports_verify_after_action_simulation() -> None:
    candidate_id = _button_candidate_id()
    scenario = ScenarioDefinition(
        scenario_id="eligible-confirm-button",
        title="Eligible Confirm Button",
        summary="The real-click prototype should be allowed without executing.",
        steps=(_real_click_step(candidate_id),),
        real_click_eligible=True,
    )
    runner = _runner(
        _capture_result(_payload()),
        safe_click_executor=SafeClickPrototypeExecutor(
            policy_engine=_policy_engine()
        ),
    )

    result = runner.run(
        scenario,
        config=RunConfig(mode=AgentMode.safe_action_mode, allow_live_input=True),
        metrics=_virtual_metrics(),
        execute=False,
    )

    assert result.success is True
    assert result.scenario_run is not None
    assert result.scenario_run.status is ScenarioRunStatus.completed
    step_run = result.scenario_run.step_runs[0]
    assert step_run.final_stage is ScenarioActionStepStage.verified
    assert step_run.action_disposition is ScenarioActionDisposition.real_click_eligible
    assert step_run.safe_click_execution is not None
    assert step_run.safe_click_execution.status.value == "real_click_allowed"
    assert step_run.recovery_plan is not None
    assert (
        step_run.recovery_plan.disposition
        is RecoveryHandlingDisposition.await_user_confirmation
    )
    assert step_run.recovery_plan.awaiting_user_confirmation is True
    assert step_run.verification_result is not None
    assert step_run.verification_result.success is True
    assert result.scenario_run.metadata["awaiting_user_confirmation_step_ids"] == (
        "confirm-step",
    )
    assert step_run.metadata["awaiting_user_confirmation"] is True


def test_scenario_action_flow_executes_only_the_existing_narrow_click_prototype() -> None:
    candidate_id = _button_candidate_id()
    transport = _RecordingClickTransport()
    scenario = ScenarioDefinition(
        scenario_id="executed-confirm-button",
        title="Executed Confirm Button",
        summary="The existing safe-click prototype should execute one narrow click.",
        steps=(_real_click_step(candidate_id),),
        real_click_eligible=True,
    )
    runner = _runner(
        _capture_result(_payload()),
        safe_click_executor=SafeClickPrototypeExecutor(
            policy_engine=_policy_engine(),
            click_transport=transport,
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
    assert result.scenario_run.status is ScenarioRunStatus.completed
    assert result.scenario_run.non_executing is False
    assert result.scenario_run.live_execution_attempted is True
    step_run = result.scenario_run.step_runs[0]
    assert step_run.action_disposition is ScenarioActionDisposition.real_click_executed
    assert step_run.live_execution_attempted is True
    assert step_run.non_executing is False
    assert step_run.safe_click_execution is not None
    assert step_run.safe_click_execution.status.value == "real_click_executed"
    assert len(transport.points) == 1


def test_scenario_action_flow_does_not_propagate_unhandled_exceptions() -> None:
    scenario = ScenarioDefinition(
        scenario_id="exploding-action-loop",
        title="Exploding Action Loop",
        summary="Unexpected exceptions should stay structured.",
        steps=(_dry_run_step(_button_candidate_id()),),
    )

    result = _ExplodingScenarioActionRunner(
        capture_provider=_StaticCaptureProvider(_capture_result(_payload())),
        text_adapter=_text_adapter(),
    ).run(scenario)

    assert result.success is False
    assert result.error_code == "scenario_action_loop_exception"
    assert result.error_message == "scenario action runner exploded"
