"""Recovery, escalation, and HITL scaffolding for the safety-first runtime."""

from __future__ import annotations

from typing import Mapping

from universal_visual_os_agent.actions.tool_boundary_models import (
    ActionToolBoundaryAssessment,
    ActionToolBoundaryBlockCode,
    ActionToolBoundaryStatus,
)
from universal_visual_os_agent.ai_architecture.escalation_engine import (
    DeterministicEscalationDecision,
    DeterministicEscalationDisposition,
    DeterministicEscalationReason,
)
from universal_visual_os_agent.recovery.models import (
    HumanConfirmationStatus,
    RecoveryEscalationOutcome,
    RecoveryFailureOrigin,
    RecoveryHandlingDisposition,
    RecoveryHandlingPlan,
    RecoveryHint,
    RecoveryPlanningResult,
    RecoveryRetryability,
)
from universal_visual_os_agent.verification.models import (
    VerificationReasonCategory,
    VerificationResult,
    VerificationStatus,
)

_RETRYABLE_ESCALATION_REASONS = frozenset(
    {
        DeterministicEscalationReason.deterministic_binding_missing,
        DeterministicEscalationReason.deterministic_binding_partial,
        DeterministicEscalationReason.resolver_response_partial,
        DeterministicEscalationReason.planner_response_partial,
        DeterministicEscalationReason.incomplete_contract_conflict,
    }
)

_RETRYABLE_TOOL_BOUNDARY_CODES = frozenset(
    {
        ActionToolBoundaryBlockCode.ai_boundary_validation_missing,
        ActionToolBoundaryBlockCode.direct_ai_output_requires_binding,
        ActionToolBoundaryBlockCode.missing_candidate_id,
        ActionToolBoundaryBlockCode.missing_normalized_target,
        ActionToolBoundaryBlockCode.candidate_binding_mismatch,
        ActionToolBoundaryBlockCode.snapshot_candidate_missing,
        ActionToolBoundaryBlockCode.target_candidate_mismatch,
        ActionToolBoundaryBlockCode.candidate_metadata_incomplete,
        ActionToolBoundaryBlockCode.missing_screen_target,
        ActionToolBoundaryBlockCode.click_transport_unavailable,
    }
)

_NON_RETRYABLE_TOOL_BOUNDARY_CODES = frozenset(
    {
        ActionToolBoundaryBlockCode.unsupported_action_type,
        ActionToolBoundaryBlockCode.observe_only_contract_violation,
        ActionToolBoundaryBlockCode.dry_run_contract_violation,
        ActionToolBoundaryBlockCode.real_click_mode_disabled,
        ActionToolBoundaryBlockCode.candidate_class_ineligible,
        ActionToolBoundaryBlockCode.candidate_rank_ineligible,
        ActionToolBoundaryBlockCode.candidate_score_ineligible,
        ActionToolBoundaryBlockCode.dry_run_not_accepted,
        ActionToolBoundaryBlockCode.policy_denied,
    }
)

_RETRYABLE_VERIFICATION_CATEGORIES = frozenset(
    {
        VerificationReasonCategory.missing_input,
        VerificationReasonCategory.partial_input,
        VerificationReasonCategory.ambiguous_result,
    }
)


