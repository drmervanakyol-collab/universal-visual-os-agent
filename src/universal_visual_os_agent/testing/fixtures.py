"""Reusable test helpers for replay and recovery modes."""

from __future__ import annotations

from pathlib import Path

from universal_visual_os_agent.app.models import LoopRequest
from universal_visual_os_agent.config.modes import AgentMode
from universal_visual_os_agent.config.models import ReplayConfig, RunConfig
from universal_visual_os_agent.persistence.models import CheckpointRecord, TaskRecord
from universal_visual_os_agent.recovery.models import RecoverySnapshot


def build_replay_mode_config(session_path: Path) -> RunConfig:
    """Build a replay-mode configuration for tests."""

    return RunConfig(
        mode=AgentMode.replay_mode,
        replay=ReplayConfig(session_path=session_path),
    )


def build_recovery_mode_config() -> RunConfig:
    """Build a recovery-mode configuration for tests."""

    return RunConfig(mode=AgentMode.recovery_mode)


def build_recovery_mode_request(task_id: str = "task-recovery") -> LoopRequest:
    """Build a recovery-mode loop request."""

    return LoopRequest(task_id=task_id)


def build_recovery_snapshot(task_id: str = "task-recovery") -> RecoverySnapshot:
    """Build a minimal recovery snapshot for replay and recovery tests."""

    return RecoverySnapshot(
        task=TaskRecord(task_id=task_id, goal="Recover safely"),
        checkpoint=CheckpointRecord(checkpoint_id=f"{task_id}-checkpoint", task_id=task_id),
    )
