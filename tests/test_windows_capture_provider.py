from __future__ import annotations

from datetime import UTC, datetime

import pytest

from universal_visual_os_agent.geometry import ScreenMetrics, ScreenMetricsQueryResult, VirtualDesktopMetrics
from universal_visual_os_agent.integrations.windows import (
    RawWindowsCapture,
    WindowsCaptureUnavailableError,
    WindowsObserveOnlyCaptureProvider,
)
from universal_visual_os_agent.perception import CaptureResult, FramePixelFormat


class FakeScreenMetricsProvider:
    def __init__(self, result: ScreenMetricsQueryResult) -> None:
        self._result = result

    def get_virtual_desktop_metrics(self) -> ScreenMetricsQueryResult:
        return self._result


class FakeWindowsScreenCaptureApi:
    def __init__(self, capture: RawWindowsCapture) -> None:
        self._capture = capture
        self.seen_bounds = None

    def capture_bounds(self, bounds) -> RawWindowsCapture:
        self.seen_bounds = bounds
        return self._capture


class UnavailableWindowsScreenCaptureApi:
    def capture_bounds(self, bounds) -> RawWindowsCapture:
        del bounds
        raise WindowsCaptureUnavailableError("Capture APIs are unavailable in this test environment.")


def test_provider_output_shape_includes_frame_payload_and_details() -> None:
    metrics = VirtualDesktopMetrics(
        displays=(
            ScreenMetrics(width_px=640, height_px=480, origin_x_px=0, origin_y_px=0, is_primary=True),
        )
    )
    captured_at = datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC)
    capture_api = FakeWindowsScreenCaptureApi(
        RawWindowsCapture(
            width=640,
            height=480,
            origin_x_px=0,
            origin_y_px=0,
            row_stride_bytes=640 * 4,
            image_bytes=b"\x00" * (640 * 480 * 4),
            captured_at=captured_at,
        )
    )
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=metrics)
        ),
        capture_api=capture_api,
    )

    result = provider.capture_frame()

    assert isinstance(result, CaptureResult)
    assert result.success is True
    assert result.frame is not None
    assert result.provider_name == "WindowsObserveOnlyCaptureProvider"
    assert result.details["display_count"] == 1
    assert capture_api.seen_bounds == metrics.bounds
    assert result.frame.source == "WindowsObserveOnlyCaptureProvider"
    assert result.frame.payload is not None
    assert result.frame.payload.pixel_format is FramePixelFormat.bgra_8888
    assert result.frame.payload.row_stride_bytes == 640 * 4


def test_provider_returns_safe_failure_when_capture_is_unavailable() -> None:
    metrics = VirtualDesktopMetrics(
        displays=(
            ScreenMetrics(width_px=320, height_px=200, origin_x_px=0, origin_y_px=0, is_primary=True),
        )
    )
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=metrics)
        ),
        capture_api=UnavailableWindowsScreenCaptureApi(),
    )

    result = provider.capture_frame()

    assert result.success is False
    assert result.frame is None
    assert result.error_code == "capture_unavailable"
    assert "unavailable" in (result.error_message or "")


def test_provider_returns_safe_failure_when_screen_metrics_are_unavailable() -> None:
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.failure(
                provider_name="FakeScreenMetricsProvider",
                error_code="windows_api_unavailable",
                error_message="Screen metrics APIs are unavailable.",
            )
        ),
        capture_api=UnavailableWindowsScreenCaptureApi(),
    )

    result = provider.capture_frame()

    assert result.success is False
    assert result.frame is None
    assert result.error_code == "screen_metrics_unavailable"
    assert result.details["metrics_error_code"] == "windows_api_unavailable"


def test_frame_metadata_preserves_width_height_timestamp_and_origin() -> None:
    metrics = VirtualDesktopMetrics(
        displays=(
            ScreenMetrics(width_px=300, height_px=200, origin_x_px=-50, origin_y_px=10, is_primary=True),
        )
    )
    captured_at = datetime(2026, 3, 30, 12, 34, 56, 123456, tzinfo=UTC)
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=metrics)
        ),
        capture_api=FakeWindowsScreenCaptureApi(
            RawWindowsCapture(
                width=300,
                height=200,
                origin_x_px=-50,
                origin_y_px=10,
                row_stride_bytes=300 * 4,
                image_bytes=b"\x01" * (300 * 200 * 4),
                captured_at=captured_at,
            )
        ),
    )

    result = provider.capture_frame()

    assert result.success is True
    assert result.frame is not None
    assert result.frame.width == 300
    assert result.frame.height == 200
    assert result.frame.captured_at == captured_at
    assert result.frame.metadata["origin_x_px"] == -50
    assert result.frame.metadata["origin_y_px"] == 10
    assert result.frame.metadata["display_count"] == 1
    assert result.frame.frame_id.startswith("capture-20260330T123456123456Z")


@pytest.mark.parametrize(
    ("frame_kwargs", "message"),
    [
        (
            {
                "frame_id": "frame-1",
                "width": 0,
                "height": 10,
                "captured_at": datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
            },
            "width must be positive",
        ),
        (
            {
                "frame_id": "frame-2",
                "width": 10,
                "height": 10,
                "captured_at": datetime(2026, 3, 30, 12, 0, 0),
            },
            "captured_at must be timezone-aware",
        ),
    ],
)
def test_captured_frame_abstraction_validates_width_height_and_timestamp(
    frame_kwargs: dict[str, object],
    message: str,
) -> None:
    from universal_visual_os_agent.perception import CapturedFrame

    with pytest.raises(ValueError, match=message):
        CapturedFrame(**frame_kwargs)
