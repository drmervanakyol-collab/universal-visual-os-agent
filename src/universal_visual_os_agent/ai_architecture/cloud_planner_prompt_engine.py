"""Compact prompt building for the observe-only cloud planner client."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Mapping, Self

from universal_visual_os_agent.ai_architecture.arbitration import ArbitrationSource
from universal_visual_os_agent.ai_architecture.cloud_planner import (
    CloudPlannerForbiddenActionLabel,
    CloudPlannerOutcome,
    CloudPlannerRationaleCode,
    CloudPlannerRequest,
)
from universal_visual_os_agent.ai_architecture.escalation_engine import (
    DeterministicEscalationDisposition,
    DeterministicEscalationReason,
)
from universal_visual_os_agent.ai_architecture.ontology import (
    SharedCandidateLabel,
    SharedTargetLabel,
)
from universal_visual_os_agent.ai_boundary.models import AiSuggestedActionType
from universal_visual_os_agent.semantics.semantic_delta import SemanticDeltaCategory
from universal_visual_os_agent.verification.models import (
    CandidateScoreDeltaDirection,
    ExpectedSemanticChange,
)


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerPromptEnvelope:
    """Compact prompt payload for one cloud planner request attempt."""

    request_id: str
    attempt_index: int
    system_prompt: str
    user_prompt: str
    compact_context: Mapping[str, object] = field(default_factory=dict)
    correction_feedback: str | None = None
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("request_id must not be empty.")
        if self.attempt_index <= 0:
            raise ValueError("attempt_index must be positive.")
        if not self.system_prompt:
            raise ValueError("system_prompt must not be empty.")
        if not self.user_prompt:
            raise ValueError("user_prompt must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Cloud planner prompts must remain observe-only and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CloudPlannerPromptBuildResult:
    """Failure-safe prompt-building result for cloud planner calls."""

    prompt_engine_name: str
    success: bool
    prompt: CloudPlannerPromptEnvelope | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.prompt_engine_name:
            raise ValueError("prompt_engine_name must not be empty.")
        if self.success and self.prompt is None:
            raise ValueError("Successful prompt-build results must include prompt.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed prompt-build results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful prompt-build results must not include error details.")
        if not self.success and self.prompt is not None:
            raise ValueError("Failed prompt-build results must not include prompt.")

    @classmethod
    def ok(
        cls,
        *,
        prompt_engine_name: str,
        prompt: CloudPlannerPromptEnvelope,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            prompt_engine_name=prompt_engine_name,
            success=True,
            prompt=prompt,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        prompt_engine_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            prompt_engine_name=prompt_engine_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


class ObserveOnlyCloudPlannerPromptEngine:
    """Build compact, deterministic prompts for the cloud planner client."""

    prompt_engine_name = "ObserveOnlyCloudPlannerPromptEngine"
    _max_candidate_entries = 8
    _summary_character_limit = 240
    _correction_feedback_limit = 1000

    def build_prompt(
        self,
        request: CloudPlannerRequest,
        *,
        attempt_index: int = 1,
        correction_feedback: str | None = None,
    ) -> CloudPlannerPromptBuildResult:
        try:
            compact_context = _compact_context(
                request=request,
                max_candidate_entries=self._max_candidate_entries,
                summary_character_limit=self._summary_character_limit,
            )
            correction_text = (
                None
                if correction_feedback is None
                else correction_feedback[: self._correction_feedback_limit]
            )
            system_prompt = _system_prompt()
            user_prompt = json.dumps(
                {
                    "request_id": request.request_id,
                    "attempt_index": attempt_index,
                    "objective_summary": request.user_objective_summary,
                    "compact_context": compact_context,
                    "response_contract": _response_contract_hints(request),
                    "correction_feedback": correction_text,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            prompt = CloudPlannerPromptEnvelope(
                request_id=request.request_id,
                attempt_index=attempt_index,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                compact_context=compact_context,
                correction_feedback=correction_text,
                metadata={
                    "candidate_count": len(request.candidate_summary),
                    "prompt_candidate_count": len(
                        compact_context.get("candidate_summary", ())
                    ),
                    "signal_status": request.signal_status.value,
                    "correction_feedback_present": correction_text is not None,
                    "observe_only": True,
                    "read_only": True,
                    "non_executing": True,
                },
            )
        except Exception as exc:  # noqa: BLE001 - prompt building must remain failure-safe
            return CloudPlannerPromptBuildResult.failure(
                prompt_engine_name=self.prompt_engine_name,
                error_code="cloud_planner_prompt_build_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return CloudPlannerPromptBuildResult.ok(
            prompt_engine_name=self.prompt_engine_name,
            prompt=prompt,
            details={
                "attempt_index": attempt_index,
                "compact_candidate_count": len(compact_context.get("candidate_summary", ())),
            },
        )


def _system_prompt() -> str:
    return (
        "You are a safety-first cloud planner for a Windows UI agent. "
        "Return exactly one JSON object and no markdown. "
        "Stay observe-only and non-executing. "
        "Never request live execution, text entry, keyboard input, or drag/drop. "
        "Use only the allowed enum values, candidate_ids, candidate labels, target labels, "
        "and escalation values supplied in the request. "
        "If context is insufficient or ambiguous, use outcome 'unresolved' or 'unknown' "
        "instead of inventing certainty."
    )


def _compact_context(
    *,
    request: CloudPlannerRequest,
    max_candidate_entries: int,
    summary_character_limit: int,
) -> Mapping[str, object]:
    candidate_entries = tuple(
        sorted(
            request.candidate_summary,
            key=lambda entry: (entry.rank, entry.candidate_binding.candidate_id),
        )
    )
    limited_entries = candidate_entries[:max_candidate_entries]
    candidate_summary = tuple(
        {
            "candidate_id": entry.candidate_binding.candidate_id,
            "rank": entry.rank,
            "score": entry.score,
            "visible": entry.visible,
            "candidate_label": entry.candidate_binding.candidate_label,
            "shared_candidate_label": (
                None
                if entry.candidate_binding.shared_candidate_label is None
                else entry.candidate_binding.shared_candidate_label.value
            ),
            "confidence": entry.candidate_binding.confidence,
            "selection_risk_level": (
                None
                if entry.candidate_binding.selection_risk_level is None
                else entry.candidate_binding.selection_risk_level.value
            ),
            "source_type": (
                None
                if entry.candidate_binding.source_type is None
                else entry.candidate_binding.source_type.value
            ),
            "disambiguation_needed": entry.candidate_binding.disambiguation_needed,
            "requires_local_resolver": entry.candidate_binding.requires_local_resolver,
            "source_conflict_present": entry.candidate_binding.source_conflict_present,
            "completeness_status": entry.completeness_status,
            "allowed_target_labels": tuple(
                label.value for label in entry.candidate_binding.allowed_target_labels
            ),
            "action_intent_id": entry.action_intent_id,
            "action_intent_status": entry.action_intent_status,
        }
        for entry in limited_entries
    )
    return {
        "snapshot_id": request.snapshot_id,
        "signal_status": request.signal_status.value,
        "candidate_summary": candidate_summary,
        "candidate_count": len(candidate_entries),
        "truncated_candidate_count": max(0, len(candidate_entries) - len(candidate_summary)),
        "scenario_context": _scenario_context_payload(
            request=request,
            summary_character_limit=summary_character_limit,
        ),
        "verification_context": _verification_context_payload(
            request=request,
            summary_character_limit=summary_character_limit,
        ),
        "escalation_context": _escalation_context_payload(
            request=request,
            summary_character_limit=summary_character_limit,
        ),
    }


def _scenario_context_payload(
    *,
    request: CloudPlannerRequest,
    summary_character_limit: int,
) -> Mapping[str, object] | None:
    if request.scenario_context is None:
        return None
    return {
        "scenario_id": request.scenario_context.scenario_id,
        "title": _truncate_text(request.scenario_context.title, summary_character_limit),
        "summary": _truncate_text(request.scenario_context.summary, summary_character_limit),
        "step_ids": request.scenario_context.step_ids,
        "status": request.scenario_context.status,
        "dry_run_eligible": request.scenario_context.dry_run_eligible,
        "real_click_eligible": request.scenario_context.real_click_eligible,
    }


def _verification_context_payload(
    *,
    request: CloudPlannerRequest,
    summary_character_limit: int,
) -> Mapping[str, object] | None:
    if request.verification_context is None:
        return None
    return {
        "status": request.verification_context.status.value,
        "summary": _truncate_text(request.verification_context.summary, summary_character_limit),
        "matched_outcome_ids": request.verification_context.matched_outcome_ids,
        "unsatisfied_outcome_ids": request.verification_context.unsatisfied_outcome_ids,
        "unknown_outcome_ids": request.verification_context.unknown_outcome_ids,
    }


def _escalation_context_payload(
    *,
    request: CloudPlannerRequest,
    summary_character_limit: int,
) -> Mapping[str, object] | None:
    if request.escalation_context is None:
        return None
    return {
        "disposition": request.escalation_context.disposition.value,
        "summary": _truncate_text(request.escalation_context.summary, summary_character_limit),
        "recommended_source": (
            None
            if request.escalation_context.recommended_source is None
            else request.escalation_context.recommended_source.value
        ),
        "reason_codes": tuple(
            reason.value for reason in request.escalation_context.reason_codes
        ),
    }


def _response_contract_hints(request: CloudPlannerRequest) -> Mapping[str, object]:
    allowed_candidate_ids = tuple(
        entry.candidate_binding.candidate_id for entry in request.candidate_summary
    )
    allowed_candidate_labels = tuple(
        dict.fromkeys(
            entry.candidate_binding.shared_candidate_label.value
            for entry in request.candidate_summary
            if entry.candidate_binding.shared_candidate_label is not None
        )
    )
    allowed_target_labels = tuple(
        dict.fromkeys(
            label.value
            for entry in request.candidate_summary
            for label in entry.candidate_binding.allowed_target_labels
        )
    ) or tuple(label.value for label in SharedTargetLabel)
    return {
        "required_fields": ("summary", "outcome", "rationale_code"),
        "planned_required_fields": (
            "normalized_goal",
            "subgoals",
        ),
        "allowed_outcomes": tuple(outcome.value for outcome in CloudPlannerOutcome),
        "allowed_rationale_codes": tuple(
            rationale_code.value for rationale_code in CloudPlannerRationaleCode
        ),
        "allowed_action_types": tuple(
            action_type.value for action_type in AiSuggestedActionType
        ),
        "allowed_candidate_ids": allowed_candidate_ids,
        "allowed_candidate_labels": allowed_candidate_labels,
        "allowed_target_labels": allowed_target_labels,
        "allowed_forbidden_actions": tuple(
            label.value for label in CloudPlannerForbiddenActionLabel
        ),
        "required_forbidden_actions": (
            CloudPlannerForbiddenActionLabel.live_execution.value,
        ),
        "allowed_escalation_dispositions": tuple(
            disposition.value for disposition in DeterministicEscalationDisposition
        ),
        "allowed_escalation_reasons": tuple(
            reason.value for reason in DeterministicEscalationReason
        ),
        "allowed_arbitration_sources": tuple(
            source.value for source in ArbitrationSource
        ),
        "allowed_delta_categories": tuple(
            category.value for category in SemanticDeltaCategory
        ),
        "allowed_expected_changes": tuple(
            change.value for change in ExpectedSemanticChange
        ),
        "allowed_score_delta_directions": tuple(
            direction.value for direction in CandidateScoreDeltaDirection
        ),
        "subgoal_shape": {
            "subgoal_id": "string",
            "summary": "string",
            "action_type": "enum",
            "candidate_id": "string or null",
            "candidate_label": "enum or null",
            "target_label": "enum or null",
            "success_criterion_ids": "string[]",
            "dry_run_only": "bool, default true",
        },
        "success_criterion_shape": {
            "criterion_id": "string",
            "summary": "string",
            "expectation": {
                "summary": "string",
                "required_candidate_ids": "string[]",
                "forbidden_candidate_ids": "string[]",
                "required_node_ids": "string[]",
                "expected_outcomes": "ExpectedSemanticOutcome[]",
                "alternate_outcome_branches": "VerificationOutcomeBranch[]",
                "timing": {
                    "timeout_seconds": "number or null",
                    "poll_interval_ms": "int or null",
                    "max_poll_attempts": "int or null",
                },
            },
        },
    }


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."
