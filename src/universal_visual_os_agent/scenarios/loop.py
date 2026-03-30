"""Observe-understand-verify scenario loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from universal_visual_os_agent.perception.interfaces import CaptureProvider
from universal_visual_os_agent.scenarios.definition import (
    SafetyFirstScenarioDefinitionBuilder,
)
from universal_visual_os_agent.scenarios.models import (
    ScenarioDefinition,
    ScenarioExecutionEligibility,
    ScenarioRun,
    ScenarioRunResult,
    ScenarioRunStatus,
    ScenarioStepDefinition,
    ScenarioStepRun,
    ScenarioStepStage,
)
from universal_visual_os_agent.scenarios.state_machine import (
    InstrumentedScenarioStateMachine,
    ScenarioFlowState,
    ScenarioStateMachineTrace,
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
    SemanticStateSnapshot,
)
from universal_visual_os_agent.semantics.interfaces import (
    CandidateExposer,
    CandidateGenerator,
    CandidateScorer,
    LayoutRegionAnalyzer,
    SemanticExtractionInputAdapter,
    SemanticLayoutEnricher,
    SemanticStateBuilder,
    TextExtractionAdapter,
)
from universal_visual_os_agent.verification import GoalOrientedSemanticVerifier
from universal_visual_os_agent.verification.interfaces import SemanticTransitionVerifier
from universal_visual_os_agent.verification.models import (
    SemanticStateTransition,
    VerificationStatus,
)


@dataclass(slots=True, frozen=True, kw_only=True)
class _UnderstandingResult:
    success: bool
    reason: str
    signal_status: str
    snapshot: SemanticStateSnapshot | None = None
    matched_candidate_ids: tuple[str, ...] = ()
    exposure_view: object | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    @property
    def understood(self) -> bool:
        return self.exposure_view is not None


class ObserveUnderstandVerifyScenarioRunner:
    """Run scenario steps through capture, semantic understanding, and verification only."""

    runner_name = "ObserveUnderstandVerifyScenarioRunner"

    def __init__(
        self,
        *,
        capture_provider: CaptureProvider,
        scenario_definition_builder: SafetyFirstScenarioDefinitionBuilder | None = None,
        semantic_input_adapter: SemanticExtractionInputAdapter | None = None,
        state_builder: SemanticStateBuilder | None = None,
        text_adapter: TextExtractionAdapter | None = None,
        layout_analyzer: LayoutRegionAnalyzer | None = None,
        semantic_layout_enricher: SemanticLayoutEnricher | None = None,
        candidate_generator: CandidateGenerator | None = None,
        candidate_scorer: CandidateScorer | None = None,
        candidate_exposer: CandidateExposer | None = None,
        verifier: SemanticTransitionVerifier | None = None,
    ) -> None:
        self._capture_provider = capture_provider
        self._scenario_definition_builder = (
            SafetyFirstScenarioDefinitionBuilder()
            if scenario_definition_builder is None
            else scenario_definition_builder
        )
        self._semantic_input_adapter = (
            FullDesktopCaptureSemanticInputAdapter()
            if semantic_input_adapter is None
            else semantic_input_adapter
        )
        self._state_builder = (
            PreparedSemanticStateBuilder() if state_builder is None else state_builder
        )
        self._text_adapter = (
            PreparedSemanticTextExtractionAdapter()
            if text_adapter is None
            else text_adapter
        )
        self._layout_analyzer = (
            GeometricLayoutRegionAnalyzer()
            if layout_analyzer is None
            else layout_analyzer
        )
        self._semantic_layout_enricher = (
            OcrAwareSemanticLayoutEnricher()
            if semantic_layout_enricher is None
            else semantic_layout_enricher
        )
        self._candidate_generator = (
            ObserveOnlyCandidateGenerator()
            if candidate_generator is None
            else candidate_generator
        )
        self._candidate_scorer = (
            ObserveOnlyCandidateScorer()
            if candidate_scorer is None
            else candidate_scorer
        )
        self._candidate_exposer = (
            ObserveOnlyCandidateExposer()
            if candidate_exposer is None
            else candidate_exposer
        )
        self._verifier = (
            GoalOrientedSemanticVerifier() if verifier is None else verifier
        )
        self._previous_snapshot: SemanticStateSnapshot | None = None

    def run(
        self,
        scenario: ScenarioDefinition,
        *,
        previous_snapshot: SemanticStateSnapshot | None = None,
    ) -> ScenarioRunResult:
        definition_result = self._scenario_definition_builder.build(scenario)
        if not definition_result.success or definition_result.scenario_definition is None:
            return ScenarioRunResult.failure(
                runner_name=self.runner_name,
                error_code=definition_result.error_code or "scenario_definition_unavailable",
                error_message=definition_result.error_message
                or "Scenario definition validation did not succeed.",
                details={
                    "definition_builder_name": getattr(
                        self._scenario_definition_builder,
                        "builder_name",
                        type(self._scenario_definition_builder).__name__,
                    ),
                },
            )

        normalized_scenario = definition_result.scenario_definition
        initial_snapshot = previous_snapshot if previous_snapshot is not None else self._previous_snapshot
        active_previous_snapshot = initial_snapshot
        latest_snapshot = active_previous_snapshot

        try:
            step_runs: list[ScenarioStepRun] = []
            for step in normalized_scenario.steps:
                step_run = self._run_step(step, before_snapshot=active_previous_snapshot)
                step_runs.append(step_run)
                if step_run.observed_snapshot is not None:
                    active_previous_snapshot = step_run.observed_snapshot
                    latest_snapshot = step_run.observed_snapshot
        except Exception as exc:  # noqa: BLE001 - scenario loop must remain failure-safe
            return ScenarioRunResult.failure(
                runner_name=self.runner_name,
                error_code="scenario_loop_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        if latest_snapshot is not None:
            self._previous_snapshot = latest_snapshot

        scenario_run = ScenarioRun(
            scenario_id=normalized_scenario.scenario_id,
            title=normalized_scenario.title,
            summary=normalized_scenario.summary,
            status=_scenario_run_status(normalized_scenario=normalized_scenario, step_runs=tuple(step_runs)),
            step_runs=tuple(step_runs),
            verified_step_count=sum(
                step_run.final_stage is ScenarioStepStage.verified
                for step_run in step_runs
            ),
            incomplete_step_count=sum(
                step_run.final_stage is ScenarioStepStage.incomplete
                for step_run in step_runs
            ),
            failed_step_count=sum(
                step_run.final_stage is ScenarioStepStage.failed
                for step_run in step_runs
            ),
            current_snapshot=latest_snapshot,
            initial_snapshot=initial_snapshot,
            signal_status=_run_signal_status(tuple(step_runs)),
            observe_only=True,
            non_executing=True,
            live_execution_attempted=False,
            metadata={
                "scenario_runner_name": self.runner_name,
                "observe_only": True,
                "non_executing": True,
                "live_execution_attempted": False,
                "scenario_definition_status": normalized_scenario.status.value,
                "scenario_definition_view_signal_status": (
                    None
                    if definition_result.definition_view is None
                    else definition_result.definition_view.signal_status
                ),
                "initial_snapshot_id": None if initial_snapshot is None else initial_snapshot.snapshot_id,
                "current_snapshot_id": None if latest_snapshot is None else latest_snapshot.snapshot_id,
                "step_ids": tuple(step.step_id for step in normalized_scenario.steps),
                "step_final_stages": tuple(
                    (step_run.step_id, step_run.final_stage.value)
                    for step_run in step_runs
                ),
                "verified_step_ids": tuple(
                    step_run.step_id
                    for step_run in step_runs
                    if step_run.final_stage is ScenarioStepStage.verified
                ),
                "incomplete_step_ids": tuple(
                    step_run.step_id
                    for step_run in step_runs
                    if step_run.final_stage is ScenarioStepStage.incomplete
                ),
                "failed_step_ids": tuple(
                    step_run.step_id
                    for step_run in step_runs
                    if step_run.final_stage is ScenarioStepStage.failed
                ),
                "dry_run_only_step_ids": tuple(
                    step.step_id
                    for step in normalized_scenario.steps
                    if step.execution_eligibility is ScenarioExecutionEligibility.dry_run_only
                ),
                "real_click_eligible_step_ids": tuple(
                    step.step_id
                    for step in normalized_scenario.steps
                    if step.execution_eligibility
                    is ScenarioExecutionEligibility.real_click_eligible
                ),
                "state_transition_count": sum(
                    0
                    if step_run.state_machine_trace is None
                    else len(step_run.state_machine_trace.transitions)
                    for step_run in step_runs
                ),
                "step_terminal_states": tuple(
                    (
                        step_run.step_id,
                        None
                        if step_run.state_machine_trace is None
                        or step_run.state_machine_trace.current_state is None
                        else step_run.state_machine_trace.current_state.value,
                    )
                    for step_run in step_runs
                ),
                "blocked_step_ids": tuple(
                    step_run.step_id
                    for step_run in step_runs
                    if step_run.state_machine_trace is not None
                    and step_run.state_machine_trace.current_state is ScenarioFlowState.blocked
                ),
                "recovery_needed_step_ids": tuple(
                    step_run.step_id
                    for step_run in step_runs
                    if step_run.state_machine_trace is not None
                    and step_run.state_machine_trace.current_state
                    is ScenarioFlowState.recovery_needed
                ),
            },
        )
        return ScenarioRunResult.ok(
            runner_name=self.runner_name,
            scenario_definition=normalized_scenario,
            scenario_run=scenario_run,
            details={
                "status": scenario_run.status.value,
                "step_count": len(step_runs),
                "signal_status": scenario_run.signal_status,
            },
        )

    def _run_step(
        self,
        step: ScenarioStepDefinition,
        *,
        before_snapshot: SemanticStateSnapshot | None,
    ) -> ScenarioStepRun:
        stage_history = [ScenarioStepStage.started]
        state_machine = InstrumentedScenarioStateMachine(
            trace_id=f"{self.runner_name}:{step.step_id}"
        )
        if step.status is not None and step.status.value == "invalid":
            state_machine.transition(
                ScenarioFlowState.aborted,
                block_reason=step.status_reason or "Scenario step definition was invalid.",
                next_expected_signal=None,
                metadata={"definition_status": step.status.value},
            )
            return self._step_run(
                step,
                final_stage=ScenarioStepStage.failed,
                stage_history=tuple(stage_history + [ScenarioStepStage.failed]),
                reason=step.status_reason or "Scenario step definition was invalid.",
                signal_status="partial",
                state_machine_trace=state_machine.trace(
                    signal_status="partial",
                    metadata={"definition_status": step.status.value},
                ),
                metadata={"definition_status": step.status.value},
            )
        if step.status is not None and step.status.value == "incomplete":
            state_machine.transition(
                ScenarioFlowState.recovery_needed,
                block_reason=step.status_reason or "Scenario step definition was incomplete.",
                recovery_hint="Complete the missing scenario-step definition fields before retrying.",
                next_expected_signal="scenario_definition",
                metadata={"definition_status": step.status.value},
            )
            return self._step_run(
                step,
                final_stage=ScenarioStepStage.incomplete,
                stage_history=tuple(stage_history + [ScenarioStepStage.incomplete]),
                reason=step.status_reason or "Scenario step definition was incomplete.",
                signal_status="partial",
                state_machine_trace=state_machine.trace(
                    signal_status="partial",
                    metadata={"definition_status": step.status.value},
                ),
                metadata={"definition_status": step.status.value},
            )

        capture_result = self._capture_provider.capture_frame()
        if not capture_result.success or capture_result.frame is None:
            state_machine.transition(
                ScenarioFlowState.recovery_needed,
                block_reason=capture_result.error_message
                or "Capture did not provide a usable frame.",
                recovery_hint="Retry capture when a readable frame is available.",
                next_expected_signal="capture_frame",
                metadata={
                    "capture_provider_name": capture_result.provider_name,
                    "capture_error_code": capture_result.error_code,
                },
            )
            return self._step_run(
                step,
                final_stage=ScenarioStepStage.incomplete,
                stage_history=tuple(stage_history + [ScenarioStepStage.incomplete]),
                reason=capture_result.error_message or "Capture did not provide a usable frame.",
                signal_status="partial",
                state_machine_trace=state_machine.trace(
                    signal_status="partial",
                    metadata={
                        "capture_provider_name": capture_result.provider_name,
                        "capture_error_code": capture_result.error_code,
                    },
                ),
                metadata={
                    "capture_provider_name": capture_result.provider_name,
                    "capture_error_code": capture_result.error_code,
                },
            )
        stage_history.append(ScenarioStepStage.observed)
        state_machine.transition(
            ScenarioFlowState.observed,
            next_expected_signal="semantic_understanding",
            metadata={
                "capture_provider_name": capture_result.provider_name,
                "frame_id": None if capture_result.frame is None else capture_result.frame.frame_id,
            },
        )

        understanding = self._understand_step(capture_result, step)
        if understanding.understood:
            stage_history.append(ScenarioStepStage.understood)
            state_machine.transition(
                ScenarioFlowState.understood,
                confidence=_understanding_confidence(
                    understanding.exposure_view,
                    understanding.matched_candidate_ids,
                ),
                next_expected_signal="verification_result",
                metadata={
                    "matched_candidate_ids": understanding.matched_candidate_ids,
                    "snapshot_id": (
                        None if understanding.snapshot is None else understanding.snapshot.snapshot_id
                    ),
                },
            )
        if not understanding.success:
            stage_history.append(ScenarioStepStage.incomplete)
            state_machine.transition(
                ScenarioFlowState.recovery_needed,
                confidence=_understanding_confidence(
                    understanding.exposure_view,
                    understanding.matched_candidate_ids,
                ),
                block_reason=understanding.reason,
                recovery_hint=_recovery_hint_for_understanding(understanding.details),
                next_expected_signal=_next_expected_signal_for_understanding(understanding.details),
                metadata=understanding.details,
            )
            step_signal_status = understanding.signal_status
            return self._step_run(
                step,
                final_stage=ScenarioStepStage.incomplete,
                stage_history=tuple(stage_history),
                reason=understanding.reason,
                observed_snapshot=understanding.snapshot,
                exposure_view=understanding.exposure_view,
                matched_candidate_ids=understanding.matched_candidate_ids,
                signal_status=step_signal_status,
                state_machine_trace=state_machine.trace(
                    signal_status=step_signal_status,
                    metadata=understanding.details,
                ),
                metadata=understanding.details,
            )

        transition_before = (
            before_snapshot
            if before_snapshot is not None
            else _synthetic_before_snapshot(understanding.snapshot)
        )
        verification_result = self._verifier.verify(
            step.expected_outcome,
            SemanticStateTransition(before=transition_before, after=understanding.snapshot),
        )
        if verification_result.status is VerificationStatus.satisfied:
            stage_history.append(ScenarioStepStage.verified)
            step_signal_status = understanding.signal_status
            state_machine.transition(
                ScenarioFlowState.verification_passed,
                confidence=_verification_confidence(
                    understanding.exposure_view,
                    understanding.matched_candidate_ids,
                ),
                next_expected_signal="scenario_step_complete",
                metadata={"verification_status": verification_result.status.value},
            )
            return self._step_run(
                step,
                final_stage=ScenarioStepStage.verified,
                stage_history=tuple(stage_history),
                reason=verification_result.summary,
                observed_snapshot=understanding.snapshot,
                exposure_view=understanding.exposure_view,
                verification_result=verification_result,
                matched_candidate_ids=understanding.matched_candidate_ids,
                signal_status=step_signal_status,
                state_machine_trace=state_machine.trace(
                    signal_status=step_signal_status,
                    metadata={"verification_status": verification_result.status.value},
                ),
                metadata={
                    **dict(understanding.details),
                    "verification_before_snapshot_id": transition_before.snapshot_id,
                    "synthetic_before_snapshot": before_snapshot is None,
                    "verification_status": verification_result.status.value,
                },
            )
        if verification_result.status is VerificationStatus.unknown:
            stage_history.append(ScenarioStepStage.incomplete)
            state_machine.transition(
                ScenarioFlowState.recovery_needed,
                confidence=_verification_confidence(
                    understanding.exposure_view,
                    understanding.matched_candidate_ids,
                ),
                block_reason=verification_result.summary,
                recovery_hint="Repeat observation with more complete semantic inputs before retrying verification.",
                next_expected_signal="capture_frame",
                metadata={"verification_status": verification_result.status.value},
            )
            return self._step_run(
                step,
                final_stage=ScenarioStepStage.incomplete,
                stage_history=tuple(stage_history),
                reason=verification_result.summary,
                observed_snapshot=understanding.snapshot,
                exposure_view=understanding.exposure_view,
                verification_result=verification_result,
                matched_candidate_ids=understanding.matched_candidate_ids,
                signal_status="partial",
                state_machine_trace=state_machine.trace(
                    signal_status="partial",
                    metadata={"verification_status": verification_result.status.value},
                ),
                metadata={
                    **dict(understanding.details),
                    "verification_before_snapshot_id": transition_before.snapshot_id,
                    "synthetic_before_snapshot": before_snapshot is None,
                    "verification_status": verification_result.status.value,
                },
            )

        stage_history.append(ScenarioStepStage.failed)
        step_signal_status = understanding.signal_status
        state_machine.transition(
            ScenarioFlowState.verification_failed,
            confidence=_verification_confidence(
                understanding.exposure_view,
                understanding.matched_candidate_ids,
            ),
            block_reason=verification_result.summary,
            recovery_hint="Inspect the semantic delta and expected outcome before retrying the step.",
            next_expected_signal="verification_delta",
            metadata={"verification_status": verification_result.status.value},
        )
        return self._step_run(
            step,
            final_stage=ScenarioStepStage.failed,
            stage_history=tuple(stage_history),
            reason=verification_result.summary,
            observed_snapshot=understanding.snapshot,
            exposure_view=understanding.exposure_view,
            verification_result=verification_result,
            matched_candidate_ids=understanding.matched_candidate_ids,
            signal_status=step_signal_status,
            state_machine_trace=state_machine.trace(
                signal_status=step_signal_status,
                metadata={"verification_status": verification_result.status.value},
            ),
            metadata={
                **dict(understanding.details),
                "verification_before_snapshot_id": transition_before.snapshot_id,
                "synthetic_before_snapshot": before_snapshot is None,
                "verification_status": verification_result.status.value,
            },
        )

    def _understand_step(
        self,
        capture_result,
        step: ScenarioStepDefinition,
    ) -> _UnderstandingResult:
        preparation_result = self._semantic_input_adapter.prepare(capture_result)
        if not preparation_result.success:
            return _UnderstandingResult(
                success=False,
                reason=preparation_result.error_message or "Semantic input preparation failed.",
                signal_status="partial",
                details={
                    "understanding_stage": "prepare",
                    "error_code": preparation_result.error_code,
                },
            )

        state_result = self._state_builder.build(preparation_result)
        if not state_result.success or state_result.snapshot is None:
            return _UnderstandingResult(
                success=False,
                reason=state_result.error_message or "Semantic state build failed.",
                signal_status="partial",
                details={
                    "understanding_stage": "state_build",
                    "error_code": state_result.error_code,
                },
            )

        text_result = self._text_adapter.extract(preparation_result, state_result)
        if not text_result.success or text_result.enriched_snapshot is None:
            return _UnderstandingResult(
                success=False,
                reason=text_result.error_message or "Text extraction failed.",
                signal_status="partial",
                snapshot=state_result.snapshot,
                details={
                    "understanding_stage": "text_extraction",
                    "error_code": text_result.error_code,
                },
            )

        layout_result = self._layout_analyzer.analyze(text_result.enriched_snapshot)
        if not layout_result.success or layout_result.snapshot is None:
            return _UnderstandingResult(
                success=False,
                reason=layout_result.error_message or "Layout analysis failed.",
                signal_status="partial",
                snapshot=text_result.enriched_snapshot,
                details={
                    "understanding_stage": "layout_analysis",
                    "error_code": layout_result.error_code,
                },
            )

        semantic_layout_result = self._semantic_layout_enricher.enrich(layout_result.snapshot)
        if not semantic_layout_result.success or semantic_layout_result.snapshot is None:
            return _UnderstandingResult(
                success=False,
                reason=semantic_layout_result.error_message or "Semantic layout enrichment failed.",
                signal_status="partial",
                snapshot=layout_result.snapshot,
                details={
                    "understanding_stage": "semantic_layout_enrichment",
                    "error_code": semantic_layout_result.error_code,
                },
            )

        generation_result = self._candidate_generator.generate(semantic_layout_result.snapshot)
        if not generation_result.success or generation_result.snapshot is None:
            return _UnderstandingResult(
                success=False,
                reason=generation_result.error_message or "Candidate generation failed.",
                signal_status="partial",
                snapshot=semantic_layout_result.snapshot,
                details={
                    "understanding_stage": "candidate_generation",
                    "error_code": generation_result.error_code,
                },
            )

        scoring_result = self._candidate_scorer.score(generation_result.snapshot)
        if not scoring_result.success or scoring_result.snapshot is None:
            return _UnderstandingResult(
                success=False,
                reason=scoring_result.error_message or "Candidate scoring failed.",
                signal_status="partial",
                snapshot=generation_result.snapshot,
                details={
                    "understanding_stage": "candidate_scoring",
                    "error_code": scoring_result.error_code,
                },
            )

        exposure_result = self._candidate_exposer.expose(
            scoring_result.snapshot,
            options=_exposure_options_for_step(step),
        )
        if not exposure_result.success or exposure_result.exposure_view is None:
            return _UnderstandingResult(
                success=False,
                reason=exposure_result.error_message or "Candidate exposure failed.",
                signal_status="partial",
                snapshot=scoring_result.snapshot,
                details={
                    "understanding_stage": "candidate_exposure",
                    "error_code": exposure_result.error_code,
                },
            )

        matched_candidate_ids = _matched_candidate_ids(step, exposure_result.exposure_view)
        if not matched_candidate_ids:
            return _UnderstandingResult(
                success=False,
                reason="No exposed candidates matched the scenario step constraints.",
                signal_status="partial",
                snapshot=scoring_result.snapshot,
                exposure_view=exposure_result.exposure_view,
                matched_candidate_ids=(),
                details={
                    "understanding_stage": "candidate_matching",
                    "allowed_candidate_ids": step.candidate_constraint.allowed_candidate_ids,
                    "candidate_classes": tuple(
                        candidate_class.value
                        for candidate_class in step.candidate_constraint.candidate_classes
                    ),
                    "require_complete": step.candidate_constraint.require_complete,
                },
            )

        return _UnderstandingResult(
            success=True,
            reason="Scenario step was understood through the semantic candidate exposure view.",
            signal_status=exposure_result.exposure_view.signal_status,
            snapshot=scoring_result.snapshot,
            exposure_view=exposure_result.exposure_view,
            matched_candidate_ids=matched_candidate_ids,
            details={
                "understanding_stage": "candidate_matching",
                "capture_provider_name": capture_result.provider_name,
                "frame_id": None if capture_result.frame is None else capture_result.frame.frame_id,
                "snapshot_id": scoring_result.snapshot.snapshot_id,
                "matched_candidate_ids": matched_candidate_ids,
                "exposed_candidate_count": exposure_result.exposure_view.exposed_candidate_count,
                "filtered_out_candidate_ids": exposure_result.exposure_view.filtered_out_candidate_ids,
                "execution_eligibility": step.execution_eligibility.value,
                "dry_run_only_step": (
                    step.execution_eligibility is ScenarioExecutionEligibility.dry_run_only
                ),
            },
        )

    def _step_run(
        self,
        step: ScenarioStepDefinition,
        *,
        final_stage: ScenarioStepStage,
        stage_history: tuple[ScenarioStepStage, ...],
        reason: str,
        observed_snapshot: SemanticStateSnapshot | None = None,
        exposure_view=None,
        verification_result=None,
        matched_candidate_ids: tuple[str, ...] = (),
        signal_status: str = "absent",
        state_machine_trace: ScenarioStateMachineTrace | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> ScenarioStepRun:
        return ScenarioStepRun(
            step_id=step.step_id,
            summary=step.summary,
            execution_eligibility=step.execution_eligibility,
            final_stage=final_stage,
            stage_history=stage_history,
            reason=reason,
            observed_snapshot=observed_snapshot,
            exposure_view=exposure_view,
            verification_result=verification_result,
            matched_candidate_ids=matched_candidate_ids,
            signal_status=signal_status,
            state_machine_trace=state_machine_trace,
            observe_only=True,
            non_executing=True,
            live_execution_attempted=False,
            metadata={
                **dict(step.metadata),
                **({} if metadata is None else dict(metadata)),
                **_state_machine_metadata(state_machine_trace),
                "observe_only": True,
                "non_executing": True,
                "live_execution_attempted": False,
                "final_stage": final_stage.value,
                "stage_history": tuple(stage.value for stage in stage_history),
                "execution_eligibility": step.execution_eligibility.value,
                "matched_candidate_ids": matched_candidate_ids,
                "observed_snapshot_id": (
                    None if observed_snapshot is None else observed_snapshot.snapshot_id
                ),
            },
        )


def _exposure_options_for_step(step: ScenarioStepDefinition) -> CandidateExposureOptions:
    return CandidateExposureOptions(
        minimum_score=step.candidate_constraint.minimum_score,
        candidate_classes=step.candidate_constraint.candidate_classes,
        limit=step.candidate_constraint.maximum_candidate_rank,
        include_only_visible=step.candidate_constraint.require_visible,
    )


def _matched_candidate_ids(
    step: ScenarioStepDefinition,
    exposure_view,
) -> tuple[str, ...]:
    allowed_candidate_ids = set(step.candidate_constraint.allowed_candidate_ids)
    matched_ids: list[str] = []
    for candidate in exposure_view.candidates:
        if allowed_candidate_ids and candidate.candidate_id not in allowed_candidate_ids:
            continue
        if (
            step.candidate_constraint.require_complete
            and candidate.completeness_status != "available"
        ):
            continue
        matched_ids.append(candidate.candidate_id)
    return tuple(matched_ids)


def _scenario_run_status(
    *,
    normalized_scenario: ScenarioDefinition,
    step_runs: tuple[ScenarioStepRun, ...],
) -> ScenarioRunStatus:
    if normalized_scenario.status.value == "invalid":
        return ScenarioRunStatus.failed
    if any(step_run.final_stage is ScenarioStepStage.failed for step_run in step_runs):
        return ScenarioRunStatus.failed
    if not step_runs:
        return ScenarioRunStatus.incomplete
    if any(step_run.final_stage is ScenarioStepStage.incomplete for step_run in step_runs):
        return ScenarioRunStatus.incomplete
    if normalized_scenario.status.value == "incomplete":
        return ScenarioRunStatus.incomplete
    return ScenarioRunStatus.completed


def _run_signal_status(step_runs: tuple[ScenarioStepRun, ...]) -> str:
    if not step_runs:
        return "absent"
    if all(step_run.signal_status == "available" for step_run in step_runs):
        return "available"
    return "partial"


def _synthetic_before_snapshot(
    after_snapshot: SemanticStateSnapshot,
) -> SemanticStateSnapshot:
    return SemanticStateSnapshot(
        observed_at=after_snapshot.observed_at,
        metadata={
            "observe_only": True,
            "analysis_only": True,
            "synthetic_before_snapshot": True,
            "source_snapshot_id": after_snapshot.snapshot_id,
        },
    )


def _state_machine_metadata(
    state_machine_trace: ScenarioStateMachineTrace | None,
) -> Mapping[str, object]:
    if state_machine_trace is None:
        return {}
    return {
        "state_machine_trace_id": state_machine_trace.trace_id,
        "state_machine_current_state": (
            None
            if state_machine_trace.current_state is None
            else state_machine_trace.current_state.value
        ),
        "state_machine_transition_count": len(state_machine_trace.transitions),
        "state_machine_state_history": tuple(
            state.value for state in state_machine_trace.state_history
        ),
        "state_machine_transition_ids": tuple(
            transition.transition_id for transition in state_machine_trace.transitions
        ),
    }


def _understanding_confidence(
    exposure_view,
    matched_candidate_ids: tuple[str, ...],
) -> float | None:
    if exposure_view is None:
        return None
    if matched_candidate_ids:
        for candidate in exposure_view.candidates:
            if candidate.candidate_id == matched_candidate_ids[0]:
                return candidate.score
    scores = tuple(
        candidate.score
        for candidate in exposure_view.candidates
        if candidate.score is not None
    )
    if not scores:
        return None
    return max(scores)


def _verification_confidence(
    exposure_view,
    matched_candidate_ids: tuple[str, ...],
) -> float | None:
    return _understanding_confidence(exposure_view, matched_candidate_ids)


def _recovery_hint_for_understanding(details: Mapping[str, object]) -> str:
    understanding_stage = details.get("understanding_stage")
    if understanding_stage == "candidate_matching":
        return "Loosen candidate constraints or re-observe the UI so a matching candidate can be exposed."
    if understanding_stage == "candidate_exposure":
        return "Retry candidate exposure after a more complete scored snapshot is available."
    if understanding_stage == "candidate_scoring":
        return "Retry candidate scoring with complete OCR, layout, and region metadata."
    if understanding_stage == "candidate_generation":
        return "Retry candidate generation after semantic layout enrichment succeeds."
    if understanding_stage == "semantic_layout_enrichment":
        return "Retry semantic layout enrichment after layout analysis completes."
    if understanding_stage == "layout_analysis":
        return "Retry layout analysis with a valid enriched semantic snapshot."
    if understanding_stage == "text_extraction":
        return "Retry OCR extraction when text regions are available."
    if understanding_stage == "state_build":
        return "Retry semantic state building with a prepared capture input."
    return "Repeat observation with more complete semantic inputs before retrying the step."


def _next_expected_signal_for_understanding(details: Mapping[str, object]) -> str:
    understanding_stage = details.get("understanding_stage")
    if isinstance(understanding_stage, str) and understanding_stage:
        return understanding_stage
    return "semantic_understanding"
