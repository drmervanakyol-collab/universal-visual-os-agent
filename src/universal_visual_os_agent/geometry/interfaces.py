"""Protocols for future OS-backed screen metrics providers."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.geometry.models import ScreenMetricsQueryResult


class ScreenMetricsProvider(Protocol):
    """OS-facing contract for retrieving virtual desktop metrics."""

    def get_virtual_desktop_metrics(self) -> ScreenMetricsQueryResult:
        """Return metrics or a structured failure without performing input actions."""
