"""Pure coordinate and bounding-box transforms."""

from __future__ import annotations

from math import floor

from universal_visual_os_agent.geometry.models import (
    NormalizedBBox,
    NormalizedPoint,
    ScreenBBox,
    ScreenMetrics,
    ScreenPoint,
)


def dpi_aware_screen_metrics(
    *,
    logical_width_px: int,
    logical_height_px: int,
    dpi_scale: float = 1.0,
    origin_x_px: int = 0,
    origin_y_px: int = 0,
    display_id: str = "primary",
    is_primary: bool = False,
) -> ScreenMetrics:
    """Create physical screen metrics from logical size and DPI scale."""

    if logical_width_px <= 0:
        raise ValueError("logical_width_px must be positive.")
    if logical_height_px <= 0:
        raise ValueError("logical_height_px must be positive.")
    if dpi_scale <= 0.0:
        raise ValueError("dpi_scale must be positive.")

    return ScreenMetrics(
        width_px=max(1, round(logical_width_px * dpi_scale)),
        height_px=max(1, round(logical_height_px * dpi_scale)),
        origin_x_px=origin_x_px,
        origin_y_px=origin_y_px,
        dpi_scale=dpi_scale,
        display_id=display_id,
        is_primary=is_primary,
    )


def normalized_to_screen(point: NormalizedPoint, metrics: ScreenMetrics) -> ScreenPoint:
    """Convert a normalized point into a physical screen coordinate."""

    return ScreenPoint(
        x_px=_normalized_axis_to_screen(point.x, origin_px=metrics.origin_x_px, span_px=metrics.width_px),
        y_px=_normalized_axis_to_screen(point.y, origin_px=metrics.origin_y_px, span_px=metrics.height_px),
    )


def screen_to_normalized(point: ScreenPoint, metrics: ScreenMetrics) -> NormalizedPoint:
    """Convert a physical screen coordinate into a normalized point."""

    if not _point_within_metrics(point, metrics):
        raise ValueError("Screen point is outside the provided screen metrics.")

    return NormalizedPoint(
        x=(point.x_px - metrics.origin_x_px) / metrics.width_px,
        y=(point.y_px - metrics.origin_y_px) / metrics.height_px,
    )


def bbox_normalized_to_screen(bbox: NormalizedBBox, metrics: ScreenMetrics) -> ScreenBBox:
    """Convert a normalized bounding box into a physical screen bounding box."""

    left_px = _normalized_edge_to_screen(bbox.left, origin_px=metrics.origin_x_px, span_px=metrics.width_px)
    top_px = _normalized_edge_to_screen(bbox.top, origin_px=metrics.origin_y_px, span_px=metrics.height_px)
    right_px = _normalized_edge_to_screen(
        bbox.left + bbox.width,
        origin_px=metrics.origin_x_px,
        span_px=metrics.width_px,
    )
    bottom_px = _normalized_edge_to_screen(
        bbox.top + bbox.height,
        origin_px=metrics.origin_y_px,
        span_px=metrics.height_px,
    )

    return ScreenBBox(
        left_px=left_px,
        top_px=top_px,
        width_px=max(0, right_px - left_px),
        height_px=max(0, bottom_px - top_px),
    )


def _normalized_axis_to_screen(value: float, *, origin_px: int, span_px: int) -> int:
    if value >= 1.0:
        return origin_px + span_px - 1
    return origin_px + floor(value * span_px)


def _normalized_edge_to_screen(value: float, *, origin_px: int, span_px: int) -> int:
    return origin_px + floor((value * span_px) + 1e-9)


def _point_within_metrics(point: ScreenPoint, metrics: ScreenMetrics) -> bool:
    return (
        metrics.origin_x_px <= point.x_px < metrics.right_px
        and metrics.origin_y_px <= point.y_px < metrics.bottom_px
    )
