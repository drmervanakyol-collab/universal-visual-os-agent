"""SQLite schema management for the Phase 2 persistence skeleton."""

from __future__ import annotations

import sqlite3

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        goal TEXT NOT NULL,
        status TEXT NOT NULL,
        state_json TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS checkpoints (
        checkpoint_id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        state_json TEXT NOT NULL,
        recovery_json TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT,
        category TEXT NOT NULL,
        message TEXT NOT NULL,
        details_json TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE SET NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_checkpoints_task_recorded ON checkpoints(task_id, recorded_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_audit_events_recorded ON audit_events(recorded_at DESC, event_id DESC)",
)


def create_schema(connection: sqlite3.Connection) -> None:
    """Ensure the required Phase 2 tables exist."""

    with connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
