"""Explicit final-boundary guard between structured AI artifacts and tool surfaces."""

from __future__ import annotations

from typing import Mapping

from universal_visual_os_agent.ai_boundary.models import (
    ValidatedLocalVisualResolverOutput,
    ValidatedPlannerActionSuggestion,
)
from universal_visual_os_agent.config.modes import AgentMode
from universal_visual_os_agent.config.models import RunConfig
from universal_visual_os_agent.geometry.models import (
    NormalizedBBox,
    NormalizedPoint,
    ScreenBBox,
    ScreenMetrics,
    ScreenPoint,
    VirtualDesktopMetrics,
)
from universal_visual_os_agent.geometry.transforms import (
    bbox_normalized_to_screen,
    normalized_to_screen,
)
from universal_visual_os_agent.policy.models import PolicyDecision, PolicyVerdict
from universal_visual_os_agent.semantics.state import SemanticCandidate, SemanticStateSnapshot

from .dry_run_models import DryRunActionDisposition, DryRunActionEvaluation
from .models import (
    ActionIntent,
    ActionIntentStatus,
    ActionRequirementStatus,
)
from .tool_boundary_models import (
    ActionToolBoundaryAssessment,
    ActionToolBoundaryBlockCode,
    ActionToolBoundaryCheckOutcome,
    ActionToolBoundaryEvaluationResult,
    ActionToolBoundarySourceKind,
    ActionToolBoundaryStatus,
    ActionToolBoundarySurface,
)


