"""Scenario-definition and scenario-flow interfaces."""

from __future__ import annotations

from typing import Mapping, Protocol

from universal_visual_os_agent.config.models import RunConfig
from universal_visual_os_agent.geometry.models import VirtualDesktopMetrics
from universal_visual_os_agent.policy.models import PolicyEvaluationContext
from universal_visual_os_agent.scenarios.models import (
    ScenarioActionRunResult,
    ScenarioDefinition,
    ScenarioDefinitionResult,
    ScenarioRunResult,
)
from universal_visual_os_agent.scenarios.state_machine import (
    ScenarioFlowState,
    ScenarioStateMachineTrace,
    ScenarioStateTransition,
)
from universal_visual_os_agent.semantics.state import SemanticStateSnapshot


class ScenarioDefinitionBuilder(Protocol):
    """Contract for building and validating scenario definitions."""

    def build(self, scenario: ScenarioDefinition) -> ScenarioDefinitionResult:
        """Validate and normalize one structured scenario definition."""


class ScenarioRunner(Protocol):
    """Contract for the non-executing scenario observe-understand-verify loop."""

    def run(
        self,
        scenario: ScenarioDefinition,
        *,
        previous_snapshot: SemanticStateSnapshot | None = None,
    ) -> ScenarioRunResult:
        """Evaluate one scenario definition without performing real OS actions."""


class ScenarioActionRunner(Protocol):
    """Contract for the safety-first scenario observe-act-verify loop."""

    def run(
        self,
        scenario: ScenarioDefinition,
        *,
        previous_snapshot: SemanticStateSnapshot | None = None,
        config: RunConfig | None = None,
        metrics: VirtualDesktopMetrics | None = None,
        policy_context: PolicyEvaluationContext | None = None,
        execute: bool = False,
    ) -> ScenarioActionRunResult:
        """Evaluate one scenario definition through dry-run or safe-click handling."""


class ScenarioStateMachine(Protocol):
    """Contract for emitting structured scenario/action FSM transitions."""

    @property
    def current_state(self) -> ScenarioFlowState | None:
        """Return the currently active FSM state."""

    @property
    def transitions(self) -> tuple[ScenarioStateTransition, ...]:
        """Return emitted transitions in insertion order."""

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
        """Advance the state machine and record transition telemetry."""

    def trace(
        self,
        *,
        signal_status: str,
        metadata: Mapping[str, object] | None = None,
    ) -> ScenarioStateMachineTrace:
        """Return an immutable trace snapshot for downstream telemetry use."""
