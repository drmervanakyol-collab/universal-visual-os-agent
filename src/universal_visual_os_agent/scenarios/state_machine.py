"""Instrumented scenario/action finite-state machine models and helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from time import perf_counter
from typing import Mapping

from universal_visual_os_agent.recovery.models import (
    RecoveryHandlingDisposition,
    RecoveryHandlingPlan,
)


class ScenarioFlowState(StrEnum):
    """Explicit scenario/action flow states for the safety-first FSM."""

    started = "started"
    observed = "observed"
    understood = "understood"
    candidate_selected = "candidate_selected"
    intent_built = "intent_built"
    dry_run_passed = "dry_run_passed"
    execution_allowed = "execution_allowed"
    executed = "executed"
    verification_passed = "verification_passed"
    verification_failed = "verification_failed"
    blocked = "blocked"
    awaiting_user_confirmation = "awaiting_user_confirmation"
    recovery_needed = "recovery_needed"
    aborted = "aborted"


_ALLOWED_TRANSITIONS: Mapping[ScenarioFlowState | None, frozenset[ScenarioFlowState]] = {
    None: frozenset({ScenarioFlowState.started}),
    ScenarioFlowState.started: frozenset(
        {
            ScenarioFlowState.observed,
            ScenarioFlowState.recovery_needed,
            ScenarioFlowState.aborted,
        }
    ),
    ScenarioFlowState.observed: frozenset(
        {
            ScenarioFlowState.understood,
            ScenarioFlowState.blocked,
            ScenarioFlowState.awaiting_user_confirmation,
            ScenarioFlowState.recovery_needed,
            ScenarioFlowState.aborted,
        }
    ),
    ScenarioFlowState.understood: frozenset(
        {
            ScenarioFlowState.candidate_selected,
            ScenarioFlowState.verification_passed,
            ScenarioFlowState.verification_failed,
            ScenarioFlowState.blocked,
            ScenarioFlowState.awaiting_user_confirmation,
            ScenarioFlowState.recovery_needed,
            ScenarioFlowState.aborted,
        }
    ),
    ScenarioFlowState.candidate_selected: frozenset(
        {
            ScenarioFlowState.intent_built,
            ScenarioFlowState.blocked,
            ScenarioFlowState.awaiting_user_confirmation,
            ScenarioFlowState.recovery_needed,
            ScenarioFlowState.aborted,
        }
    ),
    ScenarioFlowState.intent_built: frozenset(
        {
            ScenarioFlowState.dry_run_passed,
            ScenarioFlowState.blocked,
            ScenarioFlowState.awaiting_user_confirmation,
            ScenarioFlowState.recovery_needed,
            ScenarioFlowState.aborted,
        }
    ),
    ScenarioFlowState.dry_run_passed: frozenset(
        {
            ScenarioFlowState.observed,
            ScenarioFlowState.execution_allowed,
            ScenarioFlowState.verification_passed,
            ScenarioFlowState.verification_failed,
            ScenarioFlowState.blocked,
            ScenarioFlowState.awaiting_user_confirmation,
            ScenarioFlowState.recovery_needed,
            ScenarioFlowState.aborted,
        }
    ),
    ScenarioFlowState.execution_allowed: frozenset(
        {
            ScenarioFlowState.observed,
            ScenarioFlowState.executed,
            ScenarioFlowState.verification_passed,
            ScenarioFlowState.verification_failed,
            ScenarioFlowState.blocked,
            ScenarioFlowState.awaiting_user_confirmation,
            ScenarioFlowState.recovery_needed,
            ScenarioFlowState.aborted,
        }
    ),
    ScenarioFlowState.executed: frozenset(
        {
            ScenarioFlowState.observed,
            ScenarioFlowState.verification_passed,
            ScenarioFlowState.verification_failed,
            ScenarioFlowState.blocked,
            ScenarioFlowState.awaiting_user_confirmation,
            ScenarioFlowState.recovery_needed,
            ScenarioFlowState.aborted,
        }
    ),
    ScenarioFlowState.verification_passed: frozenset(),
    ScenarioFlowState.verification_failed: frozenset(
        {
            ScenarioFlowState.recovery_needed,
            ScenarioFlowState.aborted,
        }
    ),
    ScenarioFlowState.blocked: frozenset(
        {
            ScenarioFlowState.awaiting_user_confirmation,
            ScenarioFlowState.recovery_needed,
            ScenarioFlowState.aborted,
        }
    ),
    ScenarioFlowState.awaiting_user_confirmation: frozenset(
        {
            ScenarioFlowState.observed,
            ScenarioFlowState.recovery_needed,
            ScenarioFlowState.aborted,
        }
    ),
    ScenarioFlowState.recovery_needed: frozenset(
        {
            ScenarioFlowState.awaiting_user_confirmation,
            ScenarioFlowState.observed,
            ScenarioFlowState.aborted,
        }
    ),
    ScenarioFlowState.aborted: frozenset(),
}


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioStateTransition:
    """One structured state transition with telemetry."""

    transition_id: str
    transition_index: int
    occurred_at: datetime
    from_state: ScenarioFlowState | None
    to_state: ScenarioFlowState
    latency_ms: float
    confidence: float | None = None
    block_reason: str | None = None
    recovery_hint: str | None = None
    next_expected_signal: str | None = None
    observe_only_inputs: bool = True
    safety_first: bool = True
    non_executing: bool = True
    live_execution_attempted: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.transition_id:
            raise ValueError("transition_id must not be empty.")
        if self.transition_index <= 0:
            raise ValueError("transition_index must be positive.")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware.")
        if self.latency_ms < 0.0:
            raise ValueError("latency_ms must not be negative.")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")
        if self.from_state is self.to_state:
            raise ValueError("Scenario state transitions must change state.")
        if not self.observe_only_inputs or not self.safety_first:
            raise ValueError("Scenario state transitions must remain observe-only-input and safety-first.")
        if self.live_execution_attempted and self.non_executing:
            raise ValueError("Executed transitions must not be marked non_executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ScenarioStateMachineTrace:
    """Stable state-machine trace for one scenario step."""

    trace_id: str
    current_state: ScenarioFlowState | None
    transitions: tuple[ScenarioStateTransition, ...]
    signal_status: str = "absent"
    observe_only_inputs: bool = True
    safety_first: bool = True
    non_executing: bool = True
    live_execution_attempted: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.trace_id:
            raise ValueError("trace_id must not be empty.")
        if self.signal_status not in {"available", "partial", "absent"}:
            raise ValueError("signal_status must be available, partial, or absent.")
        if not self.observe_only_inputs or not self.safety_first:
            raise ValueError("Scenario state-machine traces must remain observe-only-input and safety-first.")
        if self.transitions:
            if self.current_state is not self.transitions[-1].to_state:
                raise ValueError("current_state must match the last transition destination.")
        elif self.current_state is not None:
            raise ValueError("current_state must be None when transitions are empty.")
        if self.live_execution_attempted and self.non_executing:
            raise ValueError("Traces with executed live input must not be marked non_executing.")

    @property
    def state_history(self) -> tuple[ScenarioFlowState, ...]:
        """Return the visited states in transition order."""

        return tuple(transition.to_state for transition in self.transitions)


class InstrumentedScenarioStateMachine:
    """Small explicit FSM that records structured transition telemetry."""

    def __init__(
        self,
        *,
        trace_id: str,
        observe_only_inputs: bool = True,
        safety_first: bool = True,
    ) -> None:
        self._trace_id = trace_id
        self._observe_only_inputs = observe_only_inputs
        self._safety_first = safety_first
        self._transitions: list[ScenarioStateTransition] = []
        self._current_state: ScenarioFlowState | None = None
        self._non_executing = True
        self._live_execution_attempted = False
        self._last_counter = perf_counter()
        self.transition(
            ScenarioFlowState.started,
            next_expected_signal="capture_frame",
            metadata={"initial_state": True},
        )

    @property
    def current_state(self) -> ScenarioFlowState | None:
        """Return the current FSM state."""

        return self._current_state

    @property
    def transitions(self) -> tuple[ScenarioStateTransition, ...]:
        """Return emitted transitions in deterministic insertion order."""

        return tuple(self._transitions)

    def transition(
        self,
        to_state: ScenarioFlowState,
        *,
        confidence: float | None = None,
        block_reason: str | None = None,
        recovery_hint: str | None = None,
        next_expected_signal: str | None = None,
        live_execution_attempted: bool = False,
        non_executing: bool | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> ScenarioStateTransition:
        """Advance the FSM and record one telemetry-rich transition."""

        allowed_states = _ALLOWED_TRANSITIONS[self._current_state]
        if to_state not in allowed_states:
            raise ValueError(
                f"Invalid transition from {self._current_state!r} to {to_state!r}."
            )
        occurred_at = datetime.now(UTC)
        current_counter = perf_counter()
        latency_ms = 0.0
        if self._transitions:
            latency_ms = round(max(0.0, (current_counter - self._last_counter) * 1000.0), 3)
        transition_non_executing = (
            not live_execution_attempted if non_executing is None else non_executing
        )
        transition = ScenarioStateTransition(
            transition_id=f"{self._trace_id}:{len(self._transitions) + 1}",
            transition_index=len(self._transitions) + 1,
            occurred_at=occurred_at,
            from_state=self._current_state,
            to_state=to_state,
            latency_ms=latency_ms,
            confidence=confidence,
            block_reason=block_reason,
            recovery_hint=recovery_hint,
            next_expected_signal=next_expected_signal,
            observe_only_inputs=self._observe_only_inputs,
            safety_first=self._safety_first,
            non_executing=transition_non_executing,
            live_execution_attempted=live_execution_attempted,
            metadata={} if metadata is None else metadata,
        )
        self._transitions.append(transition)
        self._current_state = to_state
        self._last_counter = current_counter
        if live_execution_attempted:
            self._live_execution_attempted = True
        self._non_executing = self._non_executing and transition_non_executing
        return transition

    def trace(
        self,
        *,
        signal_status: str,
        metadata: Mapping[str, object] | None = None,
    ) -> ScenarioStateMachineTrace:
        """Build an immutable trace snapshot for downstream models."""

        return ScenarioStateMachineTrace(
            trace_id=self._trace_id,
            current_state=self._current_state,
            transitions=tuple(self._transitions),
            signal_status=signal_status,
            observe_only_inputs=self._observe_only_inputs,
            safety_first=self._safety_first,
            non_executing=self._non_executing,
            live_execution_attempted=self._live_execution_attempted,
            metadata={} if metadata is None else metadata,
        )

    def transition_for_recovery_plan(
        self,
        plan: RecoveryHandlingPlan,
        *,
        confidence: float | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> ScenarioStateTransition:
        """Map a structured recovery plan into one explicit FSM transition."""

        next_metadata = {
            "recovery_plan_disposition": plan.disposition.value,
            "recovery_plan_retryability": plan.retryability.value,
            "recovery_plan_escalation_outcome": plan.escalation_outcome.value,
            "recovery_plan_human_confirmation_status": plan.human_confirmation_status.value,
            **dict(plan.metadata),
            **({} if metadata is None else dict(metadata)),
        }
        if plan.disposition is RecoveryHandlingDisposition.await_user_confirmation:
            return self.transition(
                ScenarioFlowState.awaiting_user_confirmation,
                confidence=confidence,
                block_reason=plan.summary,
                recovery_hint=_first_recovery_hint(plan),
                next_expected_signal=_next_expected_signal(plan, default="operator_confirmation"),
                metadata=next_metadata,
            )
        if plan.disposition in {
            RecoveryHandlingDisposition.retry,
            RecoveryHandlingDisposition.escalate,
        }:
            return self.transition(
                ScenarioFlowState.recovery_needed,
                confidence=confidence,
                block_reason=plan.summary,
                recovery_hint=_first_recovery_hint(plan),
                next_expected_signal=_next_expected_signal(plan, default="recovery_signal"),
                metadata=next_metadata,
            )
        if plan.disposition is RecoveryHandlingDisposition.blocked:
            return self.transition(
                ScenarioFlowState.blocked,
                confidence=confidence,
                block_reason=plan.summary,
                recovery_hint=_first_recovery_hint(plan),
                next_expected_signal=_next_expected_signal(plan, default="operator_review"),
                metadata=next_metadata,
            )
        if plan.disposition is RecoveryHandlingDisposition.aborted:
            return self.transition(
                ScenarioFlowState.aborted,
                confidence=confidence,
                block_reason=plan.summary,
                recovery_hint=_first_recovery_hint(plan),
                next_expected_signal=_next_expected_signal(plan, default=None),
                metadata=next_metadata,
            )
        raise ValueError("No state transition is defined for no_recovery_needed plans.")


def _first_recovery_hint(plan: RecoveryHandlingPlan) -> str | None:
    if not plan.recovery_hints:
        return None
    return plan.recovery_hints[0].summary


def _next_expected_signal(
    plan: RecoveryHandlingPlan,
    *,
    default: str | None,
) -> str | None:
    if not plan.recovery_hints:
        return default
    return plan.recovery_hints[0].next_expected_signal or default