class ObserveOnlyActionToolBoundaryGuard:
    """Centralized last-mile safety checks for action-tool surfaces."""

    guard_name = "ObserveOnlyActionToolBoundaryGuard"

    def __init__(
        self,
        *,
        supported_dry_run_action_types: frozenset[str] | None = None,
        allowed_safe_click_candidate_classes: frozenset[str] | None = None,
        minimum_safe_click_confidence: float = 0.9,
        maximum_safe_click_candidate_rank: int = 5,
    ) -> None:
        self._supported_dry_run_action_types = (
            frozenset({"candidate_select"})
            if supported_dry_run_action_types is None
            else supported_dry_run_action_types
        )
        self._allowed_safe_click_candidate_classes = (
            frozenset({"button_like"})
            if allowed_safe_click_candidate_classes is None
            else allowed_safe_click_candidate_classes
        )
        self._minimum_safe_click_confidence = minimum_safe_click_confidence
        self._maximum_safe_click_candidate_rank = maximum_safe_click_candidate_rank

    def evaluate_planner_action_suggestion_for_surface(
        self,
        suggestion: ValidatedPlannerActionSuggestion,
        *,
        surface: ActionToolBoundarySurface,
    ) -> ActionToolBoundaryEvaluationResult:
        try:
            assessment = self._direct_ai_output_assessment(
                surface=surface,
                source_kind=ActionToolBoundarySourceKind.planner_action_suggestion,
                action_type=suggestion.action_type.value,
                candidate_id=suggestion.candidate_id,
                metadata=suggestion.metadata,
            )
        except Exception as exc:  # noqa: BLE001 - boundary must remain failure-safe
            return ActionToolBoundaryEvaluationResult.failure(
                guard_name=self.guard_name,
                error_code="action_tool_boundary_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return ActionToolBoundaryEvaluationResult.ok(
            guard_name=self.guard_name,
            assessment=assessment,
            details={
                "surface": surface.value,
                "source_kind": ActionToolBoundarySourceKind.planner_action_suggestion.value,
            },
        )

    def evaluate_resolver_output_for_surface(
        self,
        output: ValidatedLocalVisualResolverOutput,
        *,
        surface: ActionToolBoundarySurface,
    ) -> ActionToolBoundaryEvaluationResult:
        try:
            assessment = self._direct_ai_output_assessment(
                surface=surface,
                source_kind=ActionToolBoundarySourceKind.resolver_output,
                action_type=output.action_type.value,
                candidate_id=output.candidate_id,
                metadata=output.metadata,
            )
        except Exception as exc:  # noqa: BLE001 - boundary must remain failure-safe
            return ActionToolBoundaryEvaluationResult.failure(
                guard_name=self.guard_name,
                error_code="action_tool_boundary_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return ActionToolBoundaryEvaluationResult.ok(
            guard_name=self.guard_name,
            assessment=assessment,
            details={
                "surface": surface.value,
                "source_kind": ActionToolBoundarySourceKind.resolver_output.value,
            },
        )

    def evaluate_intent_for_dry_run(
        self,
        intent: ActionIntent,
        *,
        snapshot: SemanticStateSnapshot | None = None,
    ) -> ActionToolBoundaryEvaluationResult:
        try:
            assessment = self._intent_assessment_for_dry_run(intent, snapshot=snapshot)
        except Exception as exc:  # noqa: BLE001 - boundary must remain failure-safe
            return ActionToolBoundaryEvaluationResult.failure(
                guard_name=self.guard_name,
                error_code="action_tool_boundary_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return ActionToolBoundaryEvaluationResult.ok(
            guard_name=self.guard_name,
            assessment=assessment,
            details={
                "surface": ActionToolBoundarySurface.dry_run_engine.value,
                "source_kind": ActionToolBoundarySourceKind.action_intent.value,
            },
        )

    def evaluate_intent_for_safe_click(
        self,
        intent: ActionIntent,
        *,
        config: RunConfig,
        target_screen_point: ScreenPoint | None,
        dry_run_evaluation: DryRunActionEvaluation,
        policy_decision: PolicyDecision | None,
        metrics: VirtualDesktopMetrics | None = None,
        snapshot: SemanticStateSnapshot | None = None,
        execute: bool = False,
        click_transport_available: bool = False,
    ) -> ActionToolBoundaryEvaluationResult:
        try:
            assessment = self._intent_assessment_for_safe_click(
                intent,
                config=config,
                target_screen_point=target_screen_point,
                dry_run_evaluation=dry_run_evaluation,
                policy_decision=policy_decision,
                metrics=metrics,
                snapshot=snapshot,
                execute=execute,
                click_transport_available=click_transport_available,
            )
        except Exception as exc:  # noqa: BLE001 - boundary must remain failure-safe
            return ActionToolBoundaryEvaluationResult.failure(
                guard_name=self.guard_name,
                error_code="action_tool_boundary_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return ActionToolBoundaryEvaluationResult.ok(
            guard_name=self.guard_name,
            assessment=assessment,
            details={
                "surface": ActionToolBoundarySurface.safe_click_prototype.value,
                "source_kind": ActionToolBoundarySourceKind.action_intent.value,
                "execute_requested": execute,
            },
        )

    def _direct_ai_output_assessment(
        self,
        *,
        surface: ActionToolBoundarySurface,
        source_kind: ActionToolBoundarySourceKind,
        action_type: str,
        candidate_id: str | None,
        metadata: Mapping[str, object],
    ) -> ActionToolBoundaryAssessment:
        outcomes = (
            _check(
                check_id="ai_boundary_validation_present",
                summary="Structured AI output must first pass AI-boundary validation.",
                condition=metadata.get("ai_boundary_validated") is True,
                blocked_reason="Structured AI output reached the tool boundary without AI-boundary validation.",
                satisfied_reason="Structured AI output preserved AI-boundary validation metadata.",
                block_code=ActionToolBoundaryBlockCode.ai_boundary_validation_missing,
                metadata={"ai_boundary_validated": metadata.get("ai_boundary_validated")},
            ),
            _check(
                check_id="action_intent_binding_required",
                summary="Structured AI output must be rebound into an action-intent scaffold before any tool surface.",
                condition=False,
                blocked_reason=(
                    "Structured AI output cannot cross the final tool boundary directly; "
                    "an observe-only action-intent binding is required first."
                ),
                satisfied_reason="",
                block_code=ActionToolBoundaryBlockCode.direct_ai_output_requires_binding,
                metadata={
                    "tool_boundary_binding_required": True,
                    "tool_boundary_source_kind": source_kind.value,
                },
            ),
        )
        return _assessment(
            surface=surface,
            source_kind=source_kind,
            action_type=action_type,
            candidate_id=candidate_id,
            check_outcomes=outcomes,
            metadata={
                "tool_boundary_binding_required": True,
                "direct_execution_forbidden": True,
            },
        )

    def _intent_assessment_for_dry_run(
        self,
        intent: ActionIntent,
        *,
        snapshot: SemanticStateSnapshot | None,
    ) -> ActionToolBoundaryAssessment:
        common_outcomes = self._common_intent_outcomes(intent, snapshot=snapshot)
        return _assessment(
            surface=ActionToolBoundarySurface.dry_run_engine,
            source_kind=ActionToolBoundarySourceKind.action_intent,
            action_type=intent.action_type,
            candidate_id=intent.candidate_id,
            check_outcomes=common_outcomes,
            metadata={
                "evaluated_with_snapshot": snapshot is not None,
                "evaluation_snapshot_id": None if snapshot is None else snapshot.snapshot_id,
            },
        )

    def _intent_assessment_for_safe_click(
        self,
        intent: ActionIntent,
        *,
        config: RunConfig,
        target_screen_point: ScreenPoint | None,
        dry_run_evaluation: DryRunActionEvaluation,
        policy_decision: PolicyDecision | None,
        metrics: VirtualDesktopMetrics | None,
        snapshot: SemanticStateSnapshot | None,
        execute: bool,
        click_transport_available: bool,
    ) -> ActionToolBoundaryAssessment:
        candidate_class = _coerce_optional_string(intent.metadata.get("candidate_class"))
        completeness_status = _coerce_optional_string(
            intent.metadata.get("candidate_exposure_completeness_status")
        )
        eligible_class = candidate_class in self._allowed_safe_click_candidate_classes
        eligible_rank = (
            intent.candidate_rank is not None
            and intent.candidate_rank <= self._maximum_safe_click_candidate_rank
        )
        eligible_score = (
            intent.candidate_score is not None
            and intent.candidate_score >= self._minimum_safe_click_confidence
        )
        real_click_mode_enabled = _real_click_mode_enabled(config)
        policy_allowed = (
            policy_decision is not None and policy_decision.verdict is PolicyVerdict.allow
        )
        snapshot_candidate = _lookup_snapshot_candidate(snapshot, intent.candidate_id)
        common_outcomes = self._common_intent_outcomes(intent, snapshot=snapshot)
        blocked_common_outcome = next(
            (
                outcome
                for outcome in common_outcomes
                if outcome.status is ActionRequirementStatus.blocked
            ),
            None,
        )
        planned_checks: list[tuple[str, ActionToolBoundaryCheckOutcome]] = [
            (
                "real_click_mode_enabled",
                _check(
                    check_id="real_click_mode_enabled",
                    summary="Real click mode requires safe_action_mode plus allow_live_input=True.",
                    condition=real_click_mode_enabled,
                    blocked_reason="RunConfig did not explicitly enable the real click prototype.",
                    satisfied_reason="Real click mode is explicitly enabled.",
                    block_code=ActionToolBoundaryBlockCode.real_click_mode_disabled,
                    metadata={"mode": config.mode.value, "allow_live_input": config.allow_live_input},
                ),
            ),
            (
                "explicit_candidate_allowlist",
                _check(
                    check_id="explicit_candidate_allowlist",
                    summary="Only top-ranked button-like candidates are explicitly eligible.",
                    condition=eligible_class and eligible_rank,
                    blocked_reason="Candidate did not match the explicit prototype allowlist.",
                    satisfied_reason="Candidate matched the explicit prototype allowlist.",
                    block_code=(
                        ActionToolBoundaryBlockCode.candidate_class_ineligible
                        if not eligible_class
                        else ActionToolBoundaryBlockCode.candidate_rank_ineligible
                    ),
                    metadata={
                        "candidate_class": candidate_class,
                        "candidate_rank": intent.candidate_rank,
                        "allowed_candidate_classes": tuple(
                            sorted(self._allowed_safe_click_candidate_classes)
                        ),
                        "maximum_candidate_rank": self._maximum_safe_click_candidate_rank,
                    },
                ),
            ),
            (
                "candidate_complete",
                _check(
                    check_id="candidate_complete",
                    summary="Candidate must be scaffolded and have complete exposure metadata.",
                    condition=(
                        intent.status is ActionIntentStatus.scaffolded
                        and completeness_status == "available"
                    ),
                    blocked_reason="Candidate metadata is incomplete for the click prototype.",
                    satisfied_reason="Candidate metadata is complete for the click prototype.",
                    block_code=ActionToolBoundaryBlockCode.candidate_metadata_incomplete,
                    metadata={
                        "intent_status": intent.status.value,
                        "candidate_exposure_completeness_status": completeness_status,
                    },
                ),
            ),
            (
                "candidate_score_threshold",
                _check(
                    check_id="candidate_score_threshold",
                    summary="Candidate confidence must meet the real-click threshold.",
                    condition=eligible_score,
                    blocked_reason="Candidate confidence was too low for the real-click prototype.",
                    satisfied_reason="Candidate confidence met the real-click threshold.",
                    block_code=ActionToolBoundaryBlockCode.candidate_score_ineligible,
                    metadata={
                        "candidate_score": intent.candidate_score,
                        "minimum_confidence": self._minimum_safe_click_confidence,
                    },
                ),
            ),
            (
                "dry_run_would_execute",
                _check(
                    check_id="dry_run_would_execute",
                    summary="Dry-run evaluation must conclude that the intent would execute safely.",
                    condition=(
                        dry_run_evaluation.disposition
                        is DryRunActionDisposition.would_execute
                    ),
                    blocked_reason=(
                        "Dry-run evaluation blocked the intent: "
                        f"{dry_run_evaluation.summary}"
                    ),
                    satisfied_reason="Dry-run evaluation allowed the intent.",
                    block_code=ActionToolBoundaryBlockCode.dry_run_not_accepted,
                    metadata={"dry_run_disposition": dry_run_evaluation.disposition.value},
                ),
            ),
            (
                "target_screen_point_available",
                _check(
                    check_id="target_screen_point_available",
                    summary="A validated screen click target must be available.",
                    condition=target_screen_point is not None,
                    blocked_reason="No validated screen click target was available.",
                    satisfied_reason=(
                        "A screen click target was derived from the normalized intent target."
                    ),
                    block_code=ActionToolBoundaryBlockCode.missing_screen_target,
                    metadata={
                        "target_screen_point": (
                            None
                            if target_screen_point is None
                            else (target_screen_point.x_px, target_screen_point.y_px)
                        ),
                    },
                ),
            ),
            (
                "screen_target_cross_validated",
                _screen_target_cross_validation_check(
                    intent=intent,
                    snapshot_candidate=snapshot_candidate,
                    target_screen_point=target_screen_point,
                    metrics=metrics,
                ),
            ),
            (
                "policy_allow",
                _check(
                    check_id="policy_allow",
                    summary="Policy must explicitly allow the live click attempt.",
                    condition=policy_allowed,
                    blocked_reason=(
                        "Policy blocked the live click attempt: "
                        f"{policy_decision.reason if policy_decision is not None else 'no policy decision'}"
                    ),
                    satisfied_reason="Policy allowed the live click attempt.",
                    block_code=ActionToolBoundaryBlockCode.policy_denied,
                    metadata={
                        "policy_verdict": (
                            None if policy_decision is None else policy_decision.verdict.value
                        ),
                        "policy_reason": (
                            None if policy_decision is None else policy_decision.reason
                        ),
                    },
                    pending=not real_click_mode_enabled,
                ),
            ),
            (
                "click_transport_available",
                _check(
                    check_id="click_transport_available",
                    summary="A real click transport must be present when execution is requested.",
                    condition=(not execute or click_transport_available),
                    blocked_reason="Execution was requested without a real click transport.",
                    satisfied_reason="Click transport is available for the requested path.",
                    block_code=ActionToolBoundaryBlockCode.click_transport_unavailable,
                    metadata={"execute_requested": execute},
                ),
            ),
        ]

        if blocked_common_outcome is not None:
            return _assessment(
                surface=ActionToolBoundarySurface.safe_click_prototype,
                source_kind=ActionToolBoundarySourceKind.action_intent,
                action_type=intent.action_type,
                candidate_id=intent.candidate_id,
                check_outcomes=common_outcomes,
                metadata={
                    "evaluated_with_snapshot": snapshot is not None,
                    "evaluation_snapshot_id": None if snapshot is None else snapshot.snapshot_id,
                    "execute_requested": execute,
                    "short_circuit_check_id": blocked_common_outcome.check_id,
                    "skipped_check_ids": tuple(check_id for check_id, _ in planned_checks),
                },
            )

        outcomes = list(common_outcomes)
        for index, (check_id, outcome) in enumerate(planned_checks):
            outcomes.append(outcome)
            if outcome.status is ActionRequirementStatus.blocked:
                return _assessment(
                    surface=ActionToolBoundarySurface.safe_click_prototype,
                    source_kind=ActionToolBoundarySourceKind.action_intent,
                    action_type=intent.action_type,
                    candidate_id=intent.candidate_id,
                    check_outcomes=tuple(outcomes),
                    metadata={
                        "evaluated_with_snapshot": snapshot is not None,
                        "evaluation_snapshot_id": None if snapshot is None else snapshot.snapshot_id,
                        "execute_requested": execute,
                        "short_circuit_check_id": check_id,
                        "skipped_check_ids": tuple(
                            planned_check_id
                            for planned_check_id, _ in planned_checks[index + 1 :]
                        ),
                    },
                )

        return _assessment(
            surface=ActionToolBoundarySurface.safe_click_prototype,
            source_kind=ActionToolBoundarySourceKind.action_intent,
            action_type=intent.action_type,
            candidate_id=intent.candidate_id,
            check_outcomes=tuple(outcomes),
            metadata={
                "evaluated_with_snapshot": snapshot is not None,
                "evaluation_snapshot_id": None if snapshot is None else snapshot.snapshot_id,
                "execute_requested": execute,
                "short_circuit_check_id": None,
                "skipped_check_ids": (),
            },
        )

    def _common_intent_outcomes(
        self,
        intent: ActionIntent,
        *,
        snapshot: SemanticStateSnapshot | None,
    ) -> tuple[ActionToolBoundaryCheckOutcome, ...]:
        candidate_required = intent.action_type == "candidate_select"
        snapshot_candidate = _lookup_snapshot_candidate(snapshot, intent.candidate_id)
        source_candidate_id = _coerce_optional_string(intent.metadata.get("source_candidate_id"))

        return (
            _check(
                check_id="supported_action_type",
                summary="Only candidate_select intents are supported by this boundary.",
                condition=intent.action_type in self._supported_dry_run_action_types,
                blocked_reason="Intent action type is outside the supported tool boundary.",
                satisfied_reason="Intent action type is supported.",
                block_code=ActionToolBoundaryBlockCode.unsupported_action_type,
                metadata={"action_type": intent.action_type},
            ),
            _check(
                check_id="intent_scaffold_origin_present",
                summary="Intent must originate from the observe-only action-intent scaffold.",
                condition=intent.metadata.get("action_intent_scaffolded") is True,
                blocked_reason="Intent did not preserve action-intent scaffold provenance.",
                satisfied_reason="Intent preserved action-intent scaffold provenance.",
                block_code=ActionToolBoundaryBlockCode.intent_scaffold_origin_missing,
                metadata={
                    "action_intent_scaffolded": intent.metadata.get("action_intent_scaffolded"),
                },
            ),
            _check(
                check_id="observe_only_origin_confirmed",
                summary="Intent must preserve observe-only non-executing provenance.",
                condition=intent.observe_only_source and intent.metadata.get("observe_only") is True,
                blocked_reason="Intent violated observe-only provenance at the final boundary.",
                satisfied_reason="Intent preserved observe-only provenance.",
                block_code=ActionToolBoundaryBlockCode.observe_only_contract_violation,
                metadata={
                    "observe_only_source": intent.observe_only_source,
                    "observe_only_metadata": intent.metadata.get("observe_only"),
                },
            ),
            _check(
                check_id="dry_run_only_enforced",
                summary="Intent must remain dry-run-only and non-executing at the final boundary.",
                condition=(
                    intent.dry_run_only
                    and not intent.executable
                    and intent.metadata.get("non_executing") is True
                ),
                blocked_reason="Intent violated the dry-run-only non-executing safety contract.",
                satisfied_reason="Intent preserved dry-run-only non-executing safety metadata.",
                block_code=ActionToolBoundaryBlockCode.dry_run_contract_violation,
                metadata={
                    "dry_run_only": intent.dry_run_only,
                    "executable": intent.executable,
                    "non_executing": intent.metadata.get("non_executing"),
                },
            ),
            _check(
                check_id="candidate_id_present",
                summary="Candidate-select intents must carry a candidate identifier.",
                condition=(not candidate_required or bool(intent.candidate_id)),
                blocked_reason="Candidate-select intent was missing a candidate identifier.",
                satisfied_reason="Intent carried a candidate identifier.",
                block_code=ActionToolBoundaryBlockCode.missing_candidate_id,
                metadata={"candidate_id": intent.candidate_id},
                pending=not candidate_required,
            ),
            _check(
                check_id="candidate_binding_consistent",
                summary="Source candidate metadata must remain consistent with the bound intent candidate.",
                condition=(
                    source_candidate_id is None
                    or intent.candidate_id is None
                    or source_candidate_id == intent.candidate_id
                ),
                blocked_reason="Intent candidate binding no longer matched its scaffold source metadata.",
                satisfied_reason="Intent candidate binding remained consistent with scaffold metadata.",
                block_code=ActionToolBoundaryBlockCode.candidate_binding_mismatch,
                metadata={"source_candidate_id": source_candidate_id, "candidate_id": intent.candidate_id},
                pending=not candidate_required,
            ),
            _check(
                check_id="normalized_target_present",
                summary="Candidate-select intents must carry a normalized target point.",
                condition=(not candidate_required or intent.target is not None),
                blocked_reason="Candidate-select intent was missing a normalized target point.",
                satisfied_reason="Intent carried a normalized target point.",
                block_code=ActionToolBoundaryBlockCode.missing_normalized_target,
                metadata={"has_normalized_target": intent.target is not None},
                pending=not candidate_required,
            ),
            _check(
                check_id="snapshot_candidate_present",
                summary="When a snapshot is available, the bound candidate must still exist.",
                condition=snapshot_candidate is not None,
                blocked_reason="Snapshot did not contain the bound candidate anymore.",
                satisfied_reason="Snapshot still contained the bound candidate.",
                block_code=ActionToolBoundaryBlockCode.snapshot_candidate_missing,
                metadata={
                    "evaluation_snapshot_id": None if snapshot is None else snapshot.snapshot_id,
                    "candidate_id": intent.candidate_id,
                },
                pending=(snapshot is None or not candidate_required or intent.candidate_id is None),
            ),
            _check(
                check_id="target_candidate_binding",
                summary="Normalized target must remain inside the bound candidate bounds.",
                condition=(
                    snapshot_candidate is not None
                    and intent.target is not None
                    and _point_in_bounds(intent.target, snapshot_candidate.bounds)
                ),
                blocked_reason="Normalized target no longer matched the bound candidate geometry.",
                satisfied_reason="Normalized target remained inside the bound candidate geometry.",
                block_code=ActionToolBoundaryBlockCode.target_candidate_mismatch,
                metadata={
                    "candidate_id": intent.candidate_id,
                    "target": None if intent.target is None else {"x": intent.target.x, "y": intent.target.y},
                },
                pending=(
                    snapshot is None
                    or snapshot_candidate is None
                    or intent.target is None
                    or not candidate_required
                ),
            ),
        )


