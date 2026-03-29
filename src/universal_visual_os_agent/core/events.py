"""Shared event wrapper types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping
from uuid import uuid4


@dataclass(slots=True, frozen=True, kw_only=True)
class EventEnvelope:
    """Transport-safe event container used across layers."""

    event_type: str
    payload: Mapping[str, object]
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

