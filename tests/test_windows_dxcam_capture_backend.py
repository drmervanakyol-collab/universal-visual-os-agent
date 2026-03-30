from __future__ import annotations

from datetime import UTC, datetime

import numpy

from universal_visual_os_agent.geometry import ScreenBBox, ScreenMetrics, ScreenMetricsQueryResult, VirtualDesktopMetrics
from universal_visual_os_agent.integrations.windows import (
    RawWindowsCapture,
    WindowsCaptureBackendCapability,
    WindowsCaptureRequest,
    WindowsCaptureRuntimeMode,
    WindowsCaptureTarget,
    WindowsDxcamCaptureBackend,
    WindowsObserveOnlyCaptureProvider,
)


class FakeScreenMetricsProvider:
    def __init__(self, result: ScreenMetricsQueryResult) -> None:
        self._result = result

    def get_virtual_desktop_metrics(self) -> ScreenMetricsQueryResult:
        return self._result


class FakeCaptureBackend:
    def __init__(
        self,
        *,
        backend_name: str,
        capability: WindowsCaptureBackendCapability,
        capture: RawWindowsCapture,
    ) -> None:
        self.backend_name = backend_name
        self._capability = capability
        self._capture = capture

    def detect_capability(self, request: WindowsCaptureRequest) -> WindowsCaptureBackendCapability:
        return self._capability

    def capture(self, request: WindowsCaptureRequest) -> RawWindowsCapture:
        return self._capture


class FakeDxcamCamera:
    def __init__(self, *, width: int, height: int, frame: object | None = None) -> None:
        self.width = width
        self.height = height
        self._frame = frame
        self.released = False

    def grab(
        self,
        *,
        region: tuple[int, int, int, int] | None = None,
        copy: bool = True,
        new_frame_only: bool = False,
    ) -> object | None:
        return self._frame

    def release(self) -> None:
        self.released = True


class FakeDxcamModule:
    def __init__(
        self,
        *,
        behaviors: dict[str, object],
        device_info: str = "Device[0]:Mock GPU",
        output_info: str = "Device[0] Output[0]: Res:(640, 480) Rot:0 Primary:True",
    ) -> None:
        self._behaviors = behaviors
        self._device_info = device_info
        self._output_info = output_info
        self.create_calls: list[str] = []

    def create(
        self,
        *,
        device_idx: int = 0,
        output_idx: int | None = None,
        region: tuple[int, int, int, int] | None = None,
        output_color: str = "BGRA",
        max_buffer_len: int = 2,
        backend: str = "dxgi",
        processor_backend: str = "numpy",
    ) -> object:
        self.create_calls.append(backend)
        behavior = self._behaviors[backend]
        if isinstance(behavior, Exception):
            raise behavior
        if callable(behavior):
            return behavior()
        return behavior

    def device_info(self) -> str:
        return self._device_info

    def output_info(self) -> str:
        return self._output_info


class RaisingGrabDxcamBackend(WindowsDxcamCaptureBackend):
    def _grab_frame(self, camera: object) -> object:
        raise RuntimeError("dxcam grab failed")


def _single_display_metrics(*, width_px: int = 640, height_px: int = 480) -> VirtualDesktopMetrics:
    return VirtualDesktopMetrics(
        displays=(
            ScreenMetrics(width_px=width_px, height_px=height_px, origin_x_px=0, origin_y_px=0, is_primary=True),
        )
    )


def _success_capture(*, backend_name: str) -> RawWindowsCapture:
    return RawWindowsCapture(
        width=640,
        height=480,
        origin_x_px=0,
        origin_y_px=0,
        row_stride_bytes=640 * 4,
        image_bytes=b"\x00" * (640 * 480 * 4),
        captured_at=datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
        metadata={"backend_name": backend_name},
    )


def _bgra_frame(*, width: int = 640, height: int = 480) -> numpy.ndarray:
    return numpy.zeros((height, width, 4), dtype=numpy.uint8)


def _request() -> WindowsCaptureRequest:
    return WindowsCaptureRequest(
        target=WindowsCaptureTarget.virtual_desktop,
        bounds=ScreenBBox(left_px=0, top_px=0, width_px=640, height_px=480),
    )


