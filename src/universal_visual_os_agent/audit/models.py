"""Audit models for observable system behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping


@dataclass(slots=True, frozen=True, kw_only=True)
class AuditEvent:
    """Human-readable audit record for safe actions and decisions."""

    category: str
    message: str
    task_id: str | None = None
    event_id: int | None = None
    details: Mapping[str, object] = field(default_factory=dict)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
