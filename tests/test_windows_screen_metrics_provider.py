from __future__ import annotations

from universal_visual_os_agent.geometry import ScreenMetrics, VirtualDesktopMetrics
from universal_visual_os_agent.integrations.windows import (
    RawWindowsMonitorMetrics,
    WindowsApiUnavailableError,
    WindowsScreenMetricsProvider,
)


class FakeWindowsMonitorApi:
    def __init__(self, monitors: tuple[RawWindowsMonitorMetrics, ...]) -> None:
        self._monitors = monitors

    def list_monitors(self) -> tuple[RawWindowsMonitorMetrics, ...]:
        return self._monitors


class UnavailableWindowsMonitorApi:
    def list_monitors(self) -> tuple[RawWindowsMonitorMetrics, ...]:
        raise WindowsApiUnavailableError("Windows APIs are not available in this test environment.")


def test_provider_returns_geometry_compatible_metrics() -> None:
    provider = WindowsScreenMetricsProvider(
        api=FakeWindowsMonitorApi(
            monitors=(
                RawWindowsMonitorMetrics(
                    left_px=0,
                    top_px=0,
                    right_px=1920,
                    bottom_px=1080,
                    is_primary=True,
                    dpi_x=96,
                    dpi_y=96,
                    display_id="DISPLAY1",
                ),
            )
        )
    )

    result = provider.get_virtual_desktop_metrics()

    assert result.success is True
    assert isinstance(result.metrics, VirtualDesktopMetrics)
    assert isinstance(result.metrics.primary_display, ScreenMetrics)
    assert result.metrics.primary_display.display_id == "DISPLAY1"


def test_provider_output_shape_includes_multi_monitor_bounds_and_dpi() -> None:
    provider = WindowsScreenMetricsProvider(
        api=FakeWindowsMonitorApi(
            monitors=(
                RawWindowsMonitorMetrics(
                    left_px=-1280,
                    top_px=120,
                    right_px=0,
                    bottom_px=1144,
                    dpi_x=96,
                    dpi_y=96,
                    display_id="DISPLAY-LEFT",
                ),
                RawWindowsMonitorMetrics(
                    left_px=0,
                    top_px=0,
                    right_px=2560,
                    bottom_px=1440,
                    is_primary=True,
                    dpi_x=144,
                    dpi_y=144,
                    display_id="DISPLAY-PRIMARY",
                ),
            )
        )
    )

    result = provider.get_virtual_desktop_metrics()

    assert result.success is True
    assert result.provider_name == "WindowsScreenMetricsProvider"
    assert result.error_code is None
    assert result.metrics is not None
    assert result.details["display_count"] == 2
    assert result.metrics.primary_display.display_id == "DISPLAY-PRIMARY"
    assert result.metrics.primary_display.is_primary is True
    assert result.metrics.primary_display.dpi_scale == 1.5
    assert result.metrics.bounds.left_px == -1280
    assert result.metrics.bounds.top_px == 0
    assert result.metrics.bounds.width_px == 3840
    assert result.metrics.bounds.height_px == 1440


def test_provider_returns_safe_failure_when_windows_apis_are_unavailable() -> None:
    provider = WindowsScreenMetricsProvider(api=UnavailableWindowsMonitorApi())

    result = provider.get_virtual_desktop_metrics()

    assert result.success is False
    assert result.metrics is None
    assert result.error_code == "windows_api_unavailable"
    assert "not available" in (result.error_message or "")


def test_provider_preserves_negative_coordinates_in_virtual_desktop_layout() -> None:
    provider = WindowsScreenMetricsProvider(
        api=FakeWindowsMonitorApi(
            monitors=(
                RawWindowsMonitorMetrics(
                    left_px=-1920,
                    top_px=-200,
                    right_px=0,
                    bottom_px=880,
                    dpi_x=120,
                    dpi_y=120,
                    display_id="DISPLAY-WEST",
                ),
                RawWindowsMonitorMetrics(
                    left_px=0,
                    top_px=-100,
                    right_px=1920,
                    bottom_px=980,
                    is_primary=True,
                    dpi_x=96,
                    dpi_y=96,
                    display_id="DISPLAY-EAST",
                ),
            )
        )
    )

    result = provider.get_virtual_desktop_metrics()

    assert result.success is True
    assert result.metrics is not None
    assert result.metrics.bounds.left_px == -1920
    assert result.metrics.bounds.top_px == -200
    assert result.metrics.bounds.width_px == 3840
    assert result.metrics.bounds.height_px == 1180
