from __future__ import annotations

from datetime import UTC, datetime

import pytest

from universal_visual_os_agent.geometry import ScreenBBox, ScreenMetrics, ScreenMetricsQueryResult, VirtualDesktopMetrics
from universal_visual_os_agent.integrations.windows import (
    RawWindowsCapture,
    WindowsCaptureBackendCapability,
    WindowsCaptureRequest,
    WindowsCaptureRuntimeMode,
    WindowsCaptureStageError,
    WindowsCaptureTarget,
    WindowsForegroundWindowPrintCaptureBackend,
    WindowsObserveOnlyCaptureProvider,
)
from universal_visual_os_agent.perception import CaptureResult, FramePixelFormat


class FakeScreenMetricsProvider:
    def __init__(self, result: ScreenMetricsQueryResult) -> None:
        self._result = result
        self.calls = 0

    def get_virtual_desktop_metrics(self) -> ScreenMetricsQueryResult:
        self.calls += 1
        return self._result


class RaisingScreenMetricsProvider:
    def get_virtual_desktop_metrics(self) -> ScreenMetricsQueryResult:
        raise AssertionError("screen metrics should not be used for this capture target")


class FakeCaptureBackend:
    def __init__(
        self,
        *,
        backend_name: str,
        capability: WindowsCaptureBackendCapability,
        capture: RawWindowsCapture | None = None,
        capture_error: Exception | None = None,
        detect_error: Exception | None = None,
    ) -> None:
        self.backend_name = backend_name
        self._capability = capability
        self._capture = capture
        self._capture_error = capture_error
        self._detect_error = detect_error
        self.detect_requests: list[WindowsCaptureRequest] = []
        self.capture_requests: list[WindowsCaptureRequest] = []

    def detect_capability(self, request: WindowsCaptureRequest) -> WindowsCaptureBackendCapability:
        self.detect_requests.append(request)
        if self._detect_error is not None:
            raise self._detect_error
        return self._capability

    def capture(self, request: WindowsCaptureRequest) -> RawWindowsCapture:
        self.capture_requests.append(request)
        if self._capture_error is not None:
            raise self._capture_error
        if self._capture is None:
            raise AssertionError("Fake capture backend is missing capture data.")
        return self._capture


class TestablePrintWindowBackend(WindowsForegroundWindowPrintCaptureBackend):
    def _is_windows_platform(self) -> bool:
        return True

    def _detect_foreground_window_handle(self) -> int | None:
        return 1234


class ScriptedPrintWindowBackend(WindowsForegroundWindowPrintCaptureBackend):
    def __init__(
        self,
        *,
        detected_handles: tuple[int | None, ...] = (1234,),
        valid_handle: bool = True,
        visible: bool = True,
        minimized: bool = False,
        bounds: ScreenBBox | None = None,
        bounds_error: WindowsCaptureStageError | None = None,
        capture_result: RawWindowsCapture | None = None,
        capture_error: WindowsCaptureStageError | None = None,
        environment_details: dict[str, object] | None = None,
    ) -> None:
        self._detected_handles = detected_handles
        self._detected_handle_index = 0
        self._valid_handle = valid_handle
        self._visible = visible
        self._minimized = minimized
        self._bounds = bounds or ScreenBBox(left_px=10, top_px=20, width_px=300, height_px=200)
        self._bounds_error = bounds_error
        self._capture_result = capture_result or _success_capture(
            width=self._bounds.width_px,
            height=self._bounds.height_px,
            origin_x_px=self._bounds.left_px,
            origin_y_px=self._bounds.top_px,
            backend_name="printwindow_foreground",
        )
        self._capture_error = capture_error
        self._environment_details = {
            "backend_name": self.backend_name,
            "platform": "win32",
            "session_name": "Console",
            "is_remote_session": False,
            "input_desktop_accessible": True,
        }
        if environment_details is not None:
            self._environment_details.update(environment_details)

    def _is_windows_platform(self) -> bool:
        return True

    def _detect_foreground_window_handle(self) -> int | None:
        if self._detected_handle_index < len(self._detected_handles):
            handle = self._detected_handles[self._detected_handle_index]
            self._detected_handle_index += 1
            return handle
        return self._detected_handles[-1] if self._detected_handles else None

    def _is_window_handle_valid(self, window_handle: int) -> bool:
        return self._valid_handle

    def _is_window_visible(self, window_handle: int) -> bool:
        return self._visible

    def _is_window_minimized(self, window_handle: int) -> bool:
        return self._minimized

    def _get_window_bounds(self, window_handle: int) -> ScreenBBox:
        if self._bounds_error is not None:
            raise self._bounds_error
        return self._bounds

    def _capture_environment_details(self) -> dict[str, object]:
        return dict(self._environment_details)

    def _capture_window_image(
        self,
        *,
        window_handle: int,
        bounds: ScreenBBox,
        attempt: object,
        requested_window_handle: int | None,
        detected_foreground_window_handle: int | None,
        environment_details: object,
    ) -> RawWindowsCapture:
        if self._capture_error is not None:
            raise self._capture_error
        return self._capture_result


