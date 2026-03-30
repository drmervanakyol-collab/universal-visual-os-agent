"""Safety-first scenario-definition scaffolding."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace

from universal_visual_os_agent.scenarios.models import (
    ScenarioDefinition,
    ScenarioDefinitionResult,
    ScenarioDefinitionStatus,
    ScenarioDefinitionView,
    ScenarioExecutionEligibility,
    ScenarioStepDefinition,
)
from universal_visual_os_agent.semantics.state import SemanticCandidateClass

_REAL_CLICK_ALLOWED_CLASSES = frozenset({SemanticCandidateClass.button_like})
_REAL_CLICK_MINIMUM_SCORE = 0.9
_REAL_CLICK_MAXIMUM_RANK = 5


@dataclass(slots=True, frozen=True, kw_only=True)
class _StepArtifacts:
    step: ScenarioStepDefinition
    incomplete_reasons: tuple[str, ...] = ()
    invalid_reasons: tuple[str, ...] = ()
    diagnostics: frozenset[str] = frozenset()


class SafetyFirstScenarioDefinitionBuilder:
    """Build stable, reusable scenario definitions without broadening execution."""

    builder_name = "SafetyFirstScenarioDefinitionBuilder"

    def build(self, scenario: ScenarioDefinition) -> ScenarioDefinitionResult:
        try:
            normalized_scenario, definition_view = self._build_definition(scenario)
        except Exception as exc:  # noqa: BLE001 - scenario definition must remain failure-safe
            return ScenarioDefinitionResult.failure(
                builder_name=self.builder_name,
                error_code="scenario_definition_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return ScenarioDefinitionResult.ok(
            builder_name=self.builder_name,
            source_definition=scenario,
            scenario_definition=normalized_scenario,
            definition_view=definition_view,
            details={
                "status": normalized_scenario.status.value,
                "step_count": len(normalized_scenario.steps),
                "signal_status": definition_view.signal_status,
            },
        )

    def _build_definition(
        self,
        scenario: ScenarioDefinition,
    ) -> tuple[ScenarioDefinition, ScenarioDefinitionView]:
        step_id_counts = Counter(
            step.step_id for step in scenario.steps if step.step_id
        )
        duplicate_step_ids = tuple(
            sorted(step_id for step_id, count in step_id_counts.items() if count > 1)
        )

        normalized_step_artifacts = tuple(
            self._normalize_step(step, scenario=scenario) for step in scenario.steps
        )
        normalized_steps = tuple(artifact.step for artifact in normalized_step_artifacts)

        scenario_incomplete_reasons: list[str] = []
        scenario_invalid_reasons: list[str] = []
        if not scenario.scenario_id:
            scenario_incomplete_reasons.append("Scenario identifier is required.")
        if not scenario.title:
            scenario_incomplete_reasons.append("Scenario title is required.")
        if not scenario.summary:
            scenario_incomplete_reasons.append("Scenario summary is required.")
        if not scenario.steps:
            scenario_incomplete_reasons.append("At least one scenario step is required.")
        if not scenario.observe_only:
            scenario_invalid_reasons.append(
                "Scenario definitions in Phase 6A must remain observe-only."
            )
        if not scenario.safety_first:
            scenario_invalid_reasons.append(
                "Scenario definitions in Phase 6A must remain safety-first."
            )
        if not scenario.definition_only:
            scenario_invalid_reasons.append(
                "Scenario definitions in Phase 6A must remain definition-only."
            )
        if not scenario.dry_run_eligible:
            scenario_invalid_reasons.append(
                "Scenario definitions in Phase 6A must remain dry-run eligible."
            )
        if duplicate_step_ids:
            scenario_invalid_reasons.append(
                "Scenario step identifiers must be unique within one scenario."
            )

        invalid_step_ids = tuple(
            step.step_id
            for step in normalized_steps
            if step.status is ScenarioDefinitionStatus.invalid and step.step_id
        )
        incomplete_step_ids = tuple(
            step.step_id
            for step in normalized_steps
            if step.status is ScenarioDefinitionStatus.incomplete and step.step_id
        )
        real_click_eligible_step_ids = tuple(
            step.step_id
            for step in normalized_steps
            if step.execution_eligibility
            is ScenarioExecutionEligibility.real_click_eligible
            and step.step_id
        )
        dry_run_only_step_ids = tuple(
            step.step_id
            for step in normalized_steps
            if step.execution_eligibility is ScenarioExecutionEligibility.dry_run_only
            and step.step_id
        )
        scenario_flag_mismatch_step_ids = tuple(
            sorted(
                step.step_id
                for step in normalized_steps
                if step.execution_eligibility
                is ScenarioExecutionEligibility.real_click_eligible
                and step.step_id
                and not scenario.real_click_eligible
            )
        )
        if scenario_flag_mismatch_step_ids:
            scenario_invalid_reasons.append(
                "Real-click-eligible steps require the scenario to be marked real_click_eligible."
            )

        normalized_status = _scenario_status(
            scenario_incomplete_reasons=scenario_incomplete_reasons,
            scenario_invalid_reasons=scenario_invalid_reasons,
            steps=normalized_steps,
        )
        normalized_reason = _primary_reason(
            invalid_reasons=scenario_invalid_reasons,
            incomplete_reasons=scenario_incomplete_reasons,
            steps=normalized_steps,
        )
        normalized_scenario = replace(
            scenario,
            steps=normalized_steps,
            status=normalized_status,
            status_reason=normalized_reason,
            metadata={
                **dict(scenario.metadata),
                "scenario_definition_built": True,
                "scenario_definition_builder_name": self.builder_name,
                "scenario_status": normalized_status.value,
                "scenario_status_reason": normalized_reason,
                "observe_only": scenario.observe_only,
                "safety_first": scenario.safety_first,
                "definition_only": scenario.definition_only,
                "dry_run_eligible": scenario.dry_run_eligible,
                "real_click_eligible": scenario.real_click_eligible,
                "step_ids": tuple(step.step_id for step in normalized_steps),
                "step_statuses": tuple(
                    (step.step_id, step.status.value) for step in normalized_steps
                ),
                "dry_run_only_step_ids": dry_run_only_step_ids,
                "real_click_eligible_step_ids": real_click_eligible_step_ids,
                "incomplete_step_ids": tuple(sorted(set(incomplete_step_ids))),
                "invalid_step_ids": tuple(sorted(set(invalid_step_ids))),
                "duplicate_step_ids": duplicate_step_ids,
                "scenario_flag_mismatch_step_ids": scenario_flag_mismatch_step_ids,
                "missing_action_type_step_ids": _diagnostic_step_ids(
                    normalized_step_artifacts,
                    "missing_action_type",
                ),
                "missing_candidate_constraint_step_ids": _diagnostic_step_ids(
                    normalized_step_artifacts,
                    "missing_candidate_constraint",
                ),
                "missing_expected_outcome_step_ids": _diagnostic_step_ids(
                    normalized_step_artifacts,
                    "missing_expected_outcome",
                ),
                "missing_precondition_step_ids": _diagnostic_step_ids(
                    normalized_step_artifacts,
                    "missing_preconditions",
                ),
                "missing_target_validation_step_ids": _diagnostic_step_ids(
                    normalized_step_artifacts,
                    "missing_target_validation",
                ),
                "missing_safety_gate_step_ids": _diagnostic_step_ids(
                    normalized_step_artifacts,
                    "missing_safety_gates",
                ),
                "unsupported_real_click_step_ids": _diagnostic_step_ids(
                    normalized_step_artifacts,
                    "unsupported_real_click",
                ),
                "real_click_safety_mismatch_step_ids": _diagnostic_step_ids(
                    normalized_step_artifacts,
                    "real_click_safety_mismatch",
                ),
            },
        )

        definition_view = ScenarioDefinitionView(
            scenario_id=normalized_scenario.scenario_id,
            title=normalized_scenario.title,
            summary=normalized_scenario.summary,
            status=normalized_scenario.status,
            step_count=len(normalized_scenario.steps),
            defined_step_count=sum(
                step.status is ScenarioDefinitionStatus.defined
                for step in normalized_scenario.steps
            ),
            incomplete_step_count=sum(
                step.status is ScenarioDefinitionStatus.incomplete
                for step in normalized_scenario.steps
            ),
            invalid_step_count=sum(
                step.status is ScenarioDefinitionStatus.invalid
                for step in normalized_scenario.steps
            ),
            dry_run_only_step_ids=dry_run_only_step_ids,
            real_click_eligible_step_ids=real_click_eligible_step_ids,
            signal_status=_signal_status(normalized_scenario),
            metadata={
                "observe_only": normalized_scenario.observe_only,
                "safety_first": normalized_scenario.safety_first,
                "definition_only": normalized_scenario.definition_only,
                "step_ids": tuple(step.step_id for step in normalized_scenario.steps),
                "duplicate_step_ids": duplicate_step_ids,
                "incomplete_step_ids": tuple(sorted(set(incomplete_step_ids))),
                "invalid_step_ids": tuple(sorted(set(invalid_step_ids))),
                "unsupported_real_click_step_ids": _diagnostic_step_ids(
                    normalized_step_artifacts,
                    "unsupported_real_click",
                ),
                "scenario_flag_mismatch_step_ids": scenario_flag_mismatch_step_ids,
            },
        )
        return normalized_scenario, definition_view

    def _normalize_step(
        self,
        step: ScenarioStepDefinition,
        *,
        scenario: ScenarioDefinition,
    ) -> _StepArtifacts:
        incomplete_reasons: list[str] = []
        invalid_reasons: list[str] = []
        diagnostics: set[str] = set()

        if not step.step_id:
            incomplete_reasons.append("Scenario step identifier is required.")
            diagnostics.add("missing_step_id")
        if not step.summary:
            incomplete_reasons.append("Scenario step summary is required.")
            diagnostics.add("missing_summary")
        if not step.action_type:
            incomplete_reasons.append("Scenario step action type is required.")
            diagnostics.add("missing_action_type")

        if (
            not step.candidate_constraint.candidate_classes
            and not step.candidate_constraint.allowed_candidate_ids
        ):
            incomplete_reasons.append(
                "Scenario steps must declare candidate selection constraints."
            )
            diagnostics.add("missing_candidate_constraint")

        if step.expected_outcome is None or _expectation_is_empty(step.expected_outcome):
            incomplete_reasons.append(
                "Scenario steps must declare a non-empty expected semantic outcome."
            )
            diagnostics.add("missing_expected_outcome")

        if (
            step.safety_requirement.require_preconditions
            and not step.precondition_requirements
        ):
            incomplete_reasons.append(
                "Scenario steps must include explicit precondition requirements."
            )
            diagnostics.add("missing_preconditions")
        if (
            step.safety_requirement.require_target_validation
            and not step.target_validation_requirements
        ):
            incomplete_reasons.append(
                "Scenario steps must include explicit target validation requirements."
            )
            diagnostics.add("missing_target_validation")
        if (
            step.safety_requirement.require_explicit_safety_gates
            and not step.safety_gating_requirements
        ):
            incomplete_reasons.append(
                "Scenario steps must include explicit safety-gating requirements."
            )
            diagnostics.add("missing_safety_gates")

        if not step.observe_only:
            invalid_reasons.append("Scenario steps in Phase 6A must remain observe-only.")
            diagnostics.add("unsafe_step_flags")
        if not step.safety_first:
            invalid_reasons.append("Scenario steps in Phase 6A must remain safety-first.")
            diagnostics.add("unsafe_step_flags")
        if not step.definition_only:
            invalid_reasons.append("Scenario steps in Phase 6A must remain definition-only.")
            diagnostics.add("unsafe_step_flags")
        if (
            step.safety_requirement.require_observe_only_inputs
            and not step.observe_only
        ):
            invalid_reasons.append(
                "Observe-only inputs are required when step safety requirements demand them."
            )
            diagnostics.add("unsafe_step_flags")
        if (
            step.safety_requirement.require_definition_only
            and not step.definition_only
        ):
            invalid_reasons.append(
                "Definition-only semantics are required when step safety requirements demand them."
            )
            diagnostics.add("unsafe_step_flags")

        if (
            step.execution_eligibility
            is ScenarioExecutionEligibility.real_click_eligible
        ):
            self._validate_real_click_eligibility(
                step,
                scenario=scenario,
                incomplete_reasons=incomplete_reasons,
                invalid_reasons=invalid_reasons,
                diagnostics=diagnostics,
            )

        status = _step_status(
            incomplete_reasons=tuple(incomplete_reasons),
            invalid_reasons=tuple(invalid_reasons),
        )
        status_reason = (
            invalid_reasons[0]
            if invalid_reasons
            else (incomplete_reasons[0] if incomplete_reasons else None)
        )
        normalized_step = replace(
            step,
            status=status,
            status_reason=status_reason,
            metadata={
                **dict(step.metadata),
                "scenario_definition_builder_name": self.builder_name,
                "step_status": status.value,
                "step_status_reason": status_reason,
                "execution_eligibility": step.execution_eligibility.value,
                "candidate_classes": tuple(
                    candidate_class.value
                    for candidate_class in step.candidate_constraint.candidate_classes
                ),
                "allowed_candidate_ids": step.candidate_constraint.allowed_candidate_ids,
                "minimum_score": step.candidate_constraint.minimum_score,
                "maximum_candidate_rank": step.candidate_constraint.maximum_candidate_rank,
                "allow_real_click_prototype": (
                    step.candidate_constraint.allow_real_click_prototype
                ),
                "observe_only": step.observe_only,
                "safety_first": step.safety_first,
                "definition_only": step.definition_only,
                "validation_incomplete_reasons": tuple(incomplete_reasons),
                "validation_invalid_reasons": tuple(invalid_reasons),
                "diagnostic_codes": tuple(sorted(diagnostics)),
            },
        )
        return _StepArtifacts(
            step=normalized_step,
            incomplete_reasons=tuple(incomplete_reasons),
            invalid_reasons=tuple(invalid_reasons),
            diagnostics=frozenset(diagnostics),
        )

    def _validate_real_click_eligibility(
        self,
        step: ScenarioStepDefinition,
        *,
        scenario: ScenarioDefinition,
        incomplete_reasons: list[str],
        invalid_reasons: list[str],
        diagnostics: set[str],
    ) -> None:
        if not scenario.real_click_eligible:
            invalid_reasons.append(
                "Real-click-eligible steps require a scenario-level real_click_eligible flag."
            )
            diagnostics.add("scenario_flag_mismatch")
        if step.action_type and step.action_type != "candidate_select":
            invalid_reasons.append(
                "The current real-click prototype only supports candidate_select steps."
            )
            diagnostics.add("unsupported_real_click")

        candidate_classes = step.candidate_constraint.candidate_classes
        if not step.candidate_constraint.allow_real_click_prototype:
            incomplete_reasons.append(
                "Real-click-eligible steps must explicitly allow the real click prototype."
            )
            diagnostics.add("real_click_allow_flag_missing")
        if not candidate_classes:
            incomplete_reasons.append(
                "Real-click-eligible steps must explicitly constrain candidate classes."
            )
            diagnostics.add("real_click_class_constraint_missing")
        elif any(
            candidate_class not in _REAL_CLICK_ALLOWED_CLASSES
            for candidate_class in candidate_classes
        ):
            invalid_reasons.append(
                "The current real-click prototype only supports button-like candidates."
            )
            diagnostics.add("unsupported_real_click")

        if step.candidate_constraint.minimum_score is None:
            incomplete_reasons.append(
                "Real-click-eligible steps must declare an explicit minimum candidate score."
            )
            diagnostics.add("real_click_score_missing")
        elif step.candidate_constraint.minimum_score < _REAL_CLICK_MINIMUM_SCORE:
            invalid_reasons.append(
                "Real-click-eligible steps must use a minimum candidate score of at least 0.9."
            )
            diagnostics.add("unsupported_real_click")

        if step.candidate_constraint.maximum_candidate_rank is None:
            incomplete_reasons.append(
                "Real-click-eligible steps must declare an explicit maximum candidate rank."
            )
            diagnostics.add("real_click_rank_missing")
        elif step.candidate_constraint.maximum_candidate_rank > _REAL_CLICK_MAXIMUM_RANK:
            invalid_reasons.append(
                "Real-click-eligible steps must stay within the top-five candidate prototype window."
            )
            diagnostics.add("unsupported_real_click")

        if not step.safety_requirement.require_target_validation:
            invalid_reasons.append(
                "Real-click-eligible steps must require target validation."
            )
            diagnostics.add("real_click_safety_mismatch")
        if not step.safety_requirement.require_explicit_safety_gates:
            invalid_reasons.append(
                "Real-click-eligible steps must require explicit safety gates."
            )
            diagnostics.add("real_click_safety_mismatch")
        if not step.safety_requirement.require_protected_context_clear:
            invalid_reasons.append(
                "Real-click-eligible steps must require protected-context clearance."
            )
            diagnostics.add("real_click_safety_mismatch")
        if not step.safety_requirement.require_policy_clearance_for_real_click:
            invalid_reasons.append(
                "Real-click-eligible steps must require policy clearance."
            )
            diagnostics.add("real_click_safety_mismatch")


def _expectation_is_empty(expectation: object) -> bool:
    if not hasattr(expectation, "required_candidate_ids"):
        return True
    return (
        not expectation.required_candidate_ids
        and not expectation.forbidden_candidate_ids
        and not expectation.required_node_ids
        and not expectation.expected_outcomes
    )


def _step_status(
    *,
    incomplete_reasons: tuple[str, ...],
    invalid_reasons: tuple[str, ...],
) -> ScenarioDefinitionStatus:
    if invalid_reasons:
        return ScenarioDefinitionStatus.invalid
    if incomplete_reasons:
        return ScenarioDefinitionStatus.incomplete
    return ScenarioDefinitionStatus.defined


def _scenario_status(
    *,
    scenario_incomplete_reasons: list[str],
    scenario_invalid_reasons: list[str],
    steps: tuple[ScenarioStepDefinition, ...],
) -> ScenarioDefinitionStatus:
    if scenario_invalid_reasons or any(
        step.status is ScenarioDefinitionStatus.invalid for step in steps
    ):
        return ScenarioDefinitionStatus.invalid
    if scenario_incomplete_reasons or any(
        step.status is ScenarioDefinitionStatus.incomplete for step in steps
    ):
        return ScenarioDefinitionStatus.incomplete
    return ScenarioDefinitionStatus.defined


def _primary_reason(
    *,
    invalid_reasons: list[str],
    incomplete_reasons: list[str],
    steps: tuple[ScenarioStepDefinition, ...],
) -> str | None:
    if invalid_reasons:
        return invalid_reasons[0]
    if incomplete_reasons:
        return incomplete_reasons[0]
    for step in steps:
        if step.status_reason:
            return step.status_reason
    return None


def _signal_status(scenario: ScenarioDefinition) -> str:
    if not scenario.steps:
        return "absent"
    if scenario.status is ScenarioDefinitionStatus.defined:
        return "available"
    return "partial"


def _diagnostic_step_ids(
    artifacts: tuple[_StepArtifacts, ...],
    code: str,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            artifact.step.step_id
            for artifact in artifacts
            if artifact.step.step_id and code in artifact.diagnostics
        )
    )
