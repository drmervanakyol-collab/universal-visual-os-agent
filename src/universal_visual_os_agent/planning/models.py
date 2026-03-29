"""Planner model types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(slots=True, frozen=True, kw_only=True)
class PlannerDecision:
    """Structured planner output for a single loop iteration."""

    goal: str
    rationale: str
    metadata: Mapping[str, object] = field(default_factory=dict)

