"""Perception model types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True, frozen=True, kw_only=True)
class CapturedFrame:
    """Metadata for an observed frame."""

    frame_id: str
    width: int
    height: int
    captured_at: datetime = field(default_factory=lambda: datetime.now(UTC))