def _single_display_metrics(*, width_px: int = 640, height_px: int = 480) -> VirtualDesktopMetrics:
    return VirtualDesktopMetrics(
        displays=(
            ScreenMetrics(width_px=width_px, height_px=height_px, origin_x_px=0, origin_y_px=0, is_primary=True),
        )
    )


def _success_capture(
    *,
    width: int = 640,
    height: int = 480,
    origin_x_px: int = 0,
    origin_y_px: int = 0,
    backend_name: str,
) -> RawWindowsCapture:
    return RawWindowsCapture(
        width=width,
        height=height,
        origin_x_px=origin_x_px,
        origin_y_px=origin_y_px,
        row_stride_bytes=width * 4,
        image_bytes=b"\x00" * (width * height * 4),
        captured_at=datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
        metadata={"backend_name": backend_name},
    )


def test_backend_selection_prefers_first_available_backend_and_reports_candidates() -> None:
    metrics = _single_display_metrics()
    unavailable_backend = FakeCaptureBackend(
        backend_name="printwindow_foreground",
        capability=WindowsCaptureBackendCapability.unavailable_backend(
            backend_name="printwindow_foreground",
            reason="PrintWindow backend only supports foreground_window requests.",
        ),
    )
    gdi_backend = FakeCaptureBackend(
        backend_name="gdi_bitblt",
        capability=WindowsCaptureBackendCapability.available_backend(backend_name="gdi_bitblt"),
        capture=_success_capture(backend_name="gdi_bitblt"),
    )
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=metrics)
        ),
        capture_backends=(unavailable_backend, gdi_backend),
        runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
    )

    result = provider.capture_frame()

    assert isinstance(result, CaptureResult)
    assert result.success is True
    assert result.frame is not None
    assert result.details["capture_target"] == WindowsCaptureTarget.virtual_desktop
    assert result.details["selected_backend_name"] == "gdi_bitblt"
    assert result.details["used_backend_name"] == "gdi_bitblt"
    assert result.details["backend_fallback_used"] is False
    assert result.details["available_backend_names"] == ("gdi_bitblt",)
    candidates = result.details["backend_candidates"]
    assert isinstance(candidates, tuple)
    assert candidates[0]["backend_name"] == "printwindow_foreground"
    assert candidates[0]["available"] is False
    assert candidates[1]["backend_name"] == "gdi_bitblt"
    assert candidates[1]["available"] is True


def test_production_runtime_skips_diagnostic_only_gdi_backend_with_stable_reason() -> None:
    metrics = _single_display_metrics()
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=metrics)
        ),
        capture_backends=(
            FakeCaptureBackend(
                backend_name="gdi_bitblt",
                capability=WindowsCaptureBackendCapability.available_backend(
                    backend_name="gdi_bitblt"
                ),
                capture=_success_capture(backend_name="gdi_bitblt"),
            ),
        ),
    )

    result = provider.capture_frame()

    assert result.success is False
    assert result.error_code == "capture_backend_unavailable"
    assert result.details["runtime_mode"] == WindowsCaptureRuntimeMode.production
    assert result.details["selected_backend_name"] is None
    candidate = result.details["backend_candidates"][0]
    assert candidate["backend_name"] == "gdi_bitblt"
    assert candidate["available"] is True
    assert candidate["diagnostic_only"] is True
    assert candidate["runtime_eligible"] is False
    assert (
        candidate["skip_reason"]
        == "Diagnostic-only backend is disabled in the production capture runtime."
    )


