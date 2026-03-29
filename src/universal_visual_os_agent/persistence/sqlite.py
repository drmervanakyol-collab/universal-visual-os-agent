"""Concrete SQLite repositories for safe local persistence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from universal_visual_os_agent.audit.models import AuditEvent
from universal_visual_os_agent.persistence.models import CheckpointRecord, TaskRecord
from universal_visual_os_agent.persistence.schema import create_schema


def connect_sqlite(database_path: Path) -> sqlite3.Connection:
    """Open a SQLite database with the Phase 2 schema initialized."""

    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    create_schema(connection)
    return connection


class SqliteTaskRepository:
    """SQLite-backed task repository."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save(self, task: TaskRecord) -> TaskRecord:
        payload = {
            "task_id": task.task_id,
            "goal": task.goal,
            "status": task.status,
            "state_json": _to_json(task.state),
            "updated_at": task.updated_at.isoformat(),
        }
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO tasks (task_id, goal, status, state_json, updated_at)
                VALUES (:task_id, :goal, :status, :state_json, :updated_at)
                ON CONFLICT(task_id) DO UPDATE SET
                    goal = excluded.goal,
                    status = excluded.status,
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                payload,
            )
        return task

    def get(self, task_id: str) -> TaskRecord | None:
        row = self._connection.execute(
            """
            SELECT task_id, goal, status, state_json, updated_at
            FROM tasks
            WHERE task_id = :task_id
            """,
            {"task_id": task_id},
        ).fetchone()
        if row is None:
            return None
        return _task_from_row(row)


class SqliteCheckpointRepository:
    """SQLite-backed checkpoint repository."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save(self, checkpoint: CheckpointRecord) -> CheckpointRecord:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO checkpoints (
                    checkpoint_id,
                    task_id,
                    state_json,
                    recovery_json,
                    recorded_at
                )
                VALUES (
                    :checkpoint_id,
                    :task_id,
                    :state_json,
                    :recovery_json,
                    :recorded_at
                )
                """,
                {
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "task_id": checkpoint.task_id,
                    "state_json": _to_json(checkpoint.state),
                    "recovery_json": _to_json(checkpoint.recovery_metadata),
                    "recorded_at": checkpoint.recorded_at.isoformat(),
                },
            )
        return checkpoint

    def get_latest_for_task(self, task_id: str) -> CheckpointRecord | None:
        row = self._connection.execute(
            """
            SELECT checkpoint_id, task_id, state_json, recovery_json, recorded_at
            FROM checkpoints
            WHERE task_id = :task_id
            ORDER BY recorded_at DESC, rowid DESC
            LIMIT 1
            """,
            {"task_id": task_id},
        ).fetchone()
        if row is None:
            return None
        return _checkpoint_from_row(row)


class SqliteAuditEventRepository:
    """SQLite-backed audit event repository."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def append(self, event: AuditEvent) -> AuditEvent:
        with self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO audit_events (
                    task_id,
                    category,
                    message,
                    details_json,
                    recorded_at
                )
                VALUES (
                    :task_id,
                    :category,
                    :message,
                    :details_json,
                    :recorded_at
                )
                """,
                {
                    "task_id": event.task_id,
                    "category": event.category,
                    "message": event.message,
                    "details_json": _to_json(event.details),
                    "recorded_at": event.recorded_at.isoformat(),
                },
            )
        return AuditEvent(
            event_id=int(cursor.lastrowid),
            task_id=event.task_id,
            category=event.category,
            message=event.message,
            details=dict(event.details),
            recorded_at=event.recorded_at,
        )

    def list_recent(self, *, limit: int = 100) -> list[AuditEvent]:
        rows = self._connection.execute(
            """
            SELECT event_id, task_id, category, message, details_json, recorded_at
            FROM audit_events
            ORDER BY recorded_at ASC, event_id ASC
            LIMIT :limit
            """,
            {"limit": limit},
        ).fetchall()
        return [_audit_event_from_row(row) for row in rows]


def _task_from_row(row: sqlite3.Row) -> TaskRecord:
    return TaskRecord(
        task_id=str(row["task_id"]),
        goal=str(row["goal"]),
        status=str(row["status"]),
        state=_from_json(str(row["state_json"])),
        updated_at=datetime.fromisoformat(str(row["updated_at"])),
    )


def _checkpoint_from_row(row: sqlite3.Row) -> CheckpointRecord:
    return CheckpointRecord(
        checkpoint_id=str(row["checkpoint_id"]),
        task_id=str(row["task_id"]),
        state=_from_json(str(row["state_json"])),
        recovery_metadata=_from_json(str(row["recovery_json"])),
        recorded_at=datetime.fromisoformat(str(row["recorded_at"])),
    )


def _audit_event_from_row(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        event_id=int(row["event_id"]),
        task_id=str(row["task_id"]) if row["task_id"] is not None else None,
        category=str(row["category"]),
        message=str(row["message"]),
        details=_from_json(str(row["details_json"])),
        recorded_at=datetime.fromisoformat(str(row["recorded_at"])),
    )


def _to_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True)


def _from_json(raw: str) -> dict[str, object]:
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("Expected JSON object payload.")
    return {str(key): value for key, value in loaded.items()}
