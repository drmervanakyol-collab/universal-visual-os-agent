"""Safety-first observe-act-verify scenario loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from universal_visual_os_agent.actions import (
    ActionIntent,
    ActionIntentScaffoldView,
    DryRunActionDisposition,
    DryRunActionEngine,
    DryRunActionEvaluation,
    ObserveOnlyActionIntentScaffolder,
    ObserveOnlyDryRunActionEngine,
    SafeClickExecution,
    SafeClickExecutor,
    SafeClickPrototypeExecutor,
    SafeClickPrototypeStatus,
)
from universal_visual_os_agent.config import AgentMode, RunConfig
from universal_visual_os_agent.geometry.models import VirtualDesktopMetrics
from universal_visual_os_agent.perception.interfaces import CaptureProvider
from universal_visual_os_agent.policy import PolicyEvaluationContext, RuleBasedPolicyEngine
from universal_visual_os_agent.scenarios.definition import SafetyFirstScenarioDefinitionBuilder
from universal_visual_os_agent.scenarios.loop import (
    ObserveUnderstandVerifyScenarioRunner,
    _next_expected_signal_for_understanding,
    _recovery_hint_for_understanding,
    _state_machine_metadata,
    _synthetic_before_snapshot,
    _understanding_confidence,
    _verification_confidence,
)
from universal_visual_os_agent.scenarios.models import (
    ScenarioActionDisposition,
    ScenarioActionRun,
    ScenarioActionRunResult,
    ScenarioActionStepRun,
    ScenarioActionStepStage,
    ScenarioDefinition,
    ScenarioExecutionEligibility,
    ScenarioRunStatus,
    ScenarioStepDefinition,
)
from universal_visual_os_agent.scenarios.state_machine import (
    InstrumentedScenarioStateMachine,
    ScenarioFlowState,
    ScenarioStateMachineTrace,
)
from universal_visual_os_agent.semantics import SemanticStateSnapshot
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
from universal_visual_os_agent.verification.interfaces import SemanticTransitionVerifier
from universal_visual_os_agent.verification.models import (
    SemanticStateTransition,
    VerificationResult,
    VerificationStatus,
)


@dataclass(slots=True, frozen=True, kw_only=True)
class _ActionResolution:
    proceed_to_post_action: bool
    action_disposition: ScenarioActionDisposition
    reason: str
    signal_status: str
    stage_updates: tuple[ScenarioActionStepStage, ...] = ()
    selected_candidate_id: str | None = None
    selected_intent: ActionIntent | None = None
    scaffold_view: ActionIntentScaffoldView | None = None
    dry_run_evaluation: DryRunActionEvaluation | None = None
    safe_click_execution: SafeClickExecution | None = None
    final_stage: ScenarioActionStepStage | None = None
    details: Mapping[str, object] = field(default_factory=dict)


class ObserveActVerifyScenarioRunner(ObserveUnderstandVerifyScenarioRunner):
    """Run scenario steps through observe, act, and verify using existing safe components."""

    runner_name = "ObserveActVerifyScenarioRunner"

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
        action_intent_scaffolder: ObserveOnlyActionIntentScaffolder | None = None,
        dry_run_action_engine: DryRunActionEngine | None = None,
        safe_click_executor: SafeClickExecutor | None = None,
    ) -> None:
        super().__init__(
            capture_provider=capture_provider,
            scenario_definition_builder=scenario_definition_builder,
            semantic_input_adapter=semantic_input_adapter,
            state_builder=state_builder,
            text_adapter=text_adapter,
            layout_analyzer=layout_analyzer,
            semantic_layout_enricher=semantic_layout_enricher,
            candidate_generator=candidate_generator,
            candidate_scorer=candidate_scorer,
            candidate_exposer=candidate_exposer,
            verifier=verifier,
        )
        self._action_intent_scaffolder = (
            ObserveOnlyActionIntentScaffolder()
            if action_intent_scaffolder is None
            else action_intent_scaffolder
        )
        self._dry_run_action_engine = (
            ObserveOnlyDryRunActionEngine()
            if dry_run_action_engine is None
            else dry_run_action_engine
        )
        self._safe_click_executor = (
            SafeClickPrototypeExecutor(policy_engine=RuleBasedPolicyEngine())
            if safe_click_executor is None
            else safe_click_executor
        )

    def run(
        self,
        scenario: ScenarioDefinition,
        *,
        previous_snapshot: SemanticStateSnapshot | None = None,
        config: RunConfig | None = None,
        metrics: VirtualDesktopMetrics | None = None,
        policy_context: PolicyEvaluationContext | None = None,
        execute: bool = False,
    ) -> ScenarioActionRunResult:
        active_config = config or RunConfig(mode=AgentMode.dry_run)
        definition_result = self._scenario_definition_builder.build(scenario)
        if not definition_result.success or definition_result.scenario_definition is None:
            return ScenarioActionRunResult.failure(
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
        initial_snapshot = (
            previous_snapshot if previous_snapshot is not None else self._previous_snapshot
        )
        active_previous_snapshot = initial_snapshot
        latest_snapshot = active_previous_snapshot

        try:
            step_runs: list[ScenarioActionStepRun] = []
            for step in normalized_scenario.steps:
                step_run = self._run_action_step(
                    step,
                    before_snapshot=active_previous_snapshot,
                    config=active_config,
                    metrics=metrics,
                    policy_context=policy_context,
                    execute=execute,
                )
                step_runs.append(step_run)
                latest_observed_snapshot = (
                    step_run.post_action_snapshot
                    if step_run.post_action_snapshot is not None
                    else step_run.pre_action_snapshot
                )
                if latest_observed_snapshot is not None:
                    active_previous_snapshot = latest_observed_snapshot
                    latest_snapshot = latest_observed_snapshot
        except Exception as exc:  # noqa: BLE001 - scenario action flow must remain failure-safe
            return ScenarioActionRunResult.failure(
                runner_name=self.runner_name,
                error_code="scenario_action_loop_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        if latest_snapshot is not None:
            self._previous_snapshot = latest_snapshot

        scenario_run = ScenarioActionRun(
            scenario_id=normalized_scenario.scenario_id,
            title=normalized_scenario.title,
            summary=normalized_scenario.summary,
            status=_scenario_action_run_status(
                normalized_scenario=normalized_scenario,
                step_runs=tuple(step_runs),
            ),
            step_runs=tuple(step_runs),
            verified_step_count=sum(
                step_run.final_stage is ScenarioActionStepStage.verified
                for step_run in step_runs
            ),
            incomplete_step_count=sum(
                step_run.final_stage is ScenarioActionStepStage.incomplete
                for step_run in step_runs
            ),
            failed_step_count=sum(
                step_run.final_stage is ScenarioActionStepStage.failed
                for step_run in step_runs
            ),
            dry_run_only_step_count=sum(
                step_run.action_disposition is ScenarioActionDisposition.dry_run_only
                for step_run in step_runs
            ),
            blocked_step_count=sum(
                step_run.action_disposition is ScenarioActionDisposition.blocked
                for step_run in step_runs
            ),
            real_click_eligible_step_count=sum(
                step_run.action_disposition
                is ScenarioActionDisposition.real_click_eligible
                for step_run in step_runs
            ),
            real_click_executed_step_count=sum(
                step_run.action_disposition
                is ScenarioActionDisposition.real_click_executed
                for step_run in step_runs
            ),
            action_incomplete_step_count=sum(
                step_run.action_disposition is ScenarioActionDisposition.incomplete
                for step_run in step_runs
            ),
            current_snapshot=latest_snapshot,
            initial_snapshot=initial_snapshot,
            signal_status=_action_run_signal_status(tuple(step_runs)),
            observe_only_inputs=True,
            safety_first=True,
            non_executing=not any(
                step_run.live_execution_attempted for step_run in step_runs
            ),
            live_execution_attempted=any(
                step_run.live_execution_attempted for step_run in step_runs
            ),
            metadata={
                "scenario_runner_name": self.runner_name,
                "observe_only_inputs": True,
                "safety_first": True,
                "non_executing": not any(
                    step_run.live_execution_attempted for step_run in step_runs
                ),
                "live_execution_attempted": any(
                    step_run.live_execution_attempted for step_run in step_runs
                ),
                "scenario_definition_status": normalized_scenario.status.value,
                "scenario_definition_view_signal_status": (
                    None
                    if definition_result.definition_view is None
                    else definition_result.definition_view.signal_status
                ),
                "initial_snapshot_id": (
                    None if initial_snapshot is None else initial_snapshot.snapshot_id
                ),
                "current_snapshot_id": (
                    None if latest_snapshot is None else latest_snapshot.snapshot_id
                ),
                "step_ids": tuple(step.step_id for step in normalized_scenario.steps),
                "step_final_stages": tuple(
                    (step_run.step_id, step_run.final_stage.value)
                    for step_run in step_runs
                ),
                "step_action_dispositions": tuple(
                    (step_run.step_id, step_run.action_disposition.value)
                    for step_run in step_runs
                ),
                "config_mode": active_config.mode.value,
                "allow_live_input": active_config.allow_live_input,
                "execute_requested": execute,
                "metrics_available": metrics is not None,
                "policy_context_completeness": (
                    None
                    if policy_context is None
                    else policy_context.completeness.value
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
        return ScenarioActionRunResult.ok(
            runner_name=self.runner_name,
            scenario_definition=normalized_scenario,
            scenario_run=scenario_run,
            details={
                "status": scenario_run.status.value,
                "step_count": len(step_runs),
                "signal_status": scenario_run.signal_status,
            },
        )

    def _run_action_step(
        self,
        step: ScenarioStepDefinition,
        *,
        before_snapshot: SemanticStateSnapshot | None,
        config: RunConfig,
        metrics: VirtualDesktopMetrics | None,
        policy_context: PolicyEvaluationContext | None,
        execute: bool,
    ) -> ScenarioActionStepRun:
        stage_history = [ScenarioActionStepStage.started]
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
            return self._action_step_run(
                step,
                action_disposition=ScenarioActionDisposition.incomplete,
                final_stage=ScenarioActionStepStage.failed,
                stage_history=tuple(stage_history + [ScenarioActionStepStage.failed]),
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
            return self._action_step_run(
                step,
                action_disposition=ScenarioActionDisposition.incomplete,
                final_stage=ScenarioActionStepStage.incomplete,
                stage_history=tuple(stage_history + [ScenarioActionStepStage.incomplete]),
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
                    "capture_phase": "pre_action",
                },
            )
            return self._action_step_run(
                step,
                action_disposition=ScenarioActionDisposition.incomplete,
                final_stage=ScenarioActionStepStage.incomplete,
                stage_history=tuple(stage_history + [ScenarioActionStepStage.incomplete]),
                reason=capture_result.error_message
                or "Capture did not provide a usable frame.",
                signal_status="partial",
                state_machine_trace=state_machine.trace(
                    signal_status="partial",
                    metadata={
                        "capture_provider_name": capture_result.provider_name,
                        "capture_error_code": capture_result.error_code,
                        "capture_phase": "pre_action",
                    },
                ),
                metadata={
                    "capture_provider_name": capture_result.provider_name,
                    "capture_error_code": capture_result.error_code,
                    "capture_phase": "pre_action",
                },
            )
        stage_history.append(ScenarioActionStepStage.observed)
        state_machine.transition(
            ScenarioFlowState.observed,
            next_expected_signal="semantic_understanding",
            metadata={
                "capture_provider_name": capture_result.provider_name,
                "frame_id": None if capture_result.frame is None else capture_result.frame.frame_id,
                "capture_phase": "pre_action",
            },
        )

        understanding = self._understand_step(capture_result, step)
        if understanding.understood:
            stage_history.append(ScenarioActionStepStage.understood)
            state_machine.transition(
                ScenarioFlowState.understood,
                confidence=_understanding_confidence(
                    understanding.exposure_view,
                    understanding.matched_candidate_ids,
                ),
                next_expected_signal="candidate_selection",
                metadata={
                    "matched_candidate_ids": understanding.matched_candidate_ids,
                    "snapshot_id": (
                        None if understanding.snapshot is None else understanding.snapshot.snapshot_id
                    ),
                },
            )
        if not understanding.success:
            stage_history.append(ScenarioActionStepStage.incomplete)
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
            return self._action_step_run(
                step,
                action_disposition=ScenarioActionDisposition.incomplete,
                final_stage=ScenarioActionStepStage.incomplete,
                stage_history=tuple(stage_history),
                reason=understanding.reason,
                pre_action_snapshot=understanding.snapshot,
                exposure_view=understanding.exposure_view,
                matched_candidate_ids=understanding.matched_candidate_ids,
                signal_status=step_signal_status,
                state_machine_trace=state_machine.trace(
                    signal_status=step_signal_status,
                    metadata=understanding.details,
                ),
                metadata=understanding.details,
            )

        action_resolution = self._resolve_action(
            step,
            snapshot=understanding.snapshot,
            exposure_view=understanding.exposure_view,
            matched_candidate_ids=understanding.matched_candidate_ids,
            config=config,
            metrics=metrics,
            policy_context=policy_context,
            execute=execute,
            state_machine=state_machine,
        )
        stage_history.extend(action_resolution.stage_updates)
        if not action_resolution.proceed_to_post_action:
            terminal_stage = (
                ScenarioActionStepStage.incomplete
                if action_resolution.final_stage is None
                else action_resolution.final_stage
            )
            stage_history.append(terminal_stage)
            return self._action_step_run(
                step,
                action_disposition=action_resolution.action_disposition,
                final_stage=terminal_stage,
                stage_history=tuple(stage_history),
                reason=action_resolution.reason,
                pre_action_snapshot=understanding.snapshot,
                exposure_view=understanding.exposure_view,
                scaffold_view=action_resolution.scaffold_view,
                dry_run_evaluation=action_resolution.dry_run_evaluation,
                safe_click_execution=action_resolution.safe_click_execution,
                matched_candidate_ids=understanding.matched_candidate_ids,
                selected_candidate_id=action_resolution.selected_candidate_id,
                selected_intent_id=(
                    None
                    if action_resolution.selected_intent is None
                    else action_resolution.selected_intent.intent_id
                ),
                signal_status=_combine_signal_status(
                    understanding.signal_status,
                    action_resolution.signal_status,
                ),
                state_machine_trace=state_machine.trace(
                    signal_status=_combine_signal_status(
                        understanding.signal_status,
                        action_resolution.signal_status,
                    ),
                    metadata=action_resolution.details,
                ),
                metadata={
                    **dict(understanding.details),
                    **dict(action_resolution.details),
                },
            )

        post_capture_result = self._capture_provider.capture_frame()
        if not post_capture_result.success or post_capture_result.frame is None:
            stage_history.append(ScenarioActionStepStage.incomplete)
            state_machine.transition(
                ScenarioFlowState.recovery_needed,
                confidence=_understanding_confidence(
                    understanding.exposure_view,
                    understanding.matched_candidate_ids,
                ),
                block_reason=post_capture_result.error_message
                or "Post-action capture did not provide a usable frame.",
                recovery_hint="Retry post-action observation when a readable frame is available.",
                next_expected_signal="capture_frame",
                metadata={
                    "capture_provider_name": post_capture_result.provider_name,
                    "capture_error_code": post_capture_result.error_code,
                    "capture_phase": "post_action",
                },
            )
            return self._action_step_run(
                step,
                action_disposition=action_resolution.action_disposition,
                final_stage=ScenarioActionStepStage.incomplete,
                stage_history=tuple(stage_history),
                reason=post_capture_result.error_message
                or "Post-action capture did not provide a usable frame.",
                pre_action_snapshot=understanding.snapshot,
                exposure_view=understanding.exposure_view,
                scaffold_view=action_resolution.scaffold_view,
                dry_run_evaluation=action_resolution.dry_run_evaluation,
                safe_click_execution=action_resolution.safe_click_execution,
                matched_candidate_ids=understanding.matched_candidate_ids,
                selected_candidate_id=action_resolution.selected_candidate_id,
                selected_intent_id=(
                    None
                    if action_resolution.selected_intent is None
                    else action_resolution.selected_intent.intent_id
                ),
                signal_status="partial",
                state_machine_trace=state_machine.trace(
                    signal_status="partial",
                    metadata={
                        "capture_provider_name": post_capture_result.provider_name,
                        "capture_error_code": post_capture_result.error_code,
                        "capture_phase": "post_action",
                    },
                ),
                metadata={
                    **dict(understanding.details),
                    **dict(action_resolution.details),
                    "capture_provider_name": post_capture_result.provider_name,
                    "capture_error_code": post_capture_result.error_code,
                    "capture_phase": "post_action",
                },
            )
        stage_history.append(ScenarioActionStepStage.post_observed)
        state_machine.transition(
            ScenarioFlowState.observed,
            confidence=_understanding_confidence(
                understanding.exposure_view,
                understanding.matched_candidate_ids,
            ),
            next_expected_signal="post_action_semantic_understanding",
            metadata={
                "capture_provider_name": post_capture_result.provider_name,
                "frame_id": None if post_capture_result.frame is None else post_capture_result.frame.frame_id,
                "capture_phase": "post_action",
            },
        )

        post_understanding = self._understand_step(post_capture_result, step)
        if post_understanding.understood:
            stage_history.append(ScenarioActionStepStage.post_understood)
            state_machine.transition(
                ScenarioFlowState.understood,
                confidence=_understanding_confidence(
                    post_understanding.exposure_view,
                    post_understanding.matched_candidate_ids,
                ),
                next_expected_signal="verification_result",
                metadata={
                    "matched_candidate_ids": post_understanding.matched_candidate_ids,
                    "snapshot_id": (
                        None
                        if post_understanding.snapshot is None
                        else post_understanding.snapshot.snapshot_id
                    ),
                    "capture_phase": "post_action",
                },
            )
        if not post_understanding.success:
            stage_history.append(ScenarioActionStepStage.incomplete)
            state_machine.transition(
                ScenarioFlowState.recovery_needed,
                confidence=_understanding_confidence(
                    post_understanding.exposure_view,
                    post_understanding.matched_candidate_ids,
                ),
                block_reason=post_understanding.reason,
                recovery_hint=_recovery_hint_for_understanding(post_understanding.details),
                next_expected_signal=_next_expected_signal_for_understanding(
                    post_understanding.details
                ),
                metadata=post_understanding.details,
            )
            step_signal_status = _combine_signal_status(
                understanding.signal_status,
                action_resolution.signal_status,
                post_understanding.signal_status,
            )
            return self._action_step_run(
                step,
                action_disposition=action_resolution.action_disposition,
                final_stage=ScenarioActionStepStage.incomplete,
                stage_history=tuple(stage_history),
                reason=post_understanding.reason,
                pre_action_snapshot=understanding.snapshot,
                post_action_snapshot=post_understanding.snapshot,
                exposure_view=understanding.exposure_view,
                scaffold_view=action_resolution.scaffold_view,
                dry_run_evaluation=action_resolution.dry_run_evaluation,
                safe_click_execution=action_resolution.safe_click_execution,
                matched_candidate_ids=understanding.matched_candidate_ids,
                selected_candidate_id=action_resolution.selected_candidate_id,
                selected_intent_id=(
                    None
                    if action_resolution.selected_intent is None
                    else action_resolution.selected_intent.intent_id
                ),
                signal_status=step_signal_status,
                state_machine_trace=state_machine.trace(
                    signal_status=step_signal_status,
                    metadata=post_understanding.details,
                ),
                metadata={
                    **dict(understanding.details),
                    **dict(action_resolution.details),
                    **{
                        f"post_action_{key}": value
                        for key, value in dict(post_understanding.details).items()
                    },
                },
            )

        transition_before = (
            before_snapshot
            if before_snapshot is not None
            else _synthetic_before_snapshot(post_understanding.snapshot)
        )
        verification_result = self._verifier.verify(
            step.expected_outcome,
            SemanticStateTransition(
                before=transition_before,
                after=post_understanding.snapshot,
            ),
        )
        return self._verification_step_run(
            step,
            before_snapshot=before_snapshot,
            transition_before=transition_before,
            understanding=understanding,
            post_understanding=post_understanding,
            action_resolution=action_resolution,
            verification_result=verification_result,
            stage_history=stage_history,
            state_machine=state_machine,
        )

    def _verification_step_run(
        self,
        step: ScenarioStepDefinition,
        *,
        before_snapshot: SemanticStateSnapshot | None,
        transition_before: SemanticStateSnapshot,
        understanding,
        post_understanding,
        action_resolution: _ActionResolution,
        verification_result: VerificationResult,
        stage_history: list[ScenarioActionStepStage],
        state_machine: InstrumentedScenarioStateMachine,
    ) -> ScenarioActionStepRun:
        common_metadata = {
            **dict(understanding.details),
            **dict(action_resolution.details),
            **{
                f"post_action_{key}": value
                for key, value in dict(post_understanding.details).items()
            },
            "verification_before_snapshot_id": transition_before.snapshot_id,
            "synthetic_before_snapshot": before_snapshot is None,
            "verification_status": verification_result.status.value,
        }
        common_kwargs = {
            "step": step,
            "action_disposition": action_resolution.action_disposition,
            "pre_action_snapshot": understanding.snapshot,
            "post_action_snapshot": post_understanding.snapshot,
            "exposure_view": understanding.exposure_view,
            "scaffold_view": action_resolution.scaffold_view,
            "dry_run_evaluation": action_resolution.dry_run_evaluation,
            "safe_click_execution": action_resolution.safe_click_execution,
            "verification_result": verification_result,
            "matched_candidate_ids": understanding.matched_candidate_ids,
            "selected_candidate_id": action_resolution.selected_candidate_id,
            "selected_intent_id": (
                None
                if action_resolution.selected_intent is None
                else action_resolution.selected_intent.intent_id
            ),
            "metadata": common_metadata,
        }

        if verification_result.status is VerificationStatus.satisfied:
            stage_history.append(ScenarioActionStepStage.verified)
            step_signal_status = _combine_signal_status(
                understanding.signal_status,
                action_resolution.signal_status,
                post_understanding.signal_status,
            )
            state_machine.transition(
                ScenarioFlowState.verification_passed,
                confidence=_verification_confidence(
                    post_understanding.exposure_view,
                    post_understanding.matched_candidate_ids,
                ),
                next_expected_signal="scenario_step_complete",
                metadata={"verification_status": verification_result.status.value},
            )
            return self._action_step_run(
                final_stage=ScenarioActionStepStage.verified,
                stage_history=tuple(stage_history),
                reason=verification_result.summary,
                signal_status=step_signal_status,
                state_machine_trace=state_machine.trace(
                    signal_status=step_signal_status,
                    metadata={"verification_status": verification_result.status.value},
                ),
                **common_kwargs,
            )
        if verification_result.status is VerificationStatus.unknown:
            stage_history.append(ScenarioActionStepStage.incomplete)
            state_machine.transition(
                ScenarioFlowState.recovery_needed,
                confidence=_verification_confidence(
                    post_understanding.exposure_view,
                    post_understanding.matched_candidate_ids,
                ),
                block_reason=verification_result.summary,
                recovery_hint="Repeat observation with more complete semantic inputs before retrying verification.",
                next_expected_signal="capture_frame",
                metadata={"verification_status": verification_result.status.value},
            )
            return self._action_step_run(
                final_stage=ScenarioActionStepStage.incomplete,
                stage_history=tuple(stage_history),
                reason=verification_result.summary,
                signal_status="partial",
                state_machine_trace=state_machine.trace(
                    signal_status="partial",
                    metadata={"verification_status": verification_result.status.value},
                ),
                **common_kwargs,
            )

        stage_history.append(ScenarioActionStepStage.failed)
        step_signal_status = _combine_signal_status(
            understanding.signal_status,
            action_resolution.signal_status,
            post_understanding.signal_status,
        )
        state_machine.transition(
            ScenarioFlowState.verification_failed,
            confidence=_verification_confidence(
                post_understanding.exposure_view,
                post_understanding.matched_candidate_ids,
            ),
            block_reason=verification_result.summary,
            recovery_hint="Inspect the semantic delta and verification expectations before retrying the step.",
            next_expected_signal="verification_delta",
            metadata={"verification_status": verification_result.status.value},
        )
        return self._action_step_run(
            final_stage=ScenarioActionStepStage.failed,
            stage_history=tuple(stage_history),
            reason=verification_result.summary,
            signal_status=step_signal_status,
            state_machine_trace=state_machine.trace(
                signal_status=step_signal_status,
                metadata={"verification_status": verification_result.status.value},
            ),
            **common_kwargs,
        )

    def _resolve_action(
        self,
        step: ScenarioStepDefinition,
        *,
        snapshot: SemanticStateSnapshot,
        exposure_view,
        matched_candidate_ids: tuple[str, ...],
        config: RunConfig,
        metrics: VirtualDesktopMetrics | None,
        policy_context: PolicyEvaluationContext | None,
        execute: bool,
        state_machine: InstrumentedScenarioStateMachine,
    ) -> _ActionResolution:
        scaffolding_result = self._action_intent_scaffolder.scaffold(
            snapshot,
            exposure_view=exposure_view,
        )
        if not scaffolding_result.success or scaffolding_result.scaffold_view is None:
            state_machine.transition(
                ScenarioFlowState.recovery_needed,
                confidence=_understanding_confidence(exposure_view, matched_candidate_ids),
                block_reason=scaffolding_result.error_message
                or "Action-intent scaffolding failed for the selected candidates.",
                recovery_hint="Retry action-intent scaffolding after exposure metadata is complete.",
                next_expected_signal="intent_scaffolding",
                metadata={"error_code": scaffolding_result.error_code},
            )
            return _ActionResolution(
                proceed_to_post_action=False,
                action_disposition=ScenarioActionDisposition.incomplete,
                reason=scaffolding_result.error_message
                or "Action-intent scaffolding failed for the selected candidates.",
                signal_status="partial",
                final_stage=ScenarioActionStepStage.incomplete,
                details={
                    "action_stage": "intent_scaffolding",
                    "action_scaffolder_name": getattr(
                        self._action_intent_scaffolder,
                        "scaffolder_name",
                        type(self._action_intent_scaffolder).__name__,
                    ),
                    "error_code": scaffolding_result.error_code,
                },
            )

        selected_candidate_id = matched_candidate_ids[0]
        selected_candidate_confidence = _selected_candidate_confidence(
            exposure_view,
            candidate_id=selected_candidate_id,
        )
        state_machine.transition(
            ScenarioFlowState.candidate_selected,
            confidence=selected_candidate_confidence,
            next_expected_signal="action_intent_scaffold",
            metadata={"selected_candidate_id": selected_candidate_id},
        )
        selected_intent = _select_intent(
            scaffolding_result.scaffold_view,
            candidate_id=selected_candidate_id,
        )
        if selected_intent is None:
            state_machine.transition(
                ScenarioFlowState.recovery_needed,
                confidence=selected_candidate_confidence,
                block_reason="No scaffolded action intent matched the selected scenario candidate.",
                recovery_hint="Rebuild action-intent scaffolds for the selected candidate.",
                next_expected_signal="intent_selection",
                metadata={"selected_candidate_id": selected_candidate_id},
            )
            return _ActionResolution(
                proceed_to_post_action=False,
                action_disposition=ScenarioActionDisposition.incomplete,
                reason="No scaffolded action intent matched the selected scenario candidate.",
                signal_status="partial",
                scaffold_view=scaffolding_result.scaffold_view,
                selected_candidate_id=selected_candidate_id,
                final_stage=ScenarioActionStepStage.incomplete,
                details={
                    "action_stage": "intent_selection",
                    "available_intent_candidate_ids": tuple(
                        intent.candidate_id
                        for intent in scaffolding_result.scaffold_view.intents
                    ),
                },
            )
        state_machine.transition(
            ScenarioFlowState.intent_built,
            confidence=selected_intent.candidate_score,
            next_expected_signal="dry_run_evaluation",
            metadata={
                "selected_candidate_id": selected_candidate_id,
                "selected_intent_id": selected_intent.intent_id,
            },
        )

        dry_run_result = self._dry_run_action_engine.evaluate_intent(
            selected_intent,
            snapshot=snapshot,
        )
        if not dry_run_result.success or dry_run_result.evaluation is None:
            state_machine.transition(
                ScenarioFlowState.recovery_needed,
                confidence=selected_intent.candidate_score,
                block_reason=dry_run_result.error_message
                or "Dry-run action evaluation failed for the selected intent.",
                recovery_hint="Retry dry-run evaluation with a complete semantic snapshot.",
                next_expected_signal="dry_run_evaluation",
                metadata={"error_code": dry_run_result.error_code},
            )
            return _ActionResolution(
                proceed_to_post_action=False,
                action_disposition=ScenarioActionDisposition.incomplete,
                reason=dry_run_result.error_message
                or "Dry-run action evaluation failed for the selected intent.",
                signal_status="partial",
                stage_updates=(ScenarioActionStepStage.intent_selected,),
                selected_candidate_id=selected_candidate_id,
                selected_intent=selected_intent,
                scaffold_view=scaffolding_result.scaffold_view,
                final_stage=ScenarioActionStepStage.incomplete,
                details={
                    "action_stage": "dry_run_evaluation",
                    "dry_run_engine_name": getattr(
                        self._dry_run_action_engine,
                        "engine_name",
                        type(self._dry_run_action_engine).__name__,
                    ),
                    "error_code": dry_run_result.error_code,
                },
            )

        dry_run_evaluation = dry_run_result.evaluation
        common_updates = (
            ScenarioActionStepStage.intent_selected,
            ScenarioActionStepStage.dry_run_evaluated,
            ScenarioActionStepStage.action_resolved,
        )
        if dry_run_evaluation.disposition in {
            DryRunActionDisposition.incomplete,
            DryRunActionDisposition.rejected,
        }:
            state_machine.transition(
                ScenarioFlowState.recovery_needed,
                confidence=selected_intent.candidate_score,
                block_reason=dry_run_evaluation.summary,
                recovery_hint="Resolve incomplete dry-run inputs before retrying the action step.",
                next_expected_signal="dry_run_evaluation",
                metadata={
                    "dry_run_disposition": dry_run_evaluation.disposition.value,
                },
            )
            return _ActionResolution(
                proceed_to_post_action=False,
                action_disposition=ScenarioActionDisposition.incomplete,
                reason=dry_run_evaluation.summary,
                signal_status="partial",
                stage_updates=common_updates,
                selected_candidate_id=selected_candidate_id,
                selected_intent=selected_intent,
                scaffold_view=scaffolding_result.scaffold_view,
                dry_run_evaluation=dry_run_evaluation,
                final_stage=ScenarioActionStepStage.incomplete,
                details={
                    "action_stage": "dry_run_resolution",
                    "dry_run_disposition": dry_run_evaluation.disposition.value,
                    "blocking_reasons": dry_run_evaluation.blocking_reasons,
                },
            )
        if dry_run_evaluation.disposition is DryRunActionDisposition.would_block:
            state_machine.transition(
                ScenarioFlowState.blocked,
                confidence=selected_intent.candidate_score,
                block_reason=dry_run_evaluation.summary,
                recovery_hint="Review blocking dry-run checks before retrying the action step.",
                next_expected_signal="operator_review",
                metadata={
                    "dry_run_disposition": dry_run_evaluation.disposition.value,
                },
            )
            return _ActionResolution(
                proceed_to_post_action=False,
                action_disposition=ScenarioActionDisposition.blocked,
                reason=dry_run_evaluation.summary,
                signal_status=_combine_signal_status(
                    scaffolding_result.scaffold_view.signal_status,
                    "available",
                ),
                stage_updates=common_updates,
                selected_candidate_id=selected_candidate_id,
                selected_intent=selected_intent,
                scaffold_view=scaffolding_result.scaffold_view,
                dry_run_evaluation=dry_run_evaluation,
                final_stage=ScenarioActionStepStage.failed,
                details={
                    "action_stage": "dry_run_resolution",
                    "dry_run_disposition": dry_run_evaluation.disposition.value,
                    "blocking_reasons": dry_run_evaluation.blocking_reasons,
                },
            )
        state_machine.transition(
            ScenarioFlowState.dry_run_passed,
            confidence=selected_intent.candidate_score,
            next_expected_signal="post_action_observation",
            metadata={"dry_run_disposition": dry_run_evaluation.disposition.value},
        )
        if step.execution_eligibility is ScenarioExecutionEligibility.dry_run_only:
            return _ActionResolution(
                proceed_to_post_action=True,
                action_disposition=ScenarioActionDisposition.dry_run_only,
                reason="Scenario step remained on the dry-run-only path after intent evaluation.",
                signal_status=_combine_signal_status(
                    scaffolding_result.scaffold_view.signal_status,
                    "available",
                ),
                stage_updates=common_updates,
                selected_candidate_id=selected_candidate_id,
                selected_intent=selected_intent,
                scaffold_view=scaffolding_result.scaffold_view,
                dry_run_evaluation=dry_run_evaluation,
                details={
                    "action_stage": "dry_run_resolution",
                    "dry_run_disposition": dry_run_evaluation.disposition.value,
                    "safe_click_consulted": False,
                },
            )

        safe_click_result = self._safe_click_executor.handle(
            selected_intent,
            config=config,
            metrics=metrics,
            snapshot=snapshot,
            policy_context=policy_context,
            execute=execute,
        )
        return _resolve_safe_click_result(
            safe_click_result=safe_click_result,
            selected_candidate_id=selected_candidate_id,
            selected_intent=selected_intent,
            scaffold_view=scaffolding_result.scaffold_view,
            dry_run_evaluation=dry_run_evaluation,
            execute=execute,
            safe_click_executor=self._safe_click_executor,
            state_machine=state_machine,
        )

    def _action_step_run(
        self,
        step: ScenarioStepDefinition,
        *,
        action_disposition: ScenarioActionDisposition,
        final_stage: ScenarioActionStepStage,
        stage_history: tuple[ScenarioActionStepStage, ...],
        reason: str,
        pre_action_snapshot: SemanticStateSnapshot | None = None,
        post_action_snapshot: SemanticStateSnapshot | None = None,
        exposure_view=None,
        scaffold_view: ActionIntentScaffoldView | None = None,
        dry_run_evaluation: DryRunActionEvaluation | None = None,
        safe_click_execution: SafeClickExecution | None = None,
        verification_result: VerificationResult | None = None,
        matched_candidate_ids: tuple[str, ...] = (),
        selected_candidate_id: str | None = None,
        selected_intent_id: str | None = None,
        signal_status: str = "absent",
        state_machine_trace: ScenarioStateMachineTrace | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> ScenarioActionStepRun:
        live_execution_attempted = (
            action_disposition is ScenarioActionDisposition.real_click_executed
        )
        return ScenarioActionStepRun(
            step_id=step.step_id,
            summary=step.summary,
            execution_eligibility=step.execution_eligibility,
            action_disposition=action_disposition,
            final_stage=final_stage,
            stage_history=stage_history,
            reason=reason,
            pre_action_snapshot=pre_action_snapshot,
            post_action_snapshot=post_action_snapshot,
            exposure_view=exposure_view,
            scaffold_view=scaffold_view,
            dry_run_evaluation=dry_run_evaluation,
            safe_click_execution=safe_click_execution,
            verification_result=verification_result,
            matched_candidate_ids=matched_candidate_ids,
            selected_candidate_id=selected_candidate_id,
            selected_intent_id=selected_intent_id,
            signal_status=signal_status,
            state_machine_trace=state_machine_trace,
            observe_only_inputs=True,
            safety_first=True,
            non_executing=not live_execution_attempted,
            live_execution_attempted=live_execution_attempted,
            metadata={
                **dict(step.metadata),
                **({} if metadata is None else dict(metadata)),
                **_state_machine_metadata(state_machine_trace),
                "observe_only_inputs": True,
                "safety_first": True,
                "non_executing": not live_execution_attempted,
                "live_execution_attempted": live_execution_attempted,
                "final_stage": final_stage.value,
                "stage_history": tuple(stage.value for stage in stage_history),
                "execution_eligibility": step.execution_eligibility.value,
                "action_disposition": action_disposition.value,
                "matched_candidate_ids": matched_candidate_ids,
                "selected_candidate_id": selected_candidate_id,
                "selected_intent_id": selected_intent_id,
                "pre_action_snapshot_id": (
                    None
                    if pre_action_snapshot is None
                    else pre_action_snapshot.snapshot_id
                ),
                "post_action_snapshot_id": (
                    None
                    if post_action_snapshot is None
                    else post_action_snapshot.snapshot_id
                ),
            },
        )


def _resolve_safe_click_result(
    *,
    safe_click_result,
    selected_candidate_id: str,
    selected_intent: ActionIntent,
    scaffold_view: ActionIntentScaffoldView,
    dry_run_evaluation: DryRunActionEvaluation,
    execute: bool,
    safe_click_executor: SafeClickExecutor,
    state_machine: InstrumentedScenarioStateMachine,
) -> _ActionResolution:
    if not safe_click_result.success or safe_click_result.execution is None:
        state_machine.transition(
            ScenarioFlowState.recovery_needed,
            confidence=selected_intent.candidate_score,
            block_reason=safe_click_result.error_message
            or "Safe click evaluation failed for the selected intent.",
            recovery_hint="Retry safe-click evaluation after policy, metrics, and target validation inputs are complete.",
            next_expected_signal="safe_click_resolution",
            metadata={"error_code": safe_click_result.error_code},
        )
        return _ActionResolution(
            proceed_to_post_action=False,
            action_disposition=ScenarioActionDisposition.incomplete,
            reason=safe_click_result.error_message
            or "Safe click evaluation failed for the selected intent.",
            signal_status="partial",
            stage_updates=(
                ScenarioActionStepStage.intent_selected,
                ScenarioActionStepStage.dry_run_evaluated,
            ),
            selected_candidate_id=selected_candidate_id,
            selected_intent=selected_intent,
            scaffold_view=scaffold_view,
            dry_run_evaluation=dry_run_evaluation,
            final_stage=ScenarioActionStepStage.incomplete,
            details={
                "action_stage": "safe_click_resolution",
                "safe_click_executor_name": getattr(
                    safe_click_executor,
                    "executor_name",
                    type(safe_click_executor).__name__,
                ),
                "error_code": safe_click_result.error_code,
            },
        )

    safe_click_execution = safe_click_result.execution
    common_updates = (
        ScenarioActionStepStage.intent_selected,
        ScenarioActionStepStage.dry_run_evaluated,
        ScenarioActionStepStage.action_resolved,
    )
    mapped_disposition = _safe_click_disposition(safe_click_execution.status)
    if safe_click_execution.status is SafeClickPrototypeStatus.blocked:
        state_machine.transition(
            ScenarioFlowState.blocked,
            confidence=selected_intent.candidate_score,
            block_reason=safe_click_execution.summary,
            recovery_hint="Review blocked safety gates before retrying the real-click-eligible step.",
            next_expected_signal="operator_review",
            metadata={
                "safe_click_status": safe_click_execution.status.value,
                "blocked_gate_ids": safe_click_execution.blocked_gate_ids,
            },
        )
        return _ActionResolution(
            proceed_to_post_action=False,
            action_disposition=mapped_disposition,
            reason=safe_click_execution.summary,
            signal_status="available",
            stage_updates=common_updates,
            selected_candidate_id=selected_candidate_id,
            selected_intent=selected_intent,
            scaffold_view=scaffold_view,
            dry_run_evaluation=dry_run_evaluation,
            safe_click_execution=safe_click_execution,
            final_stage=ScenarioActionStepStage.failed,
            details={
                "action_stage": "safe_click_resolution",
                "safe_click_status": safe_click_execution.status.value,
                "blocked_gate_ids": safe_click_execution.blocked_gate_ids,
                "blocking_reasons": safe_click_execution.blocking_reasons,
            },
        )
    if safe_click_execution.status is SafeClickPrototypeStatus.real_click_allowed:
        state_machine.transition(
            ScenarioFlowState.execution_allowed,
            confidence=selected_intent.candidate_score,
            next_expected_signal="post_action_observation",
            metadata={
                "safe_click_status": safe_click_execution.status.value,
                "execute_requested": execute,
            },
        )
    elif safe_click_execution.status is SafeClickPrototypeStatus.real_click_executed:
        state_machine.transition(
            ScenarioFlowState.execution_allowed,
            confidence=selected_intent.candidate_score,
            next_expected_signal="safe_click_execution",
            metadata={
                "safe_click_status": safe_click_execution.status.value,
                "execute_requested": execute,
            },
        )
        state_machine.transition(
            ScenarioFlowState.executed,
            confidence=selected_intent.candidate_score,
            next_expected_signal="post_action_observation",
            live_execution_attempted=True,
            non_executing=False,
            metadata={
                "safe_click_status": safe_click_execution.status.value,
                "execute_requested": execute,
            },
        )
    return _ActionResolution(
        proceed_to_post_action=True,
        action_disposition=mapped_disposition,
        reason=safe_click_execution.summary,
        signal_status="available",
        stage_updates=common_updates,
        selected_candidate_id=selected_candidate_id,
        selected_intent=selected_intent,
        scaffold_view=scaffold_view,
        dry_run_evaluation=dry_run_evaluation,
        safe_click_execution=safe_click_execution,
        details={
            "action_stage": "safe_click_resolution",
            "safe_click_status": safe_click_execution.status.value,
            "blocked_gate_ids": safe_click_execution.blocked_gate_ids,
            "blocking_reasons": safe_click_execution.blocking_reasons,
            "execute_requested": execute,
        },
    )


def _safe_click_disposition(
    status: SafeClickPrototypeStatus,
) -> ScenarioActionDisposition:
    if status is SafeClickPrototypeStatus.dry_run_only:
        return ScenarioActionDisposition.dry_run_only
    if status is SafeClickPrototypeStatus.blocked:
        return ScenarioActionDisposition.blocked
    if status is SafeClickPrototypeStatus.real_click_allowed:
        return ScenarioActionDisposition.real_click_eligible
    return ScenarioActionDisposition.real_click_executed


def _select_intent(
    scaffold_view: ActionIntentScaffoldView,
    *,
    candidate_id: str,
) -> ActionIntent | None:
    for intent in scaffold_view.intents:
        if intent.candidate_id == candidate_id:
            return intent
    return None


def _scenario_action_run_status(
    *,
    normalized_scenario: ScenarioDefinition,
    step_runs: tuple[ScenarioActionStepRun, ...],
) -> ScenarioRunStatus:
    if normalized_scenario.status.value == "invalid":
        return ScenarioRunStatus.failed
    if any(step_run.final_stage is ScenarioActionStepStage.failed for step_run in step_runs):
        return ScenarioRunStatus.failed
    if not step_runs:
        return ScenarioRunStatus.incomplete
    if any(
        step_run.final_stage is ScenarioActionStepStage.incomplete
        for step_run in step_runs
    ):
        return ScenarioRunStatus.incomplete
    if normalized_scenario.status.value == "incomplete":
        return ScenarioRunStatus.incomplete
    return ScenarioRunStatus.completed


def _action_run_signal_status(step_runs: tuple[ScenarioActionStepRun, ...]) -> str:
    if not step_runs:
        return "absent"
    if all(step_run.signal_status == "available" for step_run in step_runs):
        return "available"
    return "partial"


def _combine_signal_status(*statuses: str) -> str:
    normalized_statuses = tuple(
        status for status in statuses if status in {"available", "partial", "absent"}
    )
    if not normalized_statuses:
        return "absent"
    if any(status == "partial" for status in normalized_statuses):
        return "partial"
    if any(status == "available" for status in normalized_statuses):
        return "available"
    return "absent"


def _selected_candidate_confidence(
    exposure_view,
    *,
    candidate_id: str,
) -> float | None:
    for candidate in exposure_view.candidates:
        if candidate.candidate_id == candidate_id:
            return candidate.score
    return None