def test_printwindow_backend_reports_unavailable_for_virtual_desktop_target() -> None:
    backend = TestablePrintWindowBackend()

    capability = backend.detect_capability(
        WindowsCaptureRequest(
            target=WindowsCaptureTarget.virtual_desktop,
            bounds=ScreenBBox(left_px=0, top_px=0, width_px=100, height_px=100),
        )
    )

    assert capability.available is False
    assert capability.backend_name == "printwindow_foreground"
    assert "foreground_window" in capability.reason


def test_printwindow_backend_reports_unavailable_when_no_foreground_window_exists() -> None:
    backend = ScriptedPrintWindowBackend(detected_handles=(None,))

    capability = backend.detect_capability(WindowsCaptureRequest(target=WindowsCaptureTarget.foreground_window))

    assert capability.available is False
    assert capability.reason == "No foreground window is available for PrintWindow capture."
    assert capability.details["target"] == WindowsCaptureTarget.foreground_window


def test_printwindow_backend_reports_unavailable_when_foreground_window_is_minimized() -> None:
    backend = ScriptedPrintWindowBackend(minimized=True)

    capability = backend.detect_capability(WindowsCaptureRequest(target=WindowsCaptureTarget.foreground_window))

    assert capability.available is False
    assert capability.reason == "Foreground window is minimized and will not be captured."
    assert capability.details["window_minimized"] is True


def test_printwindow_backend_reports_unavailable_when_foreground_window_is_invisible() -> None:
    backend = ScriptedPrintWindowBackend(visible=False)

    capability = backend.detect_capability(WindowsCaptureRequest(target=WindowsCaptureTarget.foreground_window))

    assert capability.available is False
    assert capability.reason == "Foreground window is not visible for PrintWindow capture."
    assert capability.details["window_visible"] is False


def test_printwindow_capture_rejects_unsupported_target_with_structured_stage() -> None:
    backend = ScriptedPrintWindowBackend()

    with pytest.raises(WindowsCaptureStageError) as exc_info:
        backend.capture(
            WindowsCaptureRequest(
                target=WindowsCaptureTarget.virtual_desktop,
                bounds=ScreenBBox(left_px=0, top_px=0, width_px=100, height_px=100),
            )
        )

    assert exc_info.value.stage == "unsupported_request_target"
    assert exc_info.value.diagnostics["backend_name"] == "printwindow_foreground"
    assert exc_info.value.diagnostics["target"] == WindowsCaptureTarget.virtual_desktop


def test_printwindow_capture_reports_no_foreground_window_with_structured_diagnostics() -> None:
    backend = ScriptedPrintWindowBackend(detected_handles=(None,))

    with pytest.raises(WindowsCaptureStageError) as exc_info:
        backend.capture(WindowsCaptureRequest(target=WindowsCaptureTarget.foreground_window))

    assert exc_info.value.stage == "detect_target_window"
    assert exc_info.value.diagnostics["failure_classification"] == "no_foreground_window"
    assert exc_info.value.diagnostics["platform"] == "win32"
    assert exc_info.value.diagnostics["target_window_resolved"] is False


def test_printwindow_capture_reports_invalid_window_handle_with_structured_diagnostics() -> None:
    backend = ScriptedPrintWindowBackend(valid_handle=False)

    with pytest.raises(WindowsCaptureStageError) as exc_info:
        backend.capture(WindowsCaptureRequest(target=WindowsCaptureTarget.foreground_window))

    assert exc_info.value.stage == "validate_window_handle"
    assert exc_info.value.diagnostics["failure_classification"] == "inaccessible_window_handle"
    assert exc_info.value.diagnostics["target_window_handle"] == 1234
    assert exc_info.value.diagnostics["window_handle_validated"] is False


def test_printwindow_capture_reports_foreground_window_change_before_capture() -> None:
    backend = ScriptedPrintWindowBackend(detected_handles=(1234, 4321))

    with pytest.raises(WindowsCaptureStageError) as exc_info:
        backend.capture(WindowsCaptureRequest(target=WindowsCaptureTarget.foreground_window))

    assert exc_info.value.stage == "foreground_window_changed"
    assert exc_info.value.diagnostics["failure_classification"] == "foreground_window_changed"
    assert exc_info.value.diagnostics["foreground_window_change_phase"] == "before_capture"
    assert exc_info.value.diagnostics["current_foreground_window_handle"] == 4321


