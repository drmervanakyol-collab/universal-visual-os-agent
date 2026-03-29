"""Async orchestration models for the main loop skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping
from uuid import uuid4

from universal_visual_os_agent.actions.models import ActionIntent, ActionResult
from universal_visual_os_agent.perception.models import CapturedFrame
from universal_visual_os_agent.planning.models import PlannerDecision
from universal_visual_os_agent.policy.models import PolicyDecision, PolicyEvaluationContext
from universal_visual_os_agent.recovery.models import ReconciliationResult, RecoverySnapshot
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot
from universal_visual_os_agent.verification.models import (
    SemanticTransitionExpectation,
    VerificationResult,
)


class LoopStage(StrEnum):
    """Ordered stages in one orchestration attempt."""

    observe = "observe"
    diff = "diff"
    semantic_rebuild = "semantic_rebuild"
    recovery_load = "recovery_load"
    recovery_reconcile = "recovery_reconcile"
    policy_check = "policy_check"
    plan = "plan"
    verify = "verify"
    execute = "execute"


class LoopStatus(StrEnum):
    """Terminal status for one orchestration request."""

    completed = "completed"
    cancelled = "cancelled"
    timed_out = "timed_out"
    aborted = "aborted"


@dataclass(slots=True, frozen=True, kw_only=True)
class FrameDiff:
    """Pure diff metadata between two observed frames."""

    changed: bool
    summary: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(slots=True, frozen=True, kw_only=True)
class LoopPlan:
    """Planner output consumed by the orchestration layer."""

    decision: PlannerDecision
    proposed_action: ActionIntent | None = None
    expectation: SemanticTransitionExpectation | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class RetryPolicy:
    """Retry configuration for the async loop skeleton."""

    max_attempts: int = 1
    retry_on_timeout: bool = True
    retry_on_exception: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive.")


@dataclass(slots=True, frozen=True, kw_only=True)
class LoopRequest:
    """A queued orchestration request."""

    request_id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)
    policy_context: PolicyEvaluationContext | None = None


@dataclass(slots=True, frozen=True, kw_only=True)
class LoopResult:
    """Structured result for one orchestration request."""

    status: LoopStatus
    executed_stages: tuple[LoopStage, ...] = ()
    attempt_count: int = 1
    request: LoopRequest | None = None
    frame: CapturedFrame | None = None
    diff: FrameDiff | None = None
    semantic_snapshot: SemanticStateSnapshot | None = None
    recovery_snapshot: RecoverySnapshot | None = None
    reconciliation_result: ReconciliationResult | None = None
    policy_decision: PolicyDecision | None = None
    plan: LoopPlan | None = None
    verification_result: VerificationResult | None = None
    action_result: ActionResult | None = None
    live_execution_attempted: bool = False
    safe_abort_reason: str | None = None
    error_type: str | None = None