def test_dxcam_backend_reports_available_when_primary_output_matches_request() -> None:
    module = FakeDxcamModule(
        behaviors={"dxgi": lambda: FakeDxcamCamera(width=640, height=480), "winrt": RuntimeError("unused")}
    )
    backend = WindowsDxcamCaptureBackend(dxcam_module_loader=lambda: module)

    capability = backend.detect_capability(_request())

    assert capability.available is True
    assert capability.details["dxcam_backend_used"] == "dxgi"
    assert capability.details["camera_width_px"] == 640
    assert capability.details["dxcam_device_info"] == "Device[0]:Mock GPU"


def test_dxcam_backend_reports_unavailable_when_module_is_missing() -> None:
    def loader():
        raise ModuleNotFoundError("No module named 'dxcam'")

    backend = WindowsDxcamCaptureBackend(dxcam_module_loader=loader)

    capability = backend.detect_capability(_request())

    assert capability.available is False
    assert capability.reason == "DXcam is not installed."
    assert capability.details["exception_type"] == "ModuleNotFoundError"


def test_provider_prefers_dxcam_for_full_desktop_requests_when_available() -> None:
    module = FakeDxcamModule(
        behaviors={"dxgi": lambda: FakeDxcamCamera(width=640, height=480, frame=_bgra_frame()), "winrt": RuntimeError("unused")}
    )
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=_single_display_metrics())
        ),
        capture_backends=(
            WindowsDxcamCaptureBackend(dxcam_module_loader=lambda: module),
            FakeCaptureBackend(
                backend_name="gdi_bitblt",
                capability=WindowsCaptureBackendCapability.available_backend(backend_name="gdi_bitblt"),
                capture=_success_capture(backend_name="gdi_bitblt"),
            ),
        ),
    )

    result = provider.capture_frame()

    assert result.success is True
    assert result.details["selected_backend_name"] == "dxcam_desktop"
    assert result.details["used_backend_name"] == "dxcam_desktop"
    assert result.frame is not None
    assert result.frame.metadata["backend_name"] == "dxcam_desktop"
    assert result.frame.metadata["dxcam_backend_used"] == "dxgi"


def test_provider_reports_structured_dxcam_unavailability_without_gdi_fallback_in_production() -> None:
    def loader():
        raise ModuleNotFoundError("No module named 'dxcam'")

    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=_single_display_metrics())
        ),
        capture_backends=(
            WindowsDxcamCaptureBackend(dxcam_module_loader=loader),
            FakeCaptureBackend(
                backend_name="gdi_bitblt",
                capability=WindowsCaptureBackendCapability.available_backend(backend_name="gdi_bitblt"),
                capture=_success_capture(backend_name="gdi_bitblt"),
            ),
        ),
    )

    result = provider.capture_frame()

    assert result.success is False
    assert result.error_code == "capture_backend_unavailable"
    assert result.details["runtime_mode"] == WindowsCaptureRuntimeMode.production
    assert result.details["selected_backend_name"] is None
    assert result.details["available_backend_names"] == ()
    assert result.details["capability_available_backend_names"] == ("gdi_bitblt",)
    candidates = result.details["backend_candidates"]
    assert candidates[0]["backend_name"] == "dxcam_desktop"
    assert candidates[0]["available"] is False
    assert candidates[0]["capability_reason"] == "DXcam is not installed."
    assert candidates[1]["backend_name"] == "gdi_bitblt"
    assert candidates[1]["available"] is True
    assert candidates[1]["runtime_eligible"] is False
    assert (
        candidates[1]["skip_reason"]
        == "Diagnostic-only backend is disabled in the production capture runtime."
    )


