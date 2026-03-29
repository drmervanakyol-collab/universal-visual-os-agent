"""Recovery model types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(slots=True, frozen=True, kw_only=True)
class RecoverySnapshot:
    """Recovered execution context loaded from persistence."""

    task_id: str
    checkpoint_id: str
    context: Mapping[str, object] = field(default_factory=dict)

