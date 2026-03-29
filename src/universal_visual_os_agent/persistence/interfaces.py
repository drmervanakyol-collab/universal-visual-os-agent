"""Repository interfaces for SQLite-backed persistence."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.audit.models import AuditEvent
from universal_visual_os_agent.persistence.models import CheckpointRecord, TaskRecord


class TaskRepository(Protocol):
    """Task persistence contract."""

    def save(self, task: TaskRecord) -> TaskRecord:
        """Create or update a task record."""

    def get(self, task_id: str) -> TaskRecord | None:
        """Load a task by identifier."""


class CheckpointRepository(Protocol):
    """Checkpoint persistence contract."""

    def save(self, checkpoint: CheckpointRecord) -> CheckpointRecord:
        """Create a checkpoint record."""

    def get_latest_for_task(self, task_id: str) -> CheckpointRecord | None:
        """Load the most recent checkpoint for a task."""


class AuditEventRepository(Protocol):
    """Audit event persistence contract."""

    def append(self, event: AuditEvent) -> AuditEvent:
        """Persist a single audit event."""

    def list_recent(self, *, limit: int = 100) -> list[AuditEvent]:
        """Return recent audit events in ascending storage order."""

