"""Scenario-definition interfaces."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.scenarios.models import (
    ScenarioDefinition,
    ScenarioDefinitionResult,
)


class ScenarioDefinitionBuilder(Protocol):
    """Contract for building and validating scenario definitions."""

    def build(self, scenario: ScenarioDefinition) -> ScenarioDefinitionResult:
        """Validate and normalize one structured scenario definition."""
