from __future__ import annotations

import math

import pytest

from universal_visual_os_agent.geometry import (
    NormalizedBBox,
    NormalizedPoint,
    ScreenMetrics,
    ScreenPoint,
    VirtualDesktopMetrics,
    bbox_normalized_to_screen,
    dpi_aware_screen_metrics,
    normalized_to_screen,
    screen_to_normalized,
)


def test_normalized_round_trip_on_single_display() -> None:
    metrics = ScreenMetrics(width_px=200, height_px=100, origin_x_px=-50, origin_y_px=30, is_primary=True)
    normalized = NormalizedPoint(x=0.25, y=0.75)

    screen_point = normalized_to_screen(normalized, metrics)
    round_tripped = screen_to_normalized(screen_point, metrics)

    assert screen_point.x_px == 0
    assert screen_point.y_px == 105
    assert math.isclose(round_tripped.x, normalized.x)
    assert math.isclose(round_tripped.y, normalized.y)


def test_dpi_aware_screen_metrics_scales_logical_dimensions() -> None:
    metrics = dpi_aware_screen_metrics(
        logical_width_px=1280,
        logical_height_px=720,
        dpi_scale=1.5,
        is_primary=True,
    )
    screen_point = normalized_to_screen(NormalizedPoint(x=0.5, y=0.5), metrics)

    assert metrics.width_px == 1920
    assert metrics.height_px == 1080
    assert math.isclose(metrics.logical_width_px, 1280.0)
    assert math.isclose(metrics.logical_height_px, 720.0)
    assert screen_point.x_px == 960
    assert screen_point.y_px == 540


def test_negative_origin_and_virtual_desktop_bounds_are_supported() -> None:
    left_display = ScreenMetrics(
        width_px=1600,
        height_px=900,
        origin_x_px=-1600,
        origin_y_px=120,
        display_id="left",
    )
    primary_display = ScreenMetrics(
        width_px=1920,
        height_px=1080,
        origin_x_px=0,
        origin_y_px=0,
        display_id="primary",
        is_primary=True,
    )
    desktop = VirtualDesktopMetrics(displays=(left_display, primary_display))
    screen_point = normalized_to_screen(NormalizedPoint(x=0.5, y=0.5), left_display)

    assert screen_point == ScreenPoint(x_px=-800, y_px=570)
    assert desktop.primary_display == primary_display
    assert desktop.bounds.left_px == -1600
    assert desktop.bounds.top_px == 0
    assert desktop.bounds.width_px == 3520
    assert desktop.bounds.height_px == 1080


def test_bbox_normalized_to_screen_maps_edges_correctly() -> None:
    metrics = ScreenMetrics(width_px=200, height_px=100)
    bbox = bbox_normalized_to_screen(
        NormalizedBBox(left=0.1, top=0.2, width=0.3, height=0.4),
        metrics,
    )

    assert bbox.left_px == 20
    assert bbox.top_px == 20
    assert bbox.width_px == 60
    assert bbox.height_px == 40


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"x": -0.1, "y": 0.5}, "between 0.0 and 1.0"),
        ({"left": 0.8, "top": 0.0, "width": 0.3, "height": 0.1}, r"left \+ width"),
        ({"left": 0.0, "top": 0.9, "width": 0.1, "height": 0.2}, r"top \+ height"),
    ],
)
def test_invalid_normalized_bounds_raise_value_error(kwargs: dict[str, float], message: str) -> None:
    if "x" in kwargs:
        with pytest.raises(ValueError, match=message):
            NormalizedPoint(**kwargs)
    else:
        with pytest.raises(ValueError, match=message):
            NormalizedBBox(**kwargs)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"width_px": 0, "height_px": 100}, "width_px must be positive"),
        ({"width_px": 100, "height_px": -1}, "height_px must be positive"),
        ({"width_px": 100, "height_px": 100, "dpi_scale": 0.0}, "dpi_scale must be positive"),
        ({"width_px": 100, "height_px": 100, "display_id": ""}, "display_id must not be empty"),
    ],
)
def test_screen_metric_validation_rejects_invalid_values(
    kwargs: dict[str, int | float | str],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ScreenMetrics(**kwargs)


def test_screen_to_normalized_rejects_points_outside_metrics() -> None:
    metrics = ScreenMetrics(width_px=100, height_px=100, origin_x_px=-50, origin_y_px=-50)

    with pytest.raises(ValueError, match="outside the provided screen metrics"):
        screen_to_normalized(ScreenPoint(x_px=50, y_px=50), metrics)


def test_virtual_desktop_validation_rejects_duplicate_display_ids() -> None:
    display_a = ScreenMetrics(width_px=100, height_px=100, display_id="dup")
    display_b = ScreenMetrics(width_px=100, height_px=100, origin_x_px=100, display_id="dup")

    with pytest.raises(ValueError, match="Display identifiers must be unique"):
        VirtualDesktopMetrics(displays=(display_a, display_b))
