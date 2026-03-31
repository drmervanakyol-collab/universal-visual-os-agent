from __future__ import annotations

from dataclasses import replace

from test_ai_boundary_contracts import _boundary_context, _center_point
from test_scenario_action_flow import (
    _button_candidate_id,
    _payload,
    _policy_engine,
    _real_click_step,
    _runner as _action_runner,
    _virtual_metrics,
)
from test_semantic_candidate_generation import (
    _StaticResponseBackend,
    _candidate_rich_response,
    _capture_result,
)
from test_windows_capture_runtime_architecture import _FakeBackend, _desktop_request

from universal_visual_os_agent.actions import (
    ActionToolBoundaryBlockCode,
    ActionToolBoundaryStatus,
    ActionToolBoundarySurface,
    ObserveOnlyActionIntentScaffolder,
    ObserveOnlyActionToolBoundaryGuard,
    SafeClickPrototypeExecutor,
)
from universal_visual_os_agent.ai_architecture import (
    ArbitrationConflict,
    ArbitrationConflictKind,
    ArbitrationSource,
    DeterministicEscalationDisposition,
    ObserveOnlyDeterministicEscalationEngine,
    ObserveOnlyPlannerContractBuilder,
    ObserveOnlyResolverContractBuilder,
    ObserveOnlySharedOntologyBinder,
)
from universal_visual_os_agent.ai_boundary import (
    AiBoundaryValidationContext,
    CloudPlannerContract,
    LocalVisualResolverContract,
    ObserveOnlyAiBoundaryValidator,
    PlannerActionSuggestionContract,
)
from universal_visual_os_agent.app.runtime_event_models import (
    RuntimeAnalysisTarget,
    RuntimeDispatchMode,
    RuntimeEvent,
    RuntimeEventCoalescingMode,
    RuntimeEventDisposition,
    RuntimeEventSource,
    RuntimeEventType,
    RuntimeInvalidationScope,
    RuntimeInvalidationSignal,
)
from universal_visual_os_agent.app.runtime_events import (
    ObserveOnlyRuntimeEventCoordinator,
)
from universal_visual_os_agent.config import AgentMode, RunConfig
from universal_visual_os_agent.integrations.windows import (
    WindowsCaptureBackendCapability,
    WindowsCaptureRuntimeMode,
    select_capture_backends,
)
from universal_visual_os_agent.scenarios import (
    ScenarioActionDisposition,
    ScenarioActionStepStage,
    ScenarioDefinition,
    ScenarioFlowState,
    ScenarioRunStatus,
)
from universal_visual_os_agent.semantics import (
    CandidateSelectionRiskLevel,
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


def _capture_to_exposure_context():
    capture_result = _capture_result(_payload())
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(capture_result)
    state_result = PreparedSemanticStateBuilder().build(preparation)
    text_result = PreparedSemanticTextExtractionAdapter(
        text_backend=_StaticResponseBackend(_candidate_rich_response)
    ).extract(preparation, state_result)
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
    exposure_result = ObserveOnlyCandidateExposer().expose(scoring_result.snapshot)
    assert exposure_result.success is True
    assert exposure_result.exposure_view is not None
    return capture_result, scoring_result.snapshot, exposure_result.exposure_view


def test_structural_confidence_capture_runtime_policy_keeps_production_and_diagnostic_paths_separate() -> None:
    backends = (
        _FakeBackend(
            backend_name="dxcam_desktop",
            capability=WindowsCaptureBackendCapability.unavailable_backend(
                backend_name="dxcam_desktop",
                reason="DXcam runtime probe failed.",
            ),
        ),
        _FakeBackend(
            backend_name="gdi_bitblt",
            capability=WindowsCaptureBackendCapability.available_backend(
                backend_name="gdi_bitblt"
            ),
        ),
    )

    production_selection = select_capture_backends(
        backends,
        _desktop_request(),
        runtime_mode=WindowsCaptureRuntimeMode.production,
    )
    diagnostic_selection = select_capture_backends(
        backends,
        _desktop_request(),
        runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
    )

    assert production_selection.selected_backend_name is None
    assert production_selection.capability_available_backend_names == ("gdi_bitblt",)
    assert production_selection.available_backend_names == ()
    assert (
        production_selection.candidates[1].skip_reason
        == "Diagnostic-only backend is disabled in the production capture runtime."
    )
    assert diagnostic_selection.selected_backend_name == "gdi_bitblt"
    assert diagnostic_selection.available_backend_names == ("gdi_bitblt",)
    assert (
        diagnostic_selection.candidates[1].selection_reason
        == "Selected as the highest-priority diagnostic-compatible backend."
    )


def test_structural_confidence_capture_to_semantics_pipeline_preserves_observe_only_candidate_ontology() -> None:
    capture_result, scored_snapshot, exposure_view = _capture_to_exposure_context()

    assert capture_result.details["selected_backend_name"] == "dxcam_desktop"
    assert capture_result.details["backend_fallback_used"] is False
    assert scored_snapshot.metadata["candidate_generation"] is True
    assert scored_snapshot.metadata["candidate_scoring"] is True
    assert exposure_view.signal_status == "available"
    assert exposure_view.exposed_candidate_count > 0
    assert exposure_view.metadata["resolver_readiness_status_counts"]
    assert {
        SemanticCandidateClass.button_like,
        SemanticCandidateClass.input_like,
        SemanticCandidateClass.tab_like,
        SemanticCandidateClass.close_like,
        SemanticCandidateClass.interactive_region_like,
    }.issubset({candidate.candidate_class for candidate in exposure_view.candidates})
    assert all(candidate.actionable is False for candidate in exposure_view.candidates)
    assert all(candidate.non_actionable is True for candidate in exposure_view.candidates)
    assert all(candidate.source_type is not None for candidate in exposure_view.candidates)
    assert all(
        candidate.selection_risk_level is not None
        for candidate in exposure_view.candidates
    )
    assert any(candidate.requires_local_resolver for candidate in exposure_view.candidates)
    ready_candidate = next(
        candidate
        for candidate in exposure_view.candidates
        if candidate.metadata["candidate_resolver_readiness_status"] == "ready"
    )
    binding_result = ObserveOnlySharedOntologyBinder().bind_exposed_candidate(ready_candidate)

    assert binding_result.success is True
    assert binding_result.binding is not None
    assert binding_result.binding.completeness_status == "available"
    assert binding_result.binding.source_type == ready_candidate.source_type
    assert (
        binding_result.binding.selection_risk_level
        == ready_candidate.selection_risk_level
    )


def test_structural_confidence_runtime_event_coalescing_stays_event_first_with_polling_secondary() -> None:
    coordinator = ObserveOnlyRuntimeEventCoordinator()
    first_event = RuntimeEvent(
        event_type=RuntimeEventType.observation_invalidated,
        source=RuntimeEventSource.capture_runtime,
        summary="Desktop frame changed.",
        invalidation_signals=(
            RuntimeInvalidationSignal(
                scope=RuntimeInvalidationScope.frame,
                summary="Frame changed.",
            ),
        ),
        coalescing_mode=RuntimeEventCoalescingMode.merge,
        debounce_key="desktop-frame",
        debounce_window_ms=25,
    )
    second_event = RuntimeEvent(
        event_type=RuntimeEventType.observation_invalidated,
        source=RuntimeEventSource.capture_runtime,
        summary="Candidate set changed.",
        invalidation_signals=(
            RuntimeInvalidationSignal(
                scope=RuntimeInvalidationScope.candidates,
                summary="Candidates changed.",
            ),
        ),
        coalescing_mode=RuntimeEventCoalescingMode.merge,
        debounce_key="desktop-frame",
        debounce_window_ms=25,
    )

    first_submission = coordinator.submit(first_event)
    second_submission = coordinator.submit(second_event)
    dispatch_result = coordinator.dispatch_next()

    assert first_submission.success is True
    assert first_submission.disposition is RuntimeEventDisposition.accepted
    assert second_submission.success is True
    assert second_submission.disposition is RuntimeEventDisposition.coalesced
    assert dispatch_result.success is True
    assert dispatch_result.dispatch_plan is not None
    assert dispatch_result.dispatch_plan.dispatch_mode is RuntimeDispatchMode.event_first
    assert dispatch_result.dispatch_plan.coalesced_event_count == 2
    assert dispatch_result.dispatch_plan.invalidation_scopes == (
        RuntimeInvalidationScope.frame,
        RuntimeInvalidationScope.candidates,
    )
    assert dispatch_result.dispatch_plan.analysis_targets == (
        RuntimeAnalysisTarget.frame_diff,
        RuntimeAnalysisTarget.semantic_state,
        RuntimeAnalysisTarget.candidate_set,
    )
    assert dispatch_result.dispatch_plan.metadata["polling_fallback_secondary"] is True
    assert dispatch_result.dispatch_plan.non_executing is True


def test_structural_confidence_ai_boundary_and_tool_boundary_keep_direct_ai_outputs_non_executable() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    validator = ObserveOnlyAiBoundaryValidator()
    planner_result = validator.validate_planner_contract(
        CloudPlannerContract(
            decision_id="structural-planner-direct",
            summary="Return a valid structured planner suggestion.",
            action_suggestion=PlannerActionSuggestionContract(
                action_type="candidate_select",
                candidate_id=candidate.candidate_id,
                candidate_label=candidate.label,
                target_label="candidate_center",
                confidence=0.88,
            ),
        ),
        context=AiBoundaryValidationContext(snapshot=snapshot, exposure_view=exposure_view),
    )
    assert planner_result.success is True
    assert planner_result.validated_output is not None
    assert planner_result.validated_output.action_suggestion is not None

    guard = ObserveOnlyActionToolBoundaryGuard()
    planner_boundary_result = guard.evaluate_planner_action_suggestion_for_surface(
        planner_result.validated_output.action_suggestion,
        surface=ActionToolBoundarySurface.dry_run_engine,
    )
    scaffolding_result = ObserveOnlyActionIntentScaffolder().scaffold(
        snapshot,
        exposure_view=exposure_view,
    )
    assert scaffolding_result.success is True
    assert scaffolding_result.scaffold_view is not None
    scaffold_boundary_result = guard.evaluate_intent_for_dry_run(
        scaffolding_result.scaffold_view.intents[0],
        snapshot=snapshot,
    )

    assert planner_boundary_result.success is True
    assert planner_boundary_result.assessment is not None
    assert planner_boundary_result.assessment.status is ActionToolBoundaryStatus.blocked
    assert (
        ActionToolBoundaryBlockCode.direct_ai_output_requires_binding
        in planner_boundary_result.assessment.blocking_codes
    )
    assert scaffold_boundary_result.success is True
    assert scaffold_boundary_result.assessment is not None
    assert scaffold_boundary_result.assessment.status is ActionToolBoundaryStatus.allowed


def test_structural_confidence_deterministic_escalation_requires_human_confirmation_for_high_risk_multi_source_conflict() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    binding_result = ObserveOnlySharedOntologyBinder().bind_exposed_candidate(
        exposure_view.candidates[0]
    )
    assert binding_result.success is True
    assert binding_result.binding is not None
    binding = binding_result.binding
    planner_candidate = exposure_view.candidates[-1]
    resolver_response_result = ObserveOnlyResolverContractBuilder().bind_response(
        LocalVisualResolverContract(
            resolution_id="structural-resolver-agrees",
            summary="Choose the deterministic candidate center.",
            action_type="candidate_select",
            candidate_id=binding.candidate_id,
            candidate_label=binding.candidate_label,
            target_label="candidate_center",
            point=_center_point(candidate),
            confidence=0.93,
        ),
        exposure_view=exposure_view,
    )
    planner_response_result = ObserveOnlyPlannerContractBuilder().bind_response(
        CloudPlannerContract(
            decision_id="structural-planner-conflict",
            summary="Choose a different candidate.",
            action_suggestion=PlannerActionSuggestionContract(
                action_type="candidate_select",
                candidate_id=planner_candidate.candidate_id,
                candidate_label=planner_candidate.label,
                target_label="candidate_center",
                confidence=0.89,
                dry_run_only=True,
                live_execution_requested=False,
            ),
        ),
        exposure_view=exposure_view,
    )
    assert resolver_response_result.success is True
    assert resolver_response_result.response_contract is not None
    assert planner_response_result.success is True
    assert planner_response_result.response_contract is not None

    result = ObserveOnlyDeterministicEscalationEngine().evaluate(
        deterministic_binding=replace(
            binding,
            confidence=0.95,
            selection_risk_level=CandidateSelectionRiskLevel.high,
            requires_local_resolver=False,
            disambiguation_needed=False,
            source_conflict_present=True,
            completeness_status="available",
        ),
        resolver_response=resolver_response_result.response_contract,
        planner_response=planner_response_result.response_contract,
        conflicts=(
            ArbitrationConflict(
                kind=ArbitrationConflictKind.candidate_reference_mismatch,
                summary="Deterministic and planner candidate IDs differ.",
                sources=(
                    ArbitrationSource.deterministic_pipeline,
                    ArbitrationSource.cloud_planner,
                ),
                candidate_ids=(binding.candidate_id, planner_candidate.candidate_id),
            ),
        ),
    )

    assert result.success is True
    assert result.decision is not None
    assert result.decision.disposition is DeterministicEscalationDisposition.human_confirmation_required
    assert result.decision.recommended_source is None
    assert result.decision.non_executing is True


def test_structural_confidence_scenario_action_flow_keeps_real_click_eligible_path_non_executing_and_hitl_ready() -> None:
    candidate_id = _button_candidate_id()
    scenario = ScenarioDefinition(
        scenario_id="structural-hitl-confirm-button",
        title="Structural HITL Confirm Button",
        summary="Real-click-eligible path should stay non-executing and HITL-ready.",
        steps=(_real_click_step(candidate_id),),
        real_click_eligible=True,
    )
    runner = _action_runner(
        _capture_result(_payload()),
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
    assert result.scenario_run.non_executing is True
    assert result.scenario_run.live_execution_attempted is False
    assert result.scenario_run.metadata["awaiting_user_confirmation_step_ids"] == (
        "confirm-step",
    )
    step_run = result.scenario_run.step_runs[0]
    assert step_run.final_stage is ScenarioActionStepStage.verified
    assert step_run.action_disposition is ScenarioActionDisposition.real_click_eligible
    assert step_run.recovery_plan is not None
    assert step_run.recovery_plan.awaiting_user_confirmation is True
    assert step_run.state_machine_trace is not None
    assert step_run.state_machine_trace.current_state is ScenarioFlowState.verification_passed
    assert ScenarioFlowState.execution_allowed in step_run.state_machine_trace.state_history
