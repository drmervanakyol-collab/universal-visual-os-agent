"""Minimal safety-first real click prototype."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from math import floor
from typing import TYPE_CHECKING, Mapping, Self

from universal_visual_os_agent.config.modes import AgentMode
from universal_visual_os_agent.config.models import RunConfig
from universal_visual_os_agent.geometry.models import ScreenPoint, VirtualDesktopMetrics
from universal_visual_os_agent.policy.interfaces import PolicyEngine
from universal_visual_os_agent.policy.models import (
    PolicyContextCompleteness,
    PolicyDecision,
    PolicyEvaluationContext,
    PolicyVerdict,
)
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot

from .dry_run import ObserveOnlyDryRunActionEngine
from .dry_run_models import (
    DryRunActionDisposition,
    DryRunActionEvaluation,
)
from .models import ActionIntent, ActionRequirementStatus

if TYPE_CHECKING:
    from .interfaces import RealClickTransport


class SafeClickPrototypeStatus(StrEnum):
    """Statuses produced by the minimal safe-click prototype."""

    dry_run_only = "dry_run_only"
    blocked = "blocked"
    real_click_allowed = "real_click_allowed"
    real_click_executed = "real_click_executed"


@dataclass(slots=True, frozen=True, kw_only=True)
class SafeClickGateOutcome:
    """One safety gate evaluated by the click prototype."""

    gate_id: str
    summary: str
    status: ActionRequirementStatus
    reason: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.gate_id:
            raise ValueError("gate_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if not self.reason:
            raise ValueError("reason must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SafeClickExecution:
    """Structured outcome for one minimal safe-click attempt."""

    intent_id: str
    action_type: str
    status: SafeClickPrototypeStatus
    summary: str
    target_screen_point: ScreenPoint | None = None
    dry_run_evaluation: DryRunActionEvaluation | None = None
    policy_decision: PolicyDecision | None = None
    gate_outcomes: tuple[SafeClickGateOutcome, ...] = ()
    blocked_gate_ids: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    executed: bool = False
    simulated: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.intent_id:
            raise ValueError("intent_id must not be empty.")
        if not self.action_type:
            raise ValueError("action_type must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.executed != (self.status is SafeClickPrototypeStatus.real_click_executed):
            raise ValueError("executed must match whether status is real_click_executed.")
        if self.status is SafeClickPrototypeStatus.real_click_executed and self.simulated:
            raise ValueError("Executed real-click results must not be marked simulated.")
        if self.status is not SafeClickPrototypeStatus.real_click_executed and not self.simulated:
            raise ValueError("Non-executed safe-click results must remain simulated.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SafeClickExecutionResult:
    """Wrapper result for the minimal safe-click prototype."""

    executor_name: str
    success: bool
    source_intent: ActionIntent | None = None
    source_snapshot: SemanticStateSnapshot | None = None
    execution: SafeClickExecution | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.executor_name:
            raise ValueError("executor_name must not be empty.")
        if self.success and (self.source_intent is None or self.execution is None):
            raise ValueError("Successful safe-click results must include source_intent and execution.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed safe-click results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful safe-click results must not include error details.")
        if not self.success and self.execution is not None:
            raise ValueError("Failed safe-click results must not include execution.")

    @classmethod
    def ok(
        cls,
        *,
        executor_name: str,
        source_intent: ActionIntent,
        source_snapshot: SemanticStateSnapshot | None,
        execution: SafeClickExecution,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            executor_name=executor_name,
            success=True,
            source_intent=source_intent,
            source_snapshot=source_snapshot,
            execution=execution,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        executor_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            executor_name=executor_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


class SafeClickPrototypeExecutor:
    """Execute one extremely narrow, explicitly gated real-click prototype."""

    executor_name = "SafeClickPrototypeExecutor"

    def __init__(
        self,
        *,
        policy_engine: PolicyEngine,
        dry_run_engine: ObserveOnlyDryRunActionEngine | None = None,
        click_transport: RealClickTransport | None = None,
        minimum_confidence: float = 0.9,
        maximum_candidate_rank: int = 5,
        allowed_candidate_classes: frozenset[str] | None = None,
    ) -> None:
        self._policy_engine = policy_engine
        self._dry_run_engine = dry_run_engine or ObserveOnlyDryRunActionEngine()
        self._click_transport = click_transport
        self._minimum_confidence = minimum_confidence
        self._maximum_candidate_rank = maximum_candidate_rank
        self._allowed_candidate_classes = (
            frozenset({"button_like"})
            if allowed_candidate_classes is None
            else allowed_candidate_classes
        )

    def handle(
        self,
        intent: ActionIntent,
        *,
        config: RunConfig,
        metrics: VirtualDesktopMetrics | None = None,
        snapshot: SemanticStateSnapshot | None = None,
        policy_context: PolicyEvaluationContext | None = None,
        execute: bool = False,
    ) -> SafeClickExecutionResult:
        try:
            dry_run_result = self._dry_run_engine.evaluate_intent(intent, snapshot=snapshot)
            if not dry_run_result.success or dry_run_result.evaluation is None:
                return SafeClickExecutionResult.failure(
                    executor_name=self.executor_name,
                    error_code="dry_run_evaluation_unavailable",
                    error_message=(
                        dry_run_result.error_message
                        or "Safe click prototype requires a successful dry-run evaluation."
                    ),
                    details={
                        "upstream_error_code": dry_run_result.error_code,
                    },
                )

            dry_run_evaluation = dry_run_result.evaluation
            target_screen_point = _target_screen_point(intent=intent, metrics=metrics)
            policy_decision = None
            real_click_mode_enabled = _real_click_mode_enabled(config)
            if real_click_mode_enabled:
                policy_decision = self._policy_engine.evaluate(
                    intent,
                    context=_policy_context(
                        intent=intent,
                        config=config,
                        policy_context=policy_context,
                    ),
                )

            gate_outcomes = self._gate_outcomes(
                intent,
                config=config,
                dry_run_evaluation=dry_run_evaluation,
                target_screen_point=target_screen_point,
                policy_decision=policy_decision,
                execute=execute,
            )
            blocked_gate_ids = tuple(
                gate.gate_id
                for gate in gate_outcomes
                if gate.status is ActionRequirementStatus.blocked
            )
            blocking_reasons = tuple(
                gate.reason
                for gate in gate_outcomes
                if gate.status is ActionRequirementStatus.blocked
            )

            if not real_click_mode_enabled:
                execution = SafeClickExecution(
                    intent_id=intent.intent_id,
                    action_type=intent.action_type,
                    status=SafeClickPrototypeStatus.dry_run_only,
                    summary="Real click mode is disabled; the prototype remains in dry-run-only mode.",
                    target_screen_point=target_screen_point,
                    dry_run_evaluation=dry_run_evaluation,
                    policy_decision=policy_decision,
                    gate_outcomes=gate_outcomes,
                    blocked_gate_ids=blocked_gate_ids,
                    blocking_reasons=blocking_reasons,
                    executed=False,
                    simulated=True,
                    metadata=_execution_metadata(
                        config=config,
                        dry_run_evaluation=dry_run_evaluation,
                        target_screen_point=target_screen_point,
                        execute=execute,
                    ),
                )
                return SafeClickExecutionResult.ok(
                    executor_name=self.executor_name,
                    source_intent=intent,
                    source_snapshot=snapshot,
                    execution=execution,
                    details={"status": execution.status.value},
                )

            if blocked_gate_ids:
                execution = SafeClickExecution(
                    intent_id=intent.intent_id,
                    action_type=intent.action_type,
                    status=SafeClickPrototypeStatus.blocked,
                    summary="Real click prototype was blocked by one or more safety gates.",
                    target_screen_point=target_screen_point,
                    dry_run_evaluation=dry_run_evaluation,
                    policy_decision=policy_decision,
                    gate_outcomes=gate_outcomes,
                    blocked_gate_ids=blocked_gate_ids,
                    blocking_reasons=blocking_reasons,
                    executed=False,
                    simulated=True,
                    metadata=_execution_metadata(
                        config=config,
                        dry_run_evaluation=dry_run_evaluation,
                        target_screen_point=target_screen_point,
                        execute=execute,
                    ),
                )
                return SafeClickExecutionResult.ok(
                    executor_name=self.executor_name,
                    source_intent=intent,
                    source_snapshot=snapshot,
                    execution=execution,
                    details={"status": execution.status.value},
                )

            if not execute:
                execution = SafeClickExecution(
                    intent_id=intent.intent_id,
                    action_type=intent.action_type,
                    status=SafeClickPrototypeStatus.real_click_allowed,
                    summary="Real click prototype is allowed, but execution was not requested.",
                    target_screen_point=target_screen_point,
                    dry_run_evaluation=dry_run_evaluation,
                    policy_decision=policy_decision,
                    gate_outcomes=gate_outcomes,
                    blocked_gate_ids=(),
                    blocking_reasons=(),
                    executed=False,
                    simulated=True,
                    metadata=_execution_metadata(
                        config=config,
                        dry_run_evaluation=dry_run_evaluation,
                        target_screen_point=target_screen_point,
                        execute=execute,
                    ),
                )
                return SafeClickExecutionResult.ok(
                    executor_name=self.executor_name,
                    source_intent=intent,
                    source_snapshot=snapshot,
                    execution=execution,
                    details={"status": execution.status.value},
                )

            if target_screen_point is None or self._click_transport is None:
                raise RuntimeError("Safe click prototype reached execution without a target or click transport.")

            self._click_transport.click(target_screen_point)
            execution = SafeClickExecution(
                intent_id=intent.intent_id,
                action_type=intent.action_type,
                status=SafeClickPrototypeStatus.real_click_executed,
                summary="Real click prototype executed one constrained left click.",
                target_screen_point=target_screen_point,
                dry_run_evaluation=dry_run_evaluation,
                policy_decision=policy_decision,
                gate_outcomes=gate_outcomes,
                blocked_gate_ids=(),
                blocking_reasons=(),
                executed=True,
                simulated=False,
                metadata=_execution_metadata(
                    config=config,
                    dry_run_evaluation=dry_run_evaluation,
                    target_screen_point=target_screen_point,
                    execute=execute,
                ),
            )
            return SafeClickExecutionResult.ok(
                executor_name=self.executor_name,
                source_intent=intent,
                source_snapshot=snapshot,
                execution=execution,
                details={"status": execution.status.value},
            )
        except Exception as exc:  # noqa: BLE001 - safe click prototype must remain failure-safe
            return SafeClickExecutionResult.failure(
                executor_name=self.executor_name,
                error_code="safe_click_execution_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

    def _gate_outcomes(
        self,
        intent: ActionIntent,
        *,
        config: RunConfig,
        dry_run_evaluation: DryRunActionEvaluation,
        target_screen_point: ScreenPoint | None,
        policy_decision: PolicyDecision | None,
        execute: bool,
    ) -> tuple[SafeClickGateOutcome, ...]:
        candidate_class = intent.metadata.get("candidate_class")
        completeness_status = intent.metadata.get("candidate_exposure_completeness_status")
        eligible_class = isinstance(candidate_class, str) and candidate_class in self._allowed_candidate_classes
        eligible_rank = intent.candidate_rank is not None and intent.candidate_rank <= self._maximum_candidate_rank
        eligible_score = (
            intent.candidate_score is not None
            and intent.candidate_score >= self._minimum_confidence
        )
        policy_allowed = policy_decision is not None and policy_decision.verdict is PolicyVerdict.allow

        return (
            _gate_outcome(
                gate_id="real_click_mode_enabled",
                summary="Real click mode requires safe_action_mode plus allow_live_input=True.",
                status=(
                    ActionRequirementStatus.satisfied
                    if _real_click_mode_enabled(config)
                    else ActionRequirementStatus.blocked
                ),
                reason=(
                    "Real click mode is explicitly enabled."
                    if _real_click_mode_enabled(config)
                    else "RunConfig did not explicitly enable the real click prototype."
                ),
                metadata={"mode": config.mode.value, "allow_live_input": config.allow_live_input},
            ),
            _gate_outcome(
                gate_id="supported_action_type",
                summary="Only candidate_select intents are supported by the click prototype.",
                status=(
                    ActionRequirementStatus.satisfied
                    if intent.action_type == "candidate_select"
                    else ActionRequirementStatus.blocked
                ),
                reason=(
                    "Intent action type is supported."
                    if intent.action_type == "candidate_select"
                    else "Intent action type is outside the minimal click prototype."
                ),
                metadata={"action_type": intent.action_type},
            ),
            _gate_outcome(
                gate_id="explicit_candidate_allowlist",
                summary="Only top-ranked button-like candidates are explicitly eligible.",
                status=(
                    ActionRequirementStatus.satisfied
                    if eligible_class and eligible_rank
                    else ActionRequirementStatus.blocked
                ),
                reason=(
                    "Candidate matched the explicit prototype allowlist."
                    if eligible_class and eligible_rank
                    else "Candidate did not match the explicit prototype allowlist."
                ),
                metadata={
                    "candidate_class": candidate_class,
                    "candidate_rank": intent.candidate_rank,
                    "allowed_candidate_classes": tuple(sorted(self._allowed_candidate_classes)),
                    "maximum_candidate_rank": self._maximum_candidate_rank,
                },
            ),
            _gate_outcome(
                gate_id="candidate_complete",
                summary="Candidate must be scaffolded and have complete exposure metadata.",
                status=(
                    ActionRequirementStatus.satisfied
                    if intent.status is not None
                    and intent.status.value == "scaffolded"
                    and completeness_status == "available"
                    else ActionRequirementStatus.blocked
                ),
                reason=(
                    "Candidate metadata is complete for the click prototype."
                    if intent.status is not None
                    and intent.status.value == "scaffolded"
                    and completeness_status == "available"
                    else "Candidate metadata is incomplete for the click prototype."
                ),
                metadata={
                    "intent_status": intent.status.value,
                    "candidate_exposure_completeness_status": completeness_status,
                },
            ),
            _gate_outcome(
                gate_id="candidate_score_threshold",
                summary="Candidate confidence must meet the real-click threshold.",
                status=(
                    ActionRequirementStatus.satisfied
                    if eligible_score
                    else ActionRequirementStatus.blocked
                ),
                reason=(
                    "Candidate confidence met the real-click threshold."
                    if eligible_score
                    else "Candidate confidence was too low for the real-click prototype."
                ),
                metadata={
                    "candidate_score": intent.candidate_score,
                    "minimum_confidence": self._minimum_confidence,
                },
            ),
            _gate_outcome(
                gate_id="dry_run_would_execute",
                summary="Dry-run evaluation must conclude that the intent would execute safely.",
                status=(
                    ActionRequirementStatus.satisfied
                    if dry_run_evaluation.disposition is DryRunActionDisposition.would_execute
                    else ActionRequirementStatus.blocked
                ),
                reason=(
                    "Dry-run evaluation allowed the intent."
                    if dry_run_evaluation.disposition is DryRunActionDisposition.would_execute
                    else f"Dry-run evaluation blocked the intent: {dry_run_evaluation.summary}"
                ),
                metadata={"dry_run_disposition": dry_run_evaluation.disposition.value},
            ),
            _gate_outcome(
                gate_id="target_screen_point_available",
                summary="A validated screen click target must be available.",
                status=(
                    ActionRequirementStatus.satisfied
                    if target_screen_point is not None
                    else ActionRequirementStatus.blocked
                ),
                reason=(
                    "A screen click target was derived from the normalized intent target."
                    if target_screen_point is not None
                    else "No validated screen click target was available."
                ),
                metadata={
                    "has_normalized_target": intent.target is not None,
                    "target_screen_point": (
                        None
                        if target_screen_point is None
                        else (target_screen_point.x_px, target_screen_point.y_px)
                    ),
                },
            ),
            _gate_outcome(
                gate_id="policy_allow",
                summary="Policy must explicitly allow the live click attempt.",
                status=(
                    ActionRequirementStatus.pending
                    if not _real_click_mode_enabled(config)
                    else (
                        ActionRequirementStatus.satisfied
                        if policy_allowed
                        else ActionRequirementStatus.blocked
                    )
                ),
                reason=(
                    "Policy was not consulted because real click mode is disabled."
                    if not _real_click_mode_enabled(config)
                    else (
                        "Policy allowed the live click attempt."
                        if policy_allowed
                        else f"Policy blocked the live click attempt: {policy_decision.reason if policy_decision else 'no policy decision'}"
                    )
                ),
                metadata={
                    "policy_verdict": None if policy_decision is None else policy_decision.verdict.value,
                    "policy_reason": None if policy_decision is None else policy_decision.reason,
                },
            ),
            _gate_outcome(
                gate_id="click_transport_available",
                summary="A real click transport must be present when execution is requested.",
                status=(
                    ActionRequirementStatus.satisfied
                    if (not execute or self._click_transport is not None)
                    else ActionRequirementStatus.blocked
                ),
                reason=(
                    "Click transport is available for the requested path."
                    if (not execute or self._click_transport is not None)
                    else "Execution was requested without a real click transport."
                ),
                metadata={"execute_requested": execute},
            ),
        )


def _gate_outcome(
    *,
    gate_id: str,
    summary: str,
    status: ActionRequirementStatus,
    reason: str,
    metadata: Mapping[str, object],
) -> SafeClickGateOutcome:
    return SafeClickGateOutcome(
        gate_id=gate_id,
        summary=summary,
        status=status,
        reason=reason,
        metadata=metadata,
    )


def _real_click_mode_enabled(config: RunConfig) -> bool:
    return config.mode is AgentMode.safe_action_mode and config.allow_live_input


def _policy_context(
    *,
    intent: ActionIntent,
    config: RunConfig,
    policy_context: PolicyEvaluationContext | None,
) -> PolicyEvaluationContext:
    metadata = {} if policy_context is None else dict(policy_context.metadata)
    metadata.update(
        {
            "safe_click_prototype": True,
            "candidate_id": intent.candidate_id,
            "candidate_class": intent.metadata.get("candidate_class"),
        }
    )
    return PolicyEvaluationContext(
        completeness=(
            PolicyContextCompleteness.complete
            if policy_context is None
            else policy_context.completeness
        ),
        live_execution_requested=True,
        live_execution_enabled=config.allow_live_input,
        metadata=metadata,
    )


def _target_screen_point(
    *,
    intent: ActionIntent,
    metrics: VirtualDesktopMetrics | None,
) -> ScreenPoint | None:
    if intent.target is None or metrics is None:
        return None
    bounds = metrics.bounds
    x_px = (
        bounds.right_px - 1
        if intent.target.x >= 1.0
        else bounds.left_px + floor(intent.target.x * bounds.width_px)
    )
    y_px = (
        bounds.bottom_px - 1
        if intent.target.y >= 1.0
        else bounds.top_px + floor(intent.target.y * bounds.height_px)
    )
    return ScreenPoint(x_px=x_px, y_px=y_px)


def _execution_metadata(
    *,
    config: RunConfig,
    dry_run_evaluation: DryRunActionEvaluation,
    target_screen_point: ScreenPoint | None,
    execute: bool,
) -> Mapping[str, object]:
    return {
        "safe_click_prototype": True,
        "mode": config.mode.value,
        "allow_live_input": config.allow_live_input,
        "dry_run_disposition": dry_run_evaluation.disposition.value,
        "execute_requested": execute,
        "target_screen_point": (
            None
            if target_screen_point is None
            else (target_screen_point.x_px, target_screen_point.y_px)
        ),
    }