def test_printwindow_capture_reports_printwindow_failure_details() -> None:
    backend = ScriptedPrintWindowBackend(
        capture_error=WindowsCaptureStageError(
            stage="print_window",
            message="PrintWindow failed for all supported flags.",
            diagnostics={
                "failure_classification": "printwindow_failed",
                "print_window_attempts": (
                    {
                        "print_window_flag": 0,
                        "print_window_flag_name": "PW_DEFAULT",
                        "printed": False,
                    },
                ),
                "environment_limitation_suspected": True,
                "environment_limitation_reasons": ("printwindow_returned_failure_without_last_error",),
            },
        )
    )

    with pytest.raises(WindowsCaptureStageError) as exc_info:
        backend.capture(WindowsCaptureRequest(target=WindowsCaptureTarget.foreground_window))

    assert exc_info.value.stage == "print_window"
    assert exc_info.value.diagnostics["failure_classification"] == "printwindow_failed"
    assert exc_info.value.diagnostics["environment_limitation_suspected"] is True
    assert exc_info.value.diagnostics["print_window_attempts"][0]["print_window_flag_name"] == "PW_DEFAULT"
    assert exc_info.value.diagnostics["window_visible"] is True


def test_provider_distinguishes_bitmap_readback_failure_for_printwindow_backend() -> None:
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=RaisingScreenMetricsProvider(),
        capture_target=WindowsCaptureTarget.foreground_window,
        capture_backends=(
            ScriptedPrintWindowBackend(
                capture_error=WindowsCaptureStageError(
                    stage="get_dibits",
                    message="GetDIBits failed.",
                    diagnostics={"failure_classification": "bitmap_readback_failed"},
                ),
            ),
        ),
        runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
    )

    result = provider.capture_frame()

    assert result.success is False
    assert result.error_code == "bitmap_read_failed"
    assert result.details["failing_stage"] == "get_dibits"
    assert result.details["backend_attempts"][0]["failure_classification"] == "bitmap_readback_failed"


def test_provider_surfaces_printwindow_stage_failure_without_unhandled_exception() -> None:
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=RaisingScreenMetricsProvider(),
        capture_target=WindowsCaptureTarget.foreground_window,
        capture_backends=(
            ScriptedPrintWindowBackend(
                capture_error=WindowsCaptureStageError(
                    stage="print_window",
                    message="PrintWindow failed for all supported flags.",
                    diagnostics={
                        "failure_classification": "printwindow_failed",
                        "environment_limitation_suspected": True,
                    },
                ),
            ),
        ),
        runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
    )

    result = provider.capture_frame()

    assert result.success is False
    assert result.error_code == "window_print_failed"
    assert result.details["failing_stage"] == "print_window"
    assert result.details["backend_attempts"][0]["failure_classification"] == "printwindow_failed"
    assert result.details["backend_attempts"][0]["environment_limitation_suspected"] is True


def test_provider_reports_structured_unavailable_backend_selection() -> None:
    metrics = _single_display_metrics()
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=metrics)
        ),
        capture_backends=(
            FakeCaptureBackend(
                backend_name="gdi_bitblt",
                capability=WindowsCaptureBackendCapability.unavailable_backend(
                    backend_name="gdi_bitblt",
                    reason="GDI backend was disabled for this test.",
                ),
            ),
            FakeCaptureBackend(
                backend_name="printwindow_foreground",
                capability=WindowsCaptureBackendCapability.unavailable_backend(
                    backend_name="printwindow_foreground",
                    reason="PrintWindow backend only supports foreground_window requests.",
                ),
            ),
        ),
    )

    result = provider.capture_frame()

    assert result.success is False
    assert result.error_code == "capture_backend_unavailable"
    assert result.details["failing_stage"] == "backend_selection"
    assert result.details["selected_backend_name"] is None
    assert result.details["available_backend_names"] == ()


def test_provider_uses_backend_fallback_order_explicitly() -> None:
    metrics = _single_display_metrics()
    first_backend = FakeCaptureBackend(
        backend_name="gdi_bitblt",
        capability=WindowsCaptureBackendCapability.available_backend(backend_name="gdi_bitblt"),
        capture_error=WindowsCaptureStageError(
            stage="bit_blt",
            message="BitBlt failed.",
            win32_error_code=6,
            diagnostics={"backend_name": "gdi_bitblt"},
        ),
    )
    second_backend = FakeCaptureBackend(
        backend_name="legacy_safe_backend",
        capability=WindowsCaptureBackendCapability.available_backend(backend_name="legacy_safe_backend"),
        capture=_success_capture(backend_name="legacy_safe_backend"),
    )
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=metrics)
        ),
        capture_backends=(first_backend, second_backend),
        runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
    )

    result = provider.capture_frame()

    assert result.success is True
    assert result.details["selected_backend_name"] == "gdi_bitblt"
    assert result.details["used_backend_name"] == "legacy_safe_backend"
    assert result.details["backend_fallback_used"] is True
    assert result.details["backend_attempt_count"] == 2
    backend_attempts = result.details["backend_attempts"]
    assert isinstance(backend_attempts, tuple)
    assert backend_attempts[0]["backend_name"] == "gdi_bitblt"
    assert backend_attempts[0]["failing_stage"] == "bit_blt"


