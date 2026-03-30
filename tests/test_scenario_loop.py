from __future__ import annotations

from dataclasses import replace

from universal_visual_os_agent.actions.models import (
    ActionPrecondition,
    ActionRequirementStatus,
    ActionSafetyGate,
    ActionTargetValidation,
)
from universal_visual_os_agent.scenarios import (
    ObserveUnderstandVerifyScenarioRunner,
    ScenarioCandidateSelectionConstraint,
    ScenarioDefinition,
    ScenarioExecutionEligibility,
    ScenarioRunStatus,
    ScenarioStepDefinition,
    ScenarioStepStage,
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
)
from universal_visual_os_agent.semantics.semantic_delta import SemanticDeltaCategory
from universal_visual_os_agent.semantics.state import SemanticCandidateClass
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


class _ExplodingScenarioRunner(ObserveUnderstandVerifyScenarioRunner):
    def _understand_step(self, capture_result, step):
        del capture_result, step
        raise RuntimeError("scenario runner exploded")


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
            summary="Scenario loop remains non-executing.",
            status=ActionRequirementStatus.satisfied,
        ),
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


def _step_for_candidate(candidate_id: str) -> ScenarioStepDefinition:
    expectation = SemanticTransitionExpectation(
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
    return ScenarioStepDefinition(
        step_id="confirm-step",
        summary="Observe and verify the confirm/save candidate.",
        action_type="candidate_select",
        candidate_constraint=ScenarioCandidateSelectionConstraint(
            candidate_classes=(SemanticCandidateClass.button_like,),
            allowed_candidate_ids=(candidate_id,),
            minimum_score=0.9,
            maximum_candidate_rank=5,
        ),
        expected_outcome=expectation,
        precondition_requirements=_preconditions(),
        target_validation_requirements=_target_validations(),
        safety_gating_requirements=_safety_gates(),
        execution_eligibility=ScenarioExecutionEligibility.dry_run_only,
    )


def _runner(capture_result):
    return ObserveUnderstandVerifyScenarioRunner(
        capture_provider=_StaticCaptureProvider(capture_result),
        text_adapter=_text_adapter(),
    )


def test_scenario_loop_runs_successful_observe_understand_verify_path() -> None:
    snapshot = _scored_snapshot()
    exposure_result = ObserveOnlyCandidateExposer().expose(
        snapshot,
        options=CandidateExposureOptions(
            candidate_classes=(SemanticCandidateClass.button_like,),
            minimum_score=0.9,
            limit=5,
            include_only_visible=True,
        ),
    )
    assert exposure_result.success is True
    assert exposure_result.exposure_view is not None
    candidate_id = exposure_result.exposure_view.candidates[0].candidate_id

    scenario = ScenarioDefinition(
        scenario_id="verify-confirm-button",
        title="Verify Confirm Button",
        summary="Scenario loop should verify the button without executing anything.",
        steps=(_step_for_candidate(candidate_id),),
    )

    result = _runner(_capture_result(_payload())).run(scenario)

    assert result.success is True
    assert result.scenario_run is not None
    assert result.scenario_run.status is ScenarioRunStatus.completed
    assert result.scenario_run.signal_status == "available"
    assert result.scenario_run.live_execution_attempted is False
    step_run = result.scenario_run.step_runs[0]
    assert step_run.final_stage is ScenarioStepStage.verified
    assert step_run.stage_history == (
        ScenarioStepStage.started,
        ScenarioStepStage.observed,
        ScenarioStepStage.understood,
        ScenarioStepStage.verified,
    )
    assert step_run.matched_candidate_ids == (candidate_id,)
    assert step_run.observe_only is True
    assert step_run.non_executing is True
    assert step_run.live_execution_attempted is False
    assert step_run.verification_result is not None
    assert step_run.verification_result.success is True


def test_scenario_loop_marks_step_incomplete_when_no_candidates_match() -> None:
    scenario = ScenarioDefinition(
        scenario_id="missing-target",
        title="Missing Target",
        summary="Scenario step should stop safely when no candidate matches.",
        steps=(
            ScenarioStepDefinition(
                step_id="missing-step",
                summary="No candidate should match this allowlist.",
                action_type="candidate_select",
                candidate_constraint=ScenarioCandidateSelectionConstraint(
                    candidate_classes=(SemanticCandidateClass.button_like,),
                    allowed_candidate_ids=("missing-candidate-id",),
                    minimum_score=0.9,
                    maximum_candidate_rank=5,
                ),
                expected_outcome=SemanticTransitionExpectation(
                    summary="Unused verification because understanding will stay incomplete.",
                    expected_outcomes=(
                        ExpectedSemanticOutcome(
                            outcome_id="unused-appeared",
                            category=SemanticDeltaCategory.candidate,
                            item_id="missing-candidate-id",
                            expected_change=ExpectedSemanticChange.appeared,
                            summary="Unused expectation",
                        ),
                    ),
                ),
                precondition_requirements=_preconditions(),
                target_validation_requirements=_target_validations(),
                safety_gating_requirements=_safety_gates(),
            ),
        ),
    )

    result = _runner(_capture_result(_payload())).run(scenario)

    assert result.success is True
    assert result.scenario_run is not None
    assert result.scenario_run.status is ScenarioRunStatus.incomplete
    step_run = result.scenario_run.step_runs[0]
    assert step_run.final_stage is ScenarioStepStage.incomplete
    assert step_run.stage_history == (
        ScenarioStepStage.started,
        ScenarioStepStage.observed,
        ScenarioStepStage.understood,
        ScenarioStepStage.incomplete,
    )
    assert step_run.matched_candidate_ids == ()
    assert step_run.verification_result is None


def test_scenario_loop_marks_failed_verification_path() -> None:
    snapshot = _scored_snapshot()
    exposure_result = ObserveOnlyCandidateExposer().expose(
        snapshot,
        options=CandidateExposureOptions(
            candidate_classes=(SemanticCandidateClass.button_like,),
            minimum_score=0.9,
            limit=5,
            include_only_visible=True,
        ),
    )
    assert exposure_result.success is True
    assert exposure_result.exposure_view is not None
    candidate_id = exposure_result.exposure_view.candidates[0].candidate_id
    step = _step_for_candidate(candidate_id)
    failing_step = replace(
        step,
        expected_outcome=SemanticTransitionExpectation(
            summary="The candidate should disappear, which is not true.",
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
        scenario_id="failed-verify",
        title="Failed Verify",
        summary="Verification should fail while remaining non-executing.",
        steps=(failing_step,),
    )

    result = _runner(_capture_result(_payload())).run(scenario)

    assert result.success is True
    assert result.scenario_run is not None
    assert result.scenario_run.status is ScenarioRunStatus.failed
    step_run = result.scenario_run.step_runs[0]
    assert step_run.final_stage is ScenarioStepStage.failed
    assert step_run.stage_history == (
        ScenarioStepStage.started,
        ScenarioStepStage.observed,
        ScenarioStepStage.understood,
        ScenarioStepStage.failed,
    )
    assert step_run.verification_result is not None
    assert step_run.verification_result.success is False


def test_scenario_loop_result_metadata_is_consistent() -> None:
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
    candidate_id = exposure_result.exposure_view.candidates[0].candidate_id
    scenario = ScenarioDefinition(
        scenario_id="metadata-scenario",
        title="Metadata Scenario",
        summary="Scenario metadata should stay stable.",
        steps=(_step_for_candidate(candidate_id),),
    )

    result = _runner(_capture_result(_payload())).run(scenario)

    assert result.success is True
    assert result.scenario_run is not None
    scenario_run = result.scenario_run
    assert scenario_run.metadata["scenario_runner_name"] == "ObserveUnderstandVerifyScenarioRunner"
    assert scenario_run.metadata["step_ids"] == ("confirm-step",)
    assert scenario_run.metadata["verified_step_ids"] == ("confirm-step",)
    assert scenario_run.metadata["dry_run_only_step_ids"] == ("confirm-step",)
    assert scenario_run.current_snapshot is not None
    assert scenario_run.metadata["current_snapshot_id"] == scenario_run.current_snapshot.snapshot_id
    step_run = scenario_run.step_runs[0]
    assert step_run.metadata["final_stage"] == "verified"
    assert step_run.metadata["execution_eligibility"] == "dry_run_only"
    assert step_run.metadata["matched_candidate_ids"] == (candidate_id,)


def test_scenario_loop_preserves_non_executing_semantics() -> None:
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
    scenario = ScenarioDefinition(
        scenario_id="non-executing",
        title="Non Executing",
        summary="Scenario loop must never attempt live execution in Phase 6B.",
        steps=(_step_for_candidate(exposure_result.exposure_view.candidates[0].candidate_id),),
    )

    result = _runner(_capture_result(_payload())).run(scenario)

    assert result.success is True
    assert result.scenario_run is not None
    assert result.scenario_run.observe_only is True
    assert result.scenario_run.non_executing is True
    assert result.scenario_run.live_execution_attempted is False
    assert result.scenario_run.metadata["observe_only"] is True
    assert result.scenario_run.metadata["non_executing"] is True
    for step_run in result.scenario_run.step_runs:
        assert step_run.observe_only is True
        assert step_run.non_executing is True
        assert step_run.live_execution_attempted is False
        assert step_run.metadata["observe_only"] is True
        assert step_run.metadata["non_executing"] is True


def test_scenario_loop_does_not_propagate_unhandled_exceptions() -> None:
    scenario = ScenarioDefinition(
        scenario_id="exploding-loop",
        title="Exploding Loop",
        summary="Unexpected exceptions should stay structured.",
        steps=(_step_for_candidate("placeholder-candidate"),),
    )

    result = _ExplodingScenarioRunner(
        capture_provider=_StaticCaptureProvider(_capture_result(_payload())),
        text_adapter=_text_adapter(),
    ).run(scenario)

    assert result.success is False
    assert result.error_code == "scenario_loop_exception"
    assert result.error_message == "scenario runner exploded"
