"""Protocols for future OS-backed screen metrics providers."""

from __future__ import annotations

from typing import Protocol

from universal_visual_os_agent.geometry.models import VirtualDesktopMetrics


class ScreenMetricsProvider(Protocol):
    """OS-facing contract for retrieving virtual desktop metrics."""

    def get_virtual_desktop_metrics(self) -> VirtualDesktopMetrics:
        """Return the current monitor layout without performing input actions."""