def test_capability_detection_exceptions_do_not_escape_provider() -> None:
    metrics = _single_display_metrics()
    failing_backend = FakeCaptureBackend(
        backend_name="broken_detector",
        capability=WindowsCaptureBackendCapability.available_backend(backend_name="broken_detector"),
        detect_error=RuntimeError("capability probe failed"),
    )
    fallback_backend = FakeCaptureBackend(
        backend_name="gdi_bitblt",
        capability=WindowsCaptureBackendCapability.available_backend(backend_name="gdi_bitblt"),
        capture=_success_capture(backend_name="gdi_bitblt"),
    )
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=metrics)
        ),
        capture_backends=(failing_backend, fallback_backend),
        runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
    )

    result = provider.capture_frame()

    assert result.success is True
    candidates = result.details["backend_candidates"]
    broken_detector = next(
        candidate for candidate in candidates if candidate["backend_name"] == "broken_detector"
    )
    assert broken_detector["available"] is False
    assert broken_detector["details"]["exception_type"] == "RuntimeError"
    assert result.details["used_backend_name"] == "gdi_bitblt"


def test_provider_converts_unexpected_backend_exceptions_to_safe_failure() -> None:
    metrics = _single_display_metrics()
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=metrics)
        ),
        capture_backends=(
            FakeCaptureBackend(
                backend_name="gdi_bitblt",
                capability=WindowsCaptureBackendCapability.available_backend(backend_name="gdi_bitblt"),
                capture_error=RuntimeError("unexpected backend failure"),
                ),
            ),
        runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
    )

    result = provider.capture_frame()

    assert result.success is False
    assert result.error_code == "capture_internal_error"
    assert result.details["backend_attempt_count"] == 1
    assert result.details["backend_attempts"][0]["exception_type"] == "RuntimeError"


def test_foreground_window_target_skips_metrics_lookup_and_can_use_window_backend() -> None:
    window_backend = FakeCaptureBackend(
        backend_name="printwindow_foreground",
        capability=WindowsCaptureBackendCapability.available_backend(backend_name="printwindow_foreground"),
        capture=_success_capture(width=300, height=200, origin_x_px=10, origin_y_px=20, backend_name="printwindow_foreground"),
    )
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=RaisingScreenMetricsProvider(),
        capture_target=WindowsCaptureTarget.foreground_window,
        capture_backends=(window_backend,),
        runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
    )

    result = provider.capture_frame()

    assert result.success is True
    assert result.details["capture_target"] == WindowsCaptureTarget.foreground_window
    assert result.details["metrics_required"] is False
    assert result.details["metrics_lookup_succeeded"] is False
    assert result.details["used_backend_name"] == "printwindow_foreground"


def test_frame_metadata_preserves_width_height_timestamp_and_backend_metadata() -> None:
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
        capture_backends=(
            FakeCaptureBackend(
                backend_name="gdi_bitblt",
                capability=WindowsCaptureBackendCapability.available_backend(backend_name="gdi_bitblt"),
                capture=RawWindowsCapture(
                    width=300,
                    height=200,
                    origin_x_px=-50,
                    origin_y_px=10,
                    row_stride_bytes=300 * 4,
                    image_bytes=b"\x01" * (300 * 200 * 4),
                    captured_at=captured_at,
                    metadata={"backend_name": "gdi_bitblt", "capture_source_strategy": "screen_dc"},
                ),
                ),
            ),
        runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
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
    assert result.frame.metadata["backend_name"] == "gdi_bitblt"
    assert result.frame.metadata["capture_source_strategy"] == "screen_dc"
    assert result.frame.payload is not None
    assert result.frame.payload.pixel_format is FramePixelFormat.bgra_8888
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
