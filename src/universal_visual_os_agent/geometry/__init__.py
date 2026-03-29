"""Geometry and screen metric exports."""

from universal_visual_os_agent.geometry.interfaces import ScreenMetricsProvider
from universal_visual_os_agent.geometry.models import (
    NormalizedBBox,
    NormalizedPoint,
    ScreenBBox,
    ScreenMetrics,
    ScreenMetricsQueryResult,
    ScreenPoint,
    VirtualDesktopMetrics,
)
from universal_visual_os_agent.geometry.transforms import (
    bbox_normalized_to_screen,
    dpi_aware_screen_metrics,
    normalized_to_screen,
    screen_to_normalized,
)

__all__ = [
    "NormalizedBBox",
    "NormalizedPoint",
    "ScreenBBox",
    "ScreenMetrics",
    "ScreenMetricsQueryResult",
    "ScreenMetricsProvider",
    "ScreenPoint",
    "VirtualDesktopMetrics",
    "bbox_normalized_to_screen",
    "dpi_aware_screen_metrics",
    "normalized_to_screen",
    "screen_to_normalized",
]
