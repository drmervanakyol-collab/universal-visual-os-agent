"""Scenario-definition interfaces."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.config.models import RunConfig
from universal_visual_os_agent.geometry.models import VirtualDesktopMetrics
from universal_visual_os_agent.policy.models import PolicyEvaluationContext
from universal_visual_os_agent.scenarios.models import (
    ScenarioActionRunResult,
    ScenarioDefinition,
    ScenarioDefinitionResult,
    ScenarioRunResult,
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
