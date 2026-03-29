"""Recovery snapshot loading primitives backed by repositories."""

from __future__ import annotations

from universal_visual_os_agent.persistence.interfaces import CheckpointRepository, TaskRepository
from universal_visual_os_agent.recovery.models import RecoverySnapshot


class RepositoryBackedRecoverySnapshotLoader:
    """Compose task and checkpoint repositories into recovery snapshots."""

    def __init__(
        self,
        *,
        task_repository: TaskRepository,
        checkpoint_repository: CheckpointRepository,
    ) -> None:
        self._task_repository = task_repository
        self._checkpoint_repository = checkpoint_repository

    def load_latest(self, task_id: str) -> RecoverySnapshot | None:
        """Load a recovery snapshot when both task and checkpoint state exist."""

        task = self._task_repository.get(task_id)
        if task is None:
            return None

        checkpoint = self._checkpoint_repository.get_latest_for_task(task_id)
        if checkpoint is None:
            return None

        return RecoverySnapshot(task=task, checkpoint=checkpoint)
