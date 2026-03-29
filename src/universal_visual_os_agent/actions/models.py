"""Action intent and result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from universal_visual_os_agent.geometry.models import NormalizedPoint


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionIntent:
    """An action the planner would like to perform."""

    action_type: str
    target: NormalizedPoint | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(slots=True, frozen=True, kw_only=True)
class ActionResult:
    """Result returned by a dry-run or future executor."""

    accepted: bool
    simulated: bool
    details: Mapping[str, object] = field(default_factory=dict)