def _assessment(
    *,
    surface: ActionToolBoundarySurface,
    source_kind: ActionToolBoundarySourceKind,
    action_type: str | None,
    candidate_id: str | None,
    check_outcomes: tuple[ActionToolBoundaryCheckOutcome, ...],
    metadata: Mapping[str, object] | None = None,
) -> ActionToolBoundaryAssessment:
    blocked_checks = tuple(
        outcome for outcome in check_outcomes if outcome.status is ActionRequirementStatus.blocked
    )
    pending_check_ids = tuple(
        outcome.check_id
        for outcome in check_outcomes
        if outcome.status is ActionRequirementStatus.pending
    )
    blocked_check_ids = tuple(outcome.check_id for outcome in blocked_checks)
    status = (
        ActionToolBoundaryStatus.blocked
        if blocked_checks
        else ActionToolBoundaryStatus.allowed
    )
    summary = (
        "Final tool boundary blocked the requested surface."
        if blocked_checks
        else "Final tool boundary accepted the requested surface."
    )
    return ActionToolBoundaryAssessment(
        surface=surface,
        source_kind=source_kind,
        status=status,
        summary=summary,
        action_type=action_type,
        candidate_id=candidate_id,
        check_outcomes=check_outcomes,
        metadata={
            **({} if metadata is None else dict(metadata)),
            "blocked_check_ids": blocked_check_ids,
            "blocking_codes": tuple(
                code.value for code in (
                    outcome.block_code for outcome in blocked_checks
                )
                if code is not None
            ),
            "pending_check_ids": pending_check_ids,
        },
    )