def test_provider_reports_structured_dxcam_unavailability_and_uses_gdi_in_diagnostic_mode() -> None:
    def loader():
        raise ModuleNotFoundError("No module named 'dxcam'")

    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=_single_display_metrics())
        ),
        capture_backends=(
            WindowsDxcamCaptureBackend(dxcam_module_loader=loader),
            FakeCaptureBackend(
                backend_name="gdi_bitblt",
                capability=WindowsCaptureBackendCapability.available_backend(backend_name="gdi_bitblt"),
                capture=_success_capture(backend_name="gdi_bitblt"),
            ),
        ),
        runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
    )

    result = provider.capture_frame()

    assert result.success is True
    assert result.details["runtime_mode"] == WindowsCaptureRuntimeMode.diagnostic
    assert result.details["selected_backend_name"] == "gdi_bitblt"
    assert result.details["used_backend_name"] == "gdi_bitblt"
    assert result.details["backend_fallback_used"] is False
    candidates = result.details["backend_candidates"]
    assert candidates[0]["backend_name"] == "dxcam_desktop"
    assert candidates[0]["available"] is False
    assert candidates[1]["backend_name"] == "gdi_bitblt"
    assert candidates[1]["runtime_eligible"] is True
    assert (
        candidates[1]["selection_reason"]
        == "Selected as the highest-priority diagnostic-compatible backend."
    )


def test_provider_does_not_fall_back_to_gdi_when_dxcam_capture_fails_in_production() -> None:
    module = FakeDxcamModule(
        behaviors={"dxgi": lambda: FakeDxcamCamera(width=640, height=480), "winrt": RuntimeError("unused")}
    )
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=_single_display_metrics())
        ),
        capture_backends=(
            RaisingGrabDxcamBackend(dxcam_module_loader=lambda: module),
            FakeCaptureBackend(
                backend_name="gdi_bitblt",
                capability=WindowsCaptureBackendCapability.available_backend(backend_name="gdi_bitblt"),
                capture=_success_capture(backend_name="gdi_bitblt"),
            ),
        ),
    )

    result = provider.capture_frame()

    assert result.success is False
    assert result.error_code == "dxcam_grab_failed"
    assert result.details["runtime_mode"] == WindowsCaptureRuntimeMode.production
    assert result.details["selected_backend_name"] == "dxcam_desktop"
    assert result.details["available_backend_names"] == ("dxcam_desktop",)
    assert result.details["capability_available_backend_names"] == ("dxcam_desktop", "gdi_bitblt")
    candidates = result.details["backend_candidates"]
    assert candidates[1]["backend_name"] == "gdi_bitblt"
    assert candidates[1]["runtime_eligible"] is False
    assert (
        candidates[1]["skip_reason"]
        == "Diagnostic-only backend is disabled in the production capture runtime."
    )
    assert result.details["backend_attempt_count"] == 1
    assert result.details["backend_attempts"][0]["backend_name"] == "dxcam_desktop"
    assert result.details["backend_attempts"][0]["error_code"] == "dxcam_grab_failed"


def test_provider_falls_back_to_gdi_when_dxcam_capture_fails_in_diagnostic_mode() -> None:
    module = FakeDxcamModule(
        behaviors={"dxgi": lambda: FakeDxcamCamera(width=640, height=480), "winrt": RuntimeError("unused")}
    )
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=_single_display_metrics())
        ),
        capture_backends=(
            RaisingGrabDxcamBackend(dxcam_module_loader=lambda: module),
            FakeCaptureBackend(
                backend_name="gdi_bitblt",
                capability=WindowsCaptureBackendCapability.available_backend(backend_name="gdi_bitblt"),
                capture=_success_capture(backend_name="gdi_bitblt"),
            ),
        ),
        runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
    )

    result = provider.capture_frame()

    assert result.success is True
    assert result.details["runtime_mode"] == WindowsCaptureRuntimeMode.diagnostic
    assert result.details["selected_backend_name"] == "dxcam_desktop"
    assert result.details["used_backend_name"] == "gdi_bitblt"
    assert result.details["backend_fallback_used"] is True
    assert result.details["backend_attempts"][0]["backend_name"] == "dxcam_desktop"
    assert result.details["backend_attempts"][0]["error_code"] == "dxcam_grab_failed"


def test_dxcam_backend_preserves_observe_only_semantics_with_structured_failure() -> None:
    module = FakeDxcamModule(
        behaviors={"dxgi": PermissionError("access denied"), "winrt": ModuleNotFoundError("optional extra missing")}
    )
    backend = WindowsDxcamCaptureBackend(dxcam_module_loader=lambda: module)

    capability = backend.detect_capability(_request())

    assert capability.available is False
    assert capability.details["preferred_for_virtual_desktop"] is True
    assert capability.details["implementation_complete"] is True
    assert capability.details["dxcam_attempts"][0]["dxcam_backend"] == "dxgi"
