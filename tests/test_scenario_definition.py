from __future__ import annotations

from universal_visual_os_agent.actions.models import (
    ActionPrecondition,
    ActionRequirementStatus,
    ActionSafetyGate,
    ActionTargetValidation,
)
from universal_visual_os_agent.scenarios import (
    SafetyFirstScenarioDefinitionBuilder,
    ScenarioCandidateSelectionConstraint,
    ScenarioDefinition,
    ScenarioDefinitionStatus,
    ScenarioExecutionEligibility,
    ScenarioSafetyRequirement,
    ScenarioStepDefinition,
)
from universal_visual_os_agent.semantics.semantic_delta import SemanticDeltaCategory
from universal_visual_os_agent.semantics.state import SemanticCandidateClass
from universal_visual_os_agent.verification.models import (
    ExpectedSemanticChange,
    ExpectedSemanticOutcome,
    SemanticTransitionExpectation,
)


class _ExplodingScenarioDefinitionBuilder(SafetyFirstScenarioDefinitionBuilder):
    def _build_definition(self, scenario: ScenarioDefinition):
        del scenario
        raise RuntimeError("scenario definition builder exploded")


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
            summary="Definition remains non-executing at this phase.",
            status=ActionRequirementStatus.satisfied,
        ),
    )


def _expectation(item_id: str) -> SemanticTransitionExpectation:
    return SemanticTransitionExpectation(
        summary=f"Expected outcome for {item_id}",
        expected_outcomes=(
            ExpectedSemanticOutcome(
                outcome_id=f"{item_id}-appeared",
                category=SemanticDeltaCategory.candidate,
                item_id=item_id,
                expected_change=ExpectedSemanticChange.appeared,
                summary=f"{item_id} should appear",
            ),
        ),
    )


def test_scenario_definition_builder_validates_a_successful_dry_run_definition() -> None:
    step = ScenarioStepDefinition(
        step_id="open-settings",
        summary="Select the settings button candidate.",
        action_type="candidate_select",
        candidate_constraint=ScenarioCandidateSelectionConstraint(
            candidate_classes=(SemanticCandidateClass.button_like,),
            minimum_score=0.95,
            maximum_candidate_rank=3,
        ),
        expected_outcome=_expectation("settings-button"),
        precondition_requirements=_preconditions(),
        target_validation_requirements=_target_validations(),
        safety_gating_requirements=_safety_gates(),
    )
    scenario = ScenarioDefinition(
        scenario_id="settings-open",
        title="Open Settings",
        summary="Reusable dry-run scenario definition.",
        steps=(step,),
    )

    result = SafetyFirstScenarioDefinitionBuilder().build(scenario)

    assert result.success is True
    assert result.scenario_definition is not None
    assert result.definition_view is not None
    assert result.scenario_definition.status is ScenarioDefinitionStatus.defined
    assert result.definition_view.status is ScenarioDefinitionStatus.defined
    assert result.definition_view.signal_status == "available"
    assert result.definition_view.dry_run_only_step_ids == ("open-settings",)
    assert result.definition_view.real_click_eligible_step_ids == ()
    normalized_step = result.scenario_definition.steps[0]
    assert normalized_step.status is ScenarioDefinitionStatus.defined
    assert normalized_step.execution_eligibility is ScenarioExecutionEligibility.dry_run_only
    assert normalized_step.metadata["step_status"] == "defined"
    assert normalized_step.metadata["execution_eligibility"] == "dry_run_only"


def test_scenario_definition_builder_handles_incomplete_definitions_safely() -> None:
    step = ScenarioStepDefinition(
        step_id="partial-step",
        summary="",
        action_type="",
    )
    scenario = ScenarioDefinition(
        scenario_id="partial-scenario",
        title="Partial Scenario",
        summary="",
        steps=(step,),
    )

    result = SafetyFirstScenarioDefinitionBuilder().build(scenario)

    assert result.success is True
    assert result.scenario_definition is not None
    assert result.definition_view is not None
    assert result.scenario_definition.status is ScenarioDefinitionStatus.incomplete
    assert result.definition_view.signal_status == "partial"
    normalized_step = result.scenario_definition.steps[0]
    assert normalized_step.status is ScenarioDefinitionStatus.incomplete
    assert "missing_action_type" in normalized_step.metadata["diagnostic_codes"]
    assert (
        result.scenario_definition.metadata["missing_candidate_constraint_step_ids"]
        == ("partial-step",)
    )
    assert (
        result.scenario_definition.metadata["missing_expected_outcome_step_ids"]
        == ("partial-step",)
    )