def _check(
    *,
    check_id: str,
    summary: str,
    condition: bool,
    blocked_reason: str,
    satisfied_reason: str,
    block_code: ActionToolBoundaryBlockCode,
    metadata: Mapping[str, object],
    pending: bool = False,
) -> ActionToolBoundaryCheckOutcome:
    if pending:
        return ActionToolBoundaryCheckOutcome(
            check_id=check_id,
            summary=summary,
            status=ActionRequirementStatus.pending,
            reason=f"{summary} Pending additional context.",
            metadata=metadata,
        )
    if condition:
        return ActionToolBoundaryCheckOutcome(
            check_id=check_id,
            summary=summary,
            status=ActionRequirementStatus.satisfied,
            reason=satisfied_reason,
            metadata=metadata,
        )
    return ActionToolBoundaryCheckOutcome(
        check_id=check_id,
        summary=summary,
        status=ActionRequirementStatus.blocked,
        reason=blocked_reason,
        block_code=block_code,
        metadata=metadata,
    )


def _lookup_snapshot_candidate(
    snapshot: SemanticStateSnapshot | None,
    candidate_id: str | None,
) -> SemanticCandidate | None:
    if snapshot is None or candidate_id is None:
        return None
    return snapshot.get_candidate(candidate_id)


def _screen_target_cross_validation_check(
    *,
    intent: ActionIntent,
    snapshot_candidate: SemanticCandidate | None,
    target_screen_point: ScreenPoint | None,
    metrics: VirtualDesktopMetrics | None,
) -> ActionToolBoundaryCheckOutcome:
    pending = (
        intent.target is None
        or snapshot_candidate is None
        or target_screen_point is None
        or metrics is None
    )
    if pending:
        return _check(
            check_id="screen_target_cross_validated",
            summary=(
                "The late-bound screen target must still match the normalized target "
                "and candidate screen bounds."
            ),
            condition=False,
            blocked_reason=(
                "Late-bound screen target cross-validation could not be completed."
            ),
            satisfied_reason="",
            block_code=ActionToolBoundaryBlockCode.screen_target_cross_validation_failed,
            metadata={
                "target_screen_point": (
                    None
                    if target_screen_point is None
                    else (target_screen_point.x_px, target_screen_point.y_px)
                ),
                "metrics_available": metrics is not None,
                "snapshot_candidate_present": snapshot_candidate is not None,
                "has_normalized_target": intent.target is not None,
            },
            pending=True,
        )

    desktop_metrics = _virtual_desktop_screen_metrics(metrics)
    expected_screen_point = normalized_to_screen(intent.target, desktop_metrics)
    candidate_screen_bounds = bbox_normalized_to_screen(snapshot_candidate.bounds, desktop_metrics)
    point_matches_target = target_screen_point == expected_screen_point
    point_inside_candidate = _screen_point_in_bounds(
        target_screen_point,
        candidate_screen_bounds,
    )
    blocked_reason = (
        "Late-bound screen target no longer matched the normalized intent target."
        if not point_matches_target
        else "Late-bound screen target no longer fell within the bound candidate screen bounds."
    )
    metadata = {
        "target_screen_point": (target_screen_point.x_px, target_screen_point.y_px),
        "expected_screen_point": (expected_screen_point.x_px, expected_screen_point.y_px),
        "candidate_screen_bounds": {
            "left_px": candidate_screen_bounds.left_px,
            "top_px": candidate_screen_bounds.top_px,
            "width_px": candidate_screen_bounds.width_px,
            "height_px": candidate_screen_bounds.height_px,
        },
        "point_matches_normalized_target": point_matches_target,
        "point_inside_candidate_bounds": point_inside_candidate,
    }
    return _check(
        check_id="screen_target_cross_validated",
        summary=(
            "The late-bound screen target must still match the normalized target "
            "and candidate screen bounds."
        ),
        condition=point_matches_target and point_inside_candidate,
        blocked_reason=blocked_reason,
        satisfied_reason=(
            "Late-bound screen target matched the normalized target and current candidate bounds."
        ),
        block_code=ActionToolBoundaryBlockCode.screen_target_cross_validation_failed,
        metadata=metadata,
    )


def _point_in_bounds(point: NormalizedPoint, bounds: NormalizedBBox) -> bool:
    right = bounds.left + bounds.width
    bottom = bounds.top + bounds.height
    return bounds.left <= point.x <= right and bounds.top <= point.y <= bottom


def _screen_point_in_bounds(point: ScreenPoint, bounds: ScreenBBox) -> bool:
    return bounds.left_px <= point.x_px < bounds.right_px and bounds.top_px <= point.y_px < bounds.bottom_px


def _virtual_desktop_screen_metrics(metrics: VirtualDesktopMetrics) -> ScreenMetrics:
    bounds = metrics.bounds
    return ScreenMetrics(
        width_px=bounds.width_px,
        height_px=bounds.height_px,
        origin_x_px=bounds.left_px,
        origin_y_px=bounds.top_px,
        display_id="virtual_desktop",
        is_primary=True,
    )


def _real_click_mode_enabled(config: RunConfig) -> bool:
    return config.mode is AgentMode.safe_action_mode and config.allow_live_input


def _coerce_optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


__all__ = [
    "ObserveOnlyActionToolBoundaryGuard",
]
