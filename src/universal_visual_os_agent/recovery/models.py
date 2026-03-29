"""Recovery model types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping

from universal_visual_os_agent.persistence.models import CheckpointRecord, TaskRecord


@dataclass(slots=True, frozen=True, kw_only=True)
class RecoverySnapshot:
    """Recovered execution context loaded from persistence."""

    task: TaskRecord
    checkpoint: CheckpointRecord
    loaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def task_id(self) -> str:
        """Expose the recovered task identifier."""

        return self.task.task_id

    @property
    def checkpoint_id(self) -> str:
        """Expose the recovered checkpoint identifier."""

        return self.checkpoint.checkpoint_id

    @property
    def context(self) -> Mapping[str, object]:
        """Return recovery metadata needed for future reconciliation."""

        return self.checkpoint.recovery_metadata


@dataclass(slots=True, frozen=True, kw_only=True)
class ReconciliationResult:
    """Result of comparing recovered state against current knowledge."""

    safe_to_resume: bool
    summary: str
    reconciled_state: Mapping[str, object] = field(default_factory=dict)