def test_scenario_definition_builder_tracks_real_click_eligibility_metadata_consistently() -> None:
    dry_run_step = ScenarioStepDefinition(
        step_id="inspect-button",
        summary="Inspect the candidate in dry-run mode.",
        action_type="candidate_select",
        candidate_constraint=ScenarioCandidateSelectionConstraint(
            candidate_classes=(SemanticCandidateClass.button_like,),
            minimum_score=0.95,
            maximum_candidate_rank=3,
        ),
        expected_outcome=_expectation("inspect-button"),
        precondition_requirements=_preconditions(),
        target_validation_requirements=_target_validations(),
        safety_gating_requirements=_safety_gates(),
    )
    real_click_step = ScenarioStepDefinition(
        step_id="confirm-button",
        summary="Narrow real-click-eligible prototype step.",
        action_type="candidate_select",
        candidate_constraint=ScenarioCandidateSelectionConstraint(
            candidate_classes=(SemanticCandidateClass.button_like,),
            minimum_score=0.95,
            maximum_candidate_rank=2,
            allow_real_click_prototype=True,
        ),
        expected_outcome=_expectation("confirm-button"),
        precondition_requirements=_preconditions(),
        target_validation_requirements=_target_validations(),
        safety_gating_requirements=_safety_gates(),
        execution_eligibility=ScenarioExecutionEligibility.real_click_eligible,
    )
    scenario = ScenarioDefinition(
        scenario_id="mixed-eligibility",
        title="Mixed Eligibility Scenario",
        summary="Scenario definition with dry-run and narrow real-click eligibility.",
        steps=(dry_run_step, real_click_step),
        real_click_eligible=True,
    )

    result = SafetyFirstScenarioDefinitionBuilder().build(scenario)

    assert result.success is True
    assert result.scenario_definition is not None
    assert result.definition_view is not None
    assert result.scenario_definition.status is ScenarioDefinitionStatus.defined
    assert result.definition_view.dry_run_only_step_ids == ("inspect-button",)
    assert result.definition_view.real_click_eligible_step_ids == ("confirm-button",)
    assert result.scenario_definition.metadata["real_click_eligible_step_ids"] == (
        "confirm-button",
    )
    assert result.scenario_definition.metadata["dry_run_only_step_ids"] == (
        "inspect-button",
    )
    assert result.scenario_definition.steps[1].metadata["allow_real_click_prototype"] is True


def test_scenario_definition_builder_marks_unsupported_real_click_steps_invalid() -> None:
    scenario = ScenarioDefinition(
        scenario_id="unsupported-real-click",
        title="Unsupported Real Click",
        summary="Unsupported real-click constraint should be classified safely.",
        steps=(
            ScenarioStepDefinition(
                step_id="tab-step",
                summary="This step is outside the narrow click prototype.",
                action_type="candidate_select",
                candidate_constraint=ScenarioCandidateSelectionConstraint(
                    candidate_classes=(SemanticCandidateClass.tab_like,),
                    minimum_score=0.95,
                    maximum_candidate_rank=2,
                    allow_real_click_prototype=True,
                ),
                expected_outcome=_expectation("tab-step"),
                precondition_requirements=_preconditions(),
                target_validation_requirements=_target_validations(),
                safety_gating_requirements=_safety_gates(),
                execution_eligibility=ScenarioExecutionEligibility.real_click_eligible,
            ),
        ),
        real_click_eligible=True,
    )

    result = SafetyFirstScenarioDefinitionBuilder().build(scenario)

    assert result.success is True
    assert result.scenario_definition is not None
    assert result.scenario_definition.status is ScenarioDefinitionStatus.invalid
    assert result.scenario_definition.steps[0].status is ScenarioDefinitionStatus.invalid
    assert result.scenario_definition.metadata["unsupported_real_click_step_ids"] == (
        "tab-step",
    )
    assert result.definition_view is not None
    assert result.definition_view.metadata["unsupported_real_click_step_ids"] == (
        "tab-step",
    )


def test_scenario_definition_builder_preserves_safety_first_definition_only_semantics() -> None:
    scenario = ScenarioDefinition(
        scenario_id="safe-scenario",
        title="Safe Scenario",
        summary="Scenario definitions must remain non-executing scaffolds.",
        steps=(
            ScenarioStepDefinition(
                step_id="safe-step",
                summary="Dry-run-only step.",
                action_type="candidate_select",
                candidate_constraint=ScenarioCandidateSelectionConstraint(
                    candidate_classes=(SemanticCandidateClass.button_like,),
                    minimum_score=0.95,
                    maximum_candidate_rank=1,
                ),
                expected_outcome=_expectation("safe-step"),
                precondition_requirements=_preconditions(),
                target_validation_requirements=_target_validations(),
                safety_gating_requirements=_safety_gates(),
                safety_requirement=ScenarioSafetyRequirement(),
            ),
        ),
    )

    result = SafetyFirstScenarioDefinitionBuilder().build(scenario)

    assert result.success is True
    assert result.scenario_definition is not None
    assert result.definition_view is not None
    assert result.scenario_definition.observe_only is True
    assert result.scenario_definition.safety_first is True
    assert result.scenario_definition.definition_only is True
    assert result.scenario_definition.metadata["observe_only"] is True
    assert result.scenario_definition.metadata["definition_only"] is True
    step = result.scenario_definition.steps[0]
    assert step.observe_only is True
    assert step.safety_first is True
    assert step.definition_only is True
    assert step.metadata["observe_only"] is True
    assert step.metadata["safety_first"] is True
    assert step.metadata["definition_only"] is True


def test_scenario_definition_builder_does_not_propagate_unhandled_exceptions() -> None:
    scenario = ScenarioDefinition(
        scenario_id="exploding-scenario",
        title="Exploding Scenario",
        summary="Failure-safe result path.",
    )

    result = _ExplodingScenarioDefinitionBuilder().build(scenario)

    assert result.success is False
    assert result.error_code == "scenario_definition_exception"
    assert result.error_message == "scenario definition builder exploded"
