"""Phase 2 checkpoint persistence services."""

from __future__ import annotations

from universal_visual_os_agent.persistence.interfaces import CheckpointRepository, TaskRepository
from universal_visual_os_agent.persistence.models import CheckpointRecord


class CheckpointPersistenceService:
    """Write and read checkpoints with safe task existence checks."""

    def __init__(
        self,
        *,
        task_repository: TaskRepository,
        checkpoint_repository: CheckpointRepository,
    ) -> None:
        self._task_repository = task_repository
        self._checkpoint_repository = checkpoint_repository

    def write_checkpoint(self, checkpoint: CheckpointRecord) -> CheckpointRecord:
        """Persist a checkpoint for an existing task."""

        if self._task_repository.get(checkpoint.task_id) is None:
            raise ValueError(f"Cannot write checkpoint for missing task: {checkpoint.task_id}")
        return self._checkpoint_repository.save(checkpoint)

    def read_latest_checkpoint(self, task_id: str) -> CheckpointRecord | None:
        """Load the latest checkpoint for a task, if one exists."""

        return self._checkpoint_repository.get_latest_for_task(task_id)
