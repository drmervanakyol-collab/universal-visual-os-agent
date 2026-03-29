"""Shared low-level interfaces."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from universal_visual_os_agent.core.events import EventEnvelope


class Clock(Protocol):
    """Clock abstraction for deterministic tests."""

    def now(self) -> datetime:
        """Return the current UTC-aware timestamp."""


class EventSink(Protocol):
    """Minimal interface for publishing structured events."""

    def emit(self, event: EventEnvelope) -> None:
        """Publish a single event envelope."""

