from __future__ import annotations

from dataclasses import replace

from test_ai_boundary_contracts import _boundary_context, _center_point

from universal_visual_os_agent.actions import (
    ActionToolBoundaryBlockCode,
    ActionToolBoundaryStatus,
    ActionToolBoundarySurface,
    ObserveOnlyActionToolBoundaryGuard,
    ObserveOnlyActionIntentScaffolder,
    ObserveOnlyDryRunActionEngine,
)
from universal_visual_os_agent.ai_boundary import (
    AiBoundaryValidationContext,
    CloudPlannerContract,
    LocalVisualResolverContract,
    ObserveOnlyAiBoundaryValidator,
    PlannerActionSuggestionContract,
)
from universal_visual_os_agent.config import AgentMode, RunConfig
from universal_visual_os_agent.geometry import ScreenPoint
from universal_visual_os_agent.semantics import ObserveOnlyCandidateExposer


def test_tool_boundary_rejects_validated_planner_action_suggestion_until_rebound() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    planner_result = ObserveOnlyAiBoundaryValidator().validate_planner_contract(
        CloudPlannerContract(
            decision_id="planner-direct",
            summary="Return a schema-valid planner suggestion.",
            action_suggestion=PlannerActionSuggestionContract(
                action_type="candidate_select",
                candidate_id=candidate.candidate_id,
                target_label="candidate_center",
                confidence=0.88,
            ),
        ),
        context=AiBoundaryValidationContext(snapshot=snapshot, exposure_view=exposure_view),
    )
    assert planner_result.success is True
    assert planner_result.validated_output is not None
    assert planner_result.validated_output.action_suggestion is not None

    boundary_result = ObserveOnlyActionToolBoundaryGuard().evaluate_planner_action_suggestion_for_surface(
        planner_result.validated_output.action_suggestion,
        surface=ActionToolBoundarySurface.dry_run_engine,
    )

    assert boundary_result.success is True
    assert boundary_result.assessment is not None
    assert boundary_result.assessment.status is ActionToolBoundaryStatus.blocked
    assert (
        ActionToolBoundaryBlockCode.direct_ai_output_requires_binding
        in boundary_result.assessment.blocking_codes
    )
    assert "action_intent_binding_required" in boundary_result.assessment.blocked_check_ids


def test_tool_boundary_rejects_validated_resolver_output_until_rebound() -> None:
    snapshot, exposure_view, candidate = _boundary_context()
    resolver_result = ObserveOnlyAiBoundaryValidator().validate_resolver_contract(
        LocalVisualResolverContract(
            resolution_id="resolver-direct",
            summary="Return a schema-valid resolver suggestion.",
            action_type="candidate_select",
            candidate_id=candidate.candidate_id,
            candidate_label=candidate.label,
            target_label="candidate_center",
            point=_center_point(candidate),
            confidence=0.93,
        ),
        context=AiBoundaryValidationContext(snapshot=snapshot, exposure_view=exposure_view),
    )
    assert resolver_result.success is True
    assert resolver_result.validated_output is not None

    boundary_result = ObserveOnlyActionToolBoundaryGuard().evaluate_resolver_output_for_surface(
        resolver_result.validated_output,
        surface=ActionToolBoundarySurface.safe_click_prototype,
    )

    assert boundary_result.success is True
    assert boundary_result.assessment is not None
    assert boundary_result.assessment.status is ActionToolBoundaryStatus.blocked
    assert (
        ActionToolBoundaryBlockCode.direct_ai_output_requires_binding
        in boundary_result.assessment.blocking_codes
    )
    assert "action_intent_binding_required" in boundary_result.assessment.blocked_check_ids


def test_tool_boundary_accepts_scaffolded_intent_for_dry_run_surface() -> None:
    snapshot = _boundary_context()[0]
    exposure_result = ObserveOnlyCandidateExposer().expose(snapshot)
    assert exposure_result.success is True
    assert exposure_result.exposure_view is not None

    from universal_visual_os_agent.actions import ObserveOnlyActionIntentScaffolder

    scaffolding_result = ObserveOnlyActionIntentScaffolder().scaffold(
        snapshot,
        exposure_view=exposure_result.exposure_view,
    )
    assert scaffolding_result.success is True
    assert scaffolding_result.scaffold_view is not None

    boundary_result = ObserveOnlyActionToolBoundaryGuard().evaluate_intent_for_dry_run(
        scaffolding_result.scaffold_view.intents[0],
        snapshot=snapshot,
    )

    assert boundary_result.success is True
    assert boundary_result.assessment is not None
    assert boundary_result.assessment.status is ActionToolBoundaryStatus.allowed
    assert boundary_result.assessment.blocked_check_ids == ()


def test_safe_click_tool_boundary_short_circuits_after_first_hard_block() -> None:
    snapshot = _boundary_context()[0]
    exposure_result = ObserveOnlyCandidateExposer().expose(snapshot)
    assert exposure_result.success is True
    assert exposure_result.exposure_view is not None

    scaffolding_result = ObserveOnlyActionIntentScaffolder().scaffold(
        snapshot,
        exposure_view=exposure_result.exposure_view,
    )
    assert scaffolding_result.success is True
    assert scaffolding_result.scaffold_view is not None

    unsupported_intent = replace(
        scaffolding_result.scaffold_view.intents[0],
        action_type="hover",
    )
    dry_run_result = ObserveOnlyDryRunActionEngine().evaluate_intent(
        unsupported_intent,
        snapshot=snapshot,
    )
    assert dry_run_result.success is True
    assert dry_run_result.evaluation is not None

    boundary_result = ObserveOnlyActionToolBoundaryGuard().evaluate_intent_for_safe_click(
        unsupported_intent,
        config=RunConfig(mode=AgentMode.safe_action_mode, allow_live_input=True),
        target_screen_point=ScreenPoint(x_px=100, y_px=100),
        dry_run_evaluation=dry_run_result.evaluation,
        policy_decision=None,
        snapshot=snapshot,
        execute=True,
        click_transport_available=True,
    )

    assert boundary_result.success is True
    assert boundary_result.assessment is not None
    assert boundary_result.assessment.status is ActionToolBoundaryStatus.blocked
    assert boundary_result.assessment.blocked_check_ids == ("supported_action_type",)
    assert boundary_result.assessment.metadata["short_circuit_check_id"] == "supported_action_type"
    assert "dry_run_would_execute" in boundary_result.assessment.metadata["skipped_check_ids"]
    assert "policy_allow" in boundary_result.assessment.metadata["skipped_check_ids"]
