from __future__ import annotations

from datetime import UTC, datetime, timedelta
from universal_visual_os_agent.audit.models import AuditEvent
from universal_visual_os_agent.persistence import (
    CheckpointPersistenceService,
    CheckpointRecord,
    SqliteAuditEventRepository,
    SqliteCheckpointRepository,
    SqliteTaskRepository,
    TaskRecord,
    connect_sqlite,
)
from universal_visual_os_agent.recovery import RepositoryBackedRecoverySnapshotLoader


def test_checkpoint_writer_and_latest_reader(workspace_tmp_path) -> None:
    connection = connect_sqlite(workspace_tmp_path / "agent.sqlite3")
    task_repository = SqliteTaskRepository(connection)
    checkpoint_repository = SqliteCheckpointRepository(connection)
    service = CheckpointPersistenceService(
        task_repository=task_repository,
        checkpoint_repository=checkpoint_repository,
    )
    task_repository.save(TaskRecord(task_id="task-1", goal="Inspect app"))

    first = service.write_checkpoint(
        CheckpointRecord(
            checkpoint_id="cp-1",
            task_id="task-1",
            state={"step": 1},
            recorded_at=datetime(2026, 3, 29, 18, 0, tzinfo=UTC),
        )
    )
    second = service.write_checkpoint(
        CheckpointRecord(
            checkpoint_id="cp-2",
            task_id="task-1",
            state={"step": 2},
            recovery_metadata={"resume_hint": "verify"},
            recorded_at=first.recorded_at + timedelta(minutes=5),
        )
    )

    latest = service.read_latest_checkpoint("task-1")

    assert latest == second


def test_recovery_loader_returns_snapshot_from_latest_checkpoint(workspace_tmp_path) -> None:
    connection = connect_sqlite(workspace_tmp_path / "agent.sqlite3")
    task_repository = SqliteTaskRepository(connection)
    checkpoint_repository = SqliteCheckpointRepository(connection)
    service = CheckpointPersistenceService(
        task_repository=task_repository,
        checkpoint_repository=checkpoint_repository,
    )
    loader = RepositoryBackedRecoverySnapshotLoader(
        task_repository=task_repository,
        checkpoint_repository=checkpoint_repository,
    )

    task_repository.save(
        TaskRecord(
            task_id="task-2",
            goal="Recover safely",
            status="paused",
            state={"phase": "verification"},
        )
    )
    service.write_checkpoint(
        CheckpointRecord(
            checkpoint_id="cp-10",
            task_id="task-2",
            state={"step": "confirm"},
            recovery_metadata={"resume_mode": "recovery_mode"},
        )
    )

    snapshot = loader.load_latest("task-2")

    assert snapshot is not None
    assert snapshot.task.task_id == "task-2"
    assert snapshot.checkpoint.checkpoint_id == "cp-10"
    assert snapshot.context == {"resume_mode": "recovery_mode"}


def test_missing_checkpoint_data_returns_none_safely(workspace_tmp_path) -> None:
    connection = connect_sqlite(workspace_tmp_path / "agent.sqlite3")
    task_repository = SqliteTaskRepository(connection)
    checkpoint_repository = SqliteCheckpointRepository(connection)
    loader = RepositoryBackedRecoverySnapshotLoader(
        task_repository=task_repository,
        checkpoint_repository=checkpoint_repository,
    )

    task_repository.save(TaskRecord(task_id="task-3", goal="No checkpoint yet"))

    assert loader.load_latest("task-3") is None
    assert loader.load_latest("missing-task") is None


def test_checkpoint_write_rejects_missing_task(workspace_tmp_path) -> None:
    connection = connect_sqlite(workspace_tmp_path / "agent.sqlite3")
    service = CheckpointPersistenceService(
        task_repository=SqliteTaskRepository(connection),
        checkpoint_repository=SqliteCheckpointRepository(connection),
    )

    try:
        service.write_checkpoint(CheckpointRecord(checkpoint_id="cp-missing", task_id="task-missing"))
    except ValueError as exc:
        assert "missing task" in str(exc)
    else:
        raise AssertionError("Expected missing task checkpoint write to fail safely.")


def test_audit_event_persistence_basics(workspace_tmp_path) -> None:
    connection = connect_sqlite(workspace_tmp_path / "agent.sqlite3")
    task_repository = SqliteTaskRepository(connection)
    audit_repository = SqliteAuditEventRepository(connection)
    task_repository.save(TaskRecord(task_id="task-4", goal="Audit trail"))

    stored = audit_repository.append(
        AuditEvent(
            task_id="task-4",
            category="policy",
            message="Dry-run action reviewed",
            details={"verdict": "allow"},
        )
    )
    recent = audit_repository.list_recent()

    assert stored.event_id is not None
    assert recent == [stored]
