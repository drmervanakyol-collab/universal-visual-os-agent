"""Perception provider interfaces."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.perception.models import CaptureResult


class CaptureProvider(Protocol):
    """Abstract frame provider for live or replay sources."""

    def capture_frame(self) -> CaptureResult:
        """Return the latest capture result without performing input actions."""