class ObserveOnlyRecoveryEscalationHitlPlanner:
    """Build structured recovery/escalation/HITL plans without executing anything."""

    planner_name = "ObserveOnlyRecoveryEscalationHitlPlanner"

    def plan_from_escalation_decision(
        self,
        decision: DeterministicEscalationDecision,
    ) -> RecoveryPlanningResult:
        try:
            recovery_plan = self._plan_from_escalation_decision(decision)
        except Exception as exc:  # noqa: BLE001 - recovery planning must remain failure-safe
            return RecoveryPlanningResult.failure(
                planner_name=self.planner_name,
                error_code="recovery_escalation_planning_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return RecoveryPlanningResult.ok(
            planner_name=self.planner_name,
            recovery_plan=recovery_plan,
            details={
                "source": "deterministic_escalation",
                "disposition": recovery_plan.disposition.value,
            },
        )

    def plan_from_tool_boundary_assessment(
        self,
        assessment: ActionToolBoundaryAssessment,
    ) -> RecoveryPlanningResult:
        try:
            recovery_plan = self._plan_from_tool_boundary_assessment(assessment)
        except Exception as exc:  # noqa: BLE001 - recovery planning must remain failure-safe
            return RecoveryPlanningResult.failure(
                planner_name=self.planner_name,
                error_code="recovery_tool_boundary_planning_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return RecoveryPlanningResult.ok(
            planner_name=self.planner_name,
            recovery_plan=recovery_plan,
            details={
                "source": "tool_boundary",
                "disposition": recovery_plan.disposition.value,
            },
        )

    def plan_from_verification_result(
        self,
        result: VerificationResult,
    ) -> RecoveryPlanningResult:
        try:
            recovery_plan = self._plan_from_verification_result(result)
        except Exception as exc:  # noqa: BLE001 - recovery planning must remain failure-safe
            return RecoveryPlanningResult.failure(
                planner_name=self.planner_name,
                error_code="recovery_verification_planning_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return RecoveryPlanningResult.ok(
            planner_name=self.planner_name,
            recovery_plan=recovery_plan,
            details={
                "source": "verification",
                "disposition": recovery_plan.disposition.value,
            },
        )

    def plan_for_human_confirmation(
        self,
        *,
        summary: str,
        failure_origin: RecoveryFailureOrigin,
        metadata: Mapping[str, object] | None = None,
    ) -> RecoveryPlanningResult:
        try:
            recovery_plan = self._awaiting_user_confirmation_plan(
                summary=summary,
                failure_origin=failure_origin,
                metadata={} if metadata is None else dict(metadata),
            )
        except Exception as exc:  # noqa: BLE001 - recovery planning must remain failure-safe
            return RecoveryPlanningResult.failure(
                planner_name=self.planner_name,
                error_code="recovery_hitl_planning_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return RecoveryPlanningResult.ok(
            planner_name=self.planner_name,
            recovery_plan=recovery_plan,
            details={
                "source": failure_origin.value,
                "disposition": recovery_plan.disposition.value,
            },
        )

    def _plan_from_escalation_decision(
        self,
        decision: DeterministicEscalationDecision,
    ) -> RecoveryHandlingPlan:
        if decision.disposition is DeterministicEscalationDisposition.deterministic_ok:
            return self._plan(
                failure_origin=RecoveryFailureOrigin.deterministic_escalation,
                disposition=RecoveryHandlingDisposition.no_recovery_needed,
                retryability=RecoveryRetryability.not_applicable,
                summary=decision.summary,
                hints=(),
                metadata=_plan_metadata(
                    {"escalation_reason_codes": tuple(code.value for code in decision.reason_codes)},
                    decision.metadata,
                ),
            )
        if decision.disposition is DeterministicEscalationDisposition.local_resolver_recommended:
            return self._plan(
                failure_origin=RecoveryFailureOrigin.deterministic_escalation,
                disposition=RecoveryHandlingDisposition.escalate,
                retryability=RecoveryRetryability.non_retryable,
                summary=decision.summary,
                escalation_outcome=RecoveryEscalationOutcome.local_resolver_recommended,
                hints=(
                    RecoveryHint(
                        hint_id="local_resolver_follow_up",
                        summary="Request local visual resolver input when that scaffold is available.",
                        next_expected_signal="local_visual_resolver_response",
                    ),
                ),
                metadata=_plan_metadata(
                    {"escalation_reason_codes": tuple(code.value for code in decision.reason_codes)},
                    decision.metadata,
                ),
            )
        if decision.disposition is DeterministicEscalationDisposition.cloud_planner_recommended:
            return self._plan(
                failure_origin=RecoveryFailureOrigin.deterministic_escalation,
                disposition=RecoveryHandlingDisposition.escalate,
                retryability=RecoveryRetryability.non_retryable,
                summary=decision.summary,
                escalation_outcome=RecoveryEscalationOutcome.cloud_planner_recommended,
                hints=(
                    RecoveryHint(
                        hint_id="cloud_planner_follow_up",
                        summary="Escalate to the structured cloud planner when that path is available.",
                        next_expected_signal="cloud_planner_response",
                    ),
                ),
                metadata=_plan_metadata(
                    {"escalation_reason_codes": tuple(code.value for code in decision.reason_codes)},
                    decision.metadata,
                ),
            )
        if decision.disposition is DeterministicEscalationDisposition.human_confirmation_required:
            return self._awaiting_user_confirmation_plan(
                summary=decision.summary,
                failure_origin=RecoveryFailureOrigin.deterministic_escalation,
                metadata=_plan_metadata(
                    {"escalation_reason_codes": tuple(code.value for code in decision.reason_codes)},
                    decision.metadata,
                ),
            )

        retryable = any(reason in _RETRYABLE_ESCALATION_REASONS for reason in decision.reason_codes)
        if retryable:
            return self._plan(
                failure_origin=RecoveryFailureOrigin.deterministic_escalation,
                disposition=RecoveryHandlingDisposition.retry,
                retryability=RecoveryRetryability.retryable,
                summary=decision.summary,
                escalation_outcome=RecoveryEscalationOutcome.blocked,
                hints=(
                    RecoveryHint(
                        hint_id="refresh_deterministic_context",
                        summary="Refresh deterministic candidate or AI contract inputs before retrying escalation.",
                        next_expected_signal="deterministic_context_refresh",
                    ),
                ),
                metadata=_plan_metadata(
                    {"escalation_reason_codes": tuple(code.value for code in decision.reason_codes)},
                    decision.metadata,
                ),
            )

        return self._plan(
            failure_origin=RecoveryFailureOrigin.deterministic_escalation,
            disposition=RecoveryHandlingDisposition.blocked,
            retryability=RecoveryRetryability.non_retryable,
            summary=decision.summary,
            escalation_outcome=RecoveryEscalationOutcome.blocked,
            hints=(
                RecoveryHint(
                    hint_id="manual_escalation_review",
                    summary="Review high-risk or conflicting escalation inputs before continuing.",
                    next_expected_signal="operator_review",
                ),
            ),
            metadata=_plan_metadata(
                {"escalation_reason_codes": tuple(code.value for code in decision.reason_codes)},
                decision.metadata,
            ),
        )

    def _plan_from_tool_boundary_assessment(
        self,
        assessment: ActionToolBoundaryAssessment,
    ) -> RecoveryHandlingPlan:
        if assessment.status is ActionToolBoundaryStatus.allowed:
            return self._plan(
                failure_origin=RecoveryFailureOrigin.tool_boundary,
                disposition=RecoveryHandlingDisposition.no_recovery_needed,
                retryability=RecoveryRetryability.not_applicable,
                summary=assessment.summary,
                hints=(),
                metadata=assessment.metadata,
            )

        blocking_codes = assessment.blocking_codes
        if any(code in _NON_RETRYABLE_TOOL_BOUNDARY_CODES for code in blocking_codes):
            return self._plan(
                failure_origin=RecoveryFailureOrigin.tool_boundary,
                disposition=RecoveryHandlingDisposition.blocked,
                retryability=RecoveryRetryability.non_retryable,
                summary=assessment.summary,
                escalation_outcome=RecoveryEscalationOutcome.blocked,
                hints=(
                    RecoveryHint(
                        hint_id="tool_boundary_manual_review",
                        summary="Review explicit boundary and safety gates before continuing.",
                        next_expected_signal="operator_review",
                    ),
                ),
                metadata=_plan_metadata(
                    {"tool_boundary_blocking_codes": tuple(code.value for code in blocking_codes)},
                    assessment.metadata,
                ),
            )
        if any(code in _RETRYABLE_TOOL_BOUNDARY_CODES for code in blocking_codes):
            return self._plan(
                failure_origin=RecoveryFailureOrigin.tool_boundary,
                disposition=RecoveryHandlingDisposition.retry,
                retryability=RecoveryRetryability.retryable,
                summary=assessment.summary,
                escalation_outcome=RecoveryEscalationOutcome.blocked,
                hints=(
                    RecoveryHint(
                        hint_id="refresh_tool_boundary_inputs",
                        summary="Refresh bound candidate, target, or boundary metadata before retrying.",
                        next_expected_signal="tool_boundary_refresh",
                    ),
                ),
                metadata=_plan_metadata(
                    {"tool_boundary_blocking_codes": tuple(code.value for code in blocking_codes)},
                    assessment.metadata,
                ),
            )

        return self._plan(
            failure_origin=RecoveryFailureOrigin.tool_boundary,
            disposition=RecoveryHandlingDisposition.blocked,
            retryability=RecoveryRetryability.non_retryable,
            summary=assessment.summary,
            escalation_outcome=RecoveryEscalationOutcome.blocked,
            hints=(
                RecoveryHint(
                    hint_id="tool_boundary_unknown_block",
                    summary="Review blocked tool-boundary checks before continuing.",
                    next_expected_signal="operator_review",
                ),
            ),
            metadata=_plan_metadata(
                {"tool_boundary_blocking_codes": tuple(code.value for code in blocking_codes)},
                assessment.metadata,
            ),
        )

    def _plan_from_verification_result(
        self,
        result: VerificationResult,
    ) -> RecoveryHandlingPlan:
        taxonomy_categories = () if result.taxonomy is None else result.taxonomy.categories
        if result.status is VerificationStatus.satisfied:
            return self._plan(
                failure_origin=RecoveryFailureOrigin.verification,
                disposition=RecoveryHandlingDisposition.no_recovery_needed,
                retryability=RecoveryRetryability.not_applicable,
                summary=result.summary,
                hints=(),
                metadata={"verification_status": result.status.value},
            )
        if (
            result.status is VerificationStatus.unknown
            or any(category in _RETRYABLE_VERIFICATION_CATEGORIES for category in taxonomy_categories)
        ):
            return self._plan(
                failure_origin=RecoveryFailureOrigin.verification,
                disposition=RecoveryHandlingDisposition.retry,
                retryability=RecoveryRetryability.retryable,
                summary=result.summary,
                hints=(
                    RecoveryHint(
                        hint_id="refresh_verification_inputs",
                        summary="Refresh before/after semantic evidence and rerun verification.",
                        next_expected_signal="verification_delta",
                    ),
                ),
                metadata={
                    "verification_status": result.status.value,
                    "verification_taxonomy_categories": tuple(
                        category.value for category in taxonomy_categories
                    ),
                },
            )
        return self._plan(
            failure_origin=RecoveryFailureOrigin.verification,
            disposition=RecoveryHandlingDisposition.aborted,
            retryability=RecoveryRetryability.non_retryable,
            summary=result.summary,
            hints=(
                RecoveryHint(
                    hint_id="review_verification_expectation",
                    summary="Review scenario expectations or accept a manual abort before retrying.",
                    next_expected_signal="operator_review",
                ),
            ),
            metadata={
                "verification_status": result.status.value,
                "verification_taxonomy_categories": tuple(
                    category.value for category in taxonomy_categories
                ),
            },
        )

    def _awaiting_user_confirmation_plan(
        self,
        *,
        summary: str,
        failure_origin: RecoveryFailureOrigin,
        metadata: Mapping[str, object],
    ) -> RecoveryHandlingPlan:
        return self._plan(
            failure_origin=failure_origin,
            disposition=RecoveryHandlingDisposition.await_user_confirmation,
            retryability=RecoveryRetryability.non_retryable,
            summary=summary,
            escalation_outcome=RecoveryEscalationOutcome.human_confirmation_required,
            human_confirmation_status=HumanConfirmationStatus.awaiting_user_confirmation,
            hints=(
                RecoveryHint(
                    hint_id="await_operator_confirmation",
                    summary="Await explicit operator confirmation before continuing.",
                    next_expected_signal="operator_confirmation",
                ),
            ),
            metadata=metadata,
        )

    def _plan(
        self,
        *,
        failure_origin: RecoveryFailureOrigin,
        disposition: RecoveryHandlingDisposition,
        retryability: RecoveryRetryability,
        summary: str,
        hints: tuple[RecoveryHint, ...],
        escalation_outcome: RecoveryEscalationOutcome = RecoveryEscalationOutcome.none,
        human_confirmation_status: HumanConfirmationStatus = HumanConfirmationStatus.not_required,
        metadata: Mapping[str, object] | None = None,
    ) -> RecoveryHandlingPlan:
        return RecoveryHandlingPlan(
            failure_origin=failure_origin,
            disposition=disposition,
            retryability=retryability,
            summary=summary,
            escalation_outcome=escalation_outcome,
            human_confirmation_status=human_confirmation_status,
            recovery_hints=hints,
            metadata={} if metadata is None else metadata,
        )


def _plan_metadata(
    first: Mapping[str, object] | None,
    second: Mapping[str, object] | None,
) -> dict[str, object]:
    merged: dict[str, object] = {}
    if first is not None:
        merged.update(first)
    if second is not None:
        merged.update(second)
    return merged


__all__ = ["ObserveOnlyRecoveryEscalationHitlPlanner"]
