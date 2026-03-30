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
    WindowsDesktopDuplicationCaptureBackend,
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
        capture: RawWindowsCapture | None = None,
    ) -> None:
        self.backend_name = backend_name
        self._capability = capability
        self._capture = capture

    def detect_capability(self, request: WindowsCaptureRequest) -> WindowsCaptureBackendCapability:
        return self._capability

    def capture(self, request: WindowsCaptureRequest) -> RawWindowsCapture:
        if self._capture is None:
            raise AssertionError("Fake capture backend is missing capture data.")
        return self._capture


class ScriptedDesktopDuplicationBackend(WindowsDesktopDuplicationCaptureBackend):
    def __init__(self, *, probe_details: dict[str, object], windows_platform: bool = True) -> None:
        self._probe_details = probe_details
        self._windows_platform = windows_platform

    def _is_windows_platform(self) -> bool:
        return self._windows_platform

    def _probe_desktop_duplication_details(self, bounds: ScreenBBox) -> dict[str, object]:
        return {
            "backend_name": self.backend_name,
            "capture_api": "dxgi_desktop_duplication",
            "capture_target": WindowsCaptureTarget.virtual_desktop,
            "bounds_left_px": bounds.left_px,
            "bounds_top_px": bounds.top_px,
            "bounds_width_px": bounds.width_px,
            "bounds_height_px": bounds.height_px,
            "preferred_for_virtual_desktop": True,
            "implementation_status": "capability_probe_only",
            "implementation_complete": False,
            "com_binding_implemented": False,
            "platform": "win32",
            "session_name": "Console",
            "runtime_supported_os": True,
            "dxgi_library_loadable": True,
            "d3d11_library_loadable": True,
            "environment_limitation_suspected": False,
            "environment_limitation_reasons": (),
            **self._probe_details,
        }


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


def test_desktop_duplication_backend_reports_incomplete_capability_with_probe_details() -> None:
    backend = ScriptedDesktopDuplicationBackend(probe_details={})

    capability = backend.detect_capability(
        WindowsCaptureRequest(
            target=WindowsCaptureTarget.virtual_desktop,
            bounds=ScreenBBox(left_px=-100, top_px=0, width_px=1280, height_px=720),
        )
    )

    assert capability.available is False
    assert capability.backend_name == "desktop_duplication_dxgi"
    assert "not completed" in capability.reason
    assert capability.details["dxgi_library_loadable"] is True
    assert capability.details["d3d11_library_loadable"] is True
    assert capability.details["implementation_status"] == "capability_probe_only"
    assert capability.details["preferred_for_virtual_desktop"] is True


def test_desktop_duplication_backend_rejects_foreground_window_requests() -> None:
    backend = ScriptedDesktopDuplicationBackend(probe_details={})

    capability = backend.detect_capability(WindowsCaptureRequest(target=WindowsCaptureTarget.foreground_window))

    assert capability.available is False
    assert capability.reason == "Desktop Duplication only supports virtual_desktop requests."
    assert capability.details["target"] == WindowsCaptureTarget.foreground_window


def test_desktop_duplication_backend_capture_fails_safely_when_incomplete() -> None:
    backend = ScriptedDesktopDuplicationBackend(probe_details={})

    with pytest.raises(WindowsCaptureStageError) as exc_info:
        backend.capture(
            WindowsCaptureRequest(
                target=WindowsCaptureTarget.virtual_desktop,
                bounds=ScreenBBox(left_px=0, top_px=0, width_px=800, height_px=600),
            )
        )

    assert exc_info.value.stage == "desktop_duplication_incomplete"
    assert exc_info.value.diagnostics["backend_name"] == "desktop_duplication_dxgi"
    assert exc_info.value.diagnostics["implementation_complete"] is False


def test_desktop_duplication_backend_reports_runtime_unavailable_when_os_support_is_missing() -> None:
    backend = ScriptedDesktopDuplicationBackend(
        probe_details={
            "runtime_supported_os": False,
            "windows_major": 6,
            "windows_minor": 1,
            "windows_build": 7601,
        }
    )

    capability = backend.detect_capability(
        WindowsCaptureRequest(
            target=WindowsCaptureTarget.virtual_desktop,
            bounds=ScreenBBox(left_px=0, top_px=0, width_px=800, height_px=600),
        )
    )

    assert capability.available is False
    assert capability.reason == "Desktop Duplication requires Windows 8 or newer."
    assert capability.details["runtime_supported_os"] is False


def test_provider_does_not_silently_fall_back_to_gdi_in_production_full_desktop_mode() -> None:
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=_single_display_metrics())
        ),
        capture_backends=(
            ScriptedDesktopDuplicationBackend(probe_details={}),
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
    candidates = result.details["backend_candidates"]
    assert candidates[0]["backend_name"] == "desktop_duplication_dxgi"
    assert candidates[0]["available"] is False
    assert candidates[0]["details"]["implementation_status"] == "capability_probe_only"
    assert candidates[1]["backend_name"] == "gdi_bitblt"
    assert candidates[1]["runtime_eligible"] is False
    assert candidates[1]["diagnostic_only"] is True


def test_diagnostic_runtime_can_use_gdi_after_desktop_duplication_candidate() -> None:
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=_single_display_metrics())
        ),
        capture_backends=(
            ScriptedDesktopDuplicationBackend(probe_details={}),
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
    assert result.details["selected_backend_name"] == "gdi_bitblt"
    assert result.details["used_backend_name"] == "gdi_bitblt"


def test_default_provider_builds_dxcam_before_gdi() -> None:
    provider = WindowsObserveOnlyCaptureProvider(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(provider_name="FakeScreenMetricsProvider", metrics=_single_display_metrics())
        )
    )

    backend_names = tuple(backend.backend_name for backend in provider._capture_backends)

    assert backend_names[:2] == ("dxcam_desktop", "gdi_bitblt")
