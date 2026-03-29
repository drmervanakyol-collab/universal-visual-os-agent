"""SQLite-oriented persistence models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping


@dataclass(slots=True, frozen=True, kw_only=True)
class TaskRecord:
    """Persisted task state used as the root for checkpoints."""

    task_id: str
    goal: str
    status: str = "pending"
    state: Mapping[str, object] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True, frozen=True, kw_only=True)
class CheckpointRecord:
    """Persisted checkpoint metadata for recovery."""

    checkpoint_id: str
    task_id: str
    state: Mapping[str, object] = field(default_factory=dict)
    recovery_metadata: Mapping[str, object] = field(default_factory=dict)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
