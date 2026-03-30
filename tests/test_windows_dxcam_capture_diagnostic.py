from __future__ import annotations

from datetime import UTC, datetime

from universal_visual_os_agent.geometry import (
    ScreenMetrics,
    ScreenMetricsQueryResult,
    VirtualDesktopMetrics,
)
from universal_visual_os_agent.integrations.windows import (
    RawWindowsCapture,
    WindowsCaptureBackendCapability,
    WindowsCaptureRequest,
    WindowsCaptureStageError,
    WindowsDxcamCaptureBackend,
    run_dxcam_capture_diagnostic,
)


class FakeScreenMetricsProvider:
    def __init__(self, result: ScreenMetricsQueryResult) -> None:
        self._result = result

    def get_virtual_desktop_metrics(self) -> ScreenMetricsQueryResult:
        return self._result


class FakeDxcamCamera:
    def __init__(self, *, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def release(self) -> None:
        return


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


class DeterministicDxcamBackend(WindowsDxcamCaptureBackend):
    def __init__(
        self,
        *,
        dxcam_module: FakeDxcamModule,
        environment_details: dict[str, object],
        capture_result: RawWindowsCapture | None = None,
        capture_exception: Exception | None = None,
    ) -> None:
        super().__init__(dxcam_module_loader=lambda: dxcam_module)
        self._environment_details = environment_details
        self._capture_result = capture_result
        self._capture_exception = capture_exception

    def _is_windows_platform(self) -> bool:
        return True

    def _capture_environment_details(self) -> dict[str, object]:
        return {
            "backend_name": self.backend_name,
            "platform": "win32",
            "session_name": "Console",
            "is_remote_session": False,
            "input_desktop_accessible": True,
            "environment_limitation_suspected": False,
            "environment_limitation_reasons": (),
            **self._environment_details,
        }

    def capture(self, request: WindowsCaptureRequest) -> RawWindowsCapture:
        if self._capture_exception is not None:
            raise self._capture_exception
        if self._capture_result is None:
            raise AssertionError("Test backend requires capture_result or capture_exception.")
        return self._capture_result


class RaisingBackend:
    backend_name = "dxcam_desktop"

    def detect_capability(self, request: WindowsCaptureRequest) -> WindowsCaptureBackendCapability:
        raise RuntimeError("diagnostic probe exploded")


def _single_display_metrics(*, width_px: int = 640, height_px: int = 480) -> VirtualDesktopMetrics:
    return VirtualDesktopMetrics(
        displays=(
            ScreenMetrics(width_px=width_px, height_px=height_px, origin_x_px=0, origin_y_px=0, is_primary=True),
        )
    )


def _success_capture(*, width: int = 640, height: int = 480) -> RawWindowsCapture:
    return RawWindowsCapture(
        width=width,
        height=height,
        origin_x_px=0,
        origin_y_px=0,
        row_stride_bytes=width * 4,
        image_bytes=b"\x00" * (width * height * 4),
        captured_at=datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
        metadata={
            "backend_name": "dxcam_desktop",
            "capture_source_strategy": "dxcam",
            "dxcam_backend_used": "dxgi",
        },
    )


def test_dxcam_capture_diagnostic_reports_real_capture_success_and_optional_bmp_output(
    workspace_tmp_path,
) -> None:
    backend = DeterministicDxcamBackend(
        dxcam_module=FakeDxcamModule(
            behaviors={
                "dxgi": lambda: FakeDxcamCamera(width=640, height=480),
                "winrt": RuntimeError("unused"),
            }
        ),
        environment_details={},
        capture_result=_success_capture(),
    )
    output_path = workspace_tmp_path / "dxcam-diagnostic.bmp"

    result = run_dxcam_capture_diagnostic(
        output_path=output_path,
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(
                provider_name="FakeScreenMetricsProvider",
                metrics=_single_display_metrics(),
            )
        ),
        capture_backend=backend,
    )

    assert result.metrics_lookup_succeeded is True
    assert result.backend_available is True
    assert result.capture_attempted is True
    assert result.capture_succeeded is True
    assert result.saved_image_path == str(output_path)
    assert output_path.exists()
    assert output_path.read_bytes()[:2] == b"BM"
    assert result.captured_frame_summary["width"] == 640
    assert result.captured_frame_summary["height"] == 480
    assert result.captured_frame_summary["metadata"]["dxcam_backend_used"] == "dxgi"
    display = result.to_display_dict()
    assert display["capture_succeeded"] is True
    assert display["captured_frame_summary"]["width"] == 640


def test_dxcam_capture_diagnostic_reports_access_denied_probe_details_clearly() -> None:
    backend = DeterministicDxcamBackend(
        dxcam_module=FakeDxcamModule(
            behaviors={
                "dxgi": Exception(-2147024891, "Access denied"),
                "winrt": ModuleNotFoundError("WinRT backend requires optional dependencies."),
            }
        ),
        environment_details={},
    )

    result = run_dxcam_capture_diagnostic(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(
                provider_name="FakeScreenMetricsProvider",
                metrics=_single_display_metrics(),
            )
        ),
        capture_backend=backend,
    )

    assert result.metrics_lookup_succeeded is True
    assert result.backend_available is False
    assert result.capture_attempted is False
    assert result.capture_succeeded is False
    assert result.availability_reason == "DXcam dxgi backend access was denied in this environment."
    assert result.failure_backend == "dxgi"
    assert result.failure_stage == "dxcam_create"
    assert result.failure_hresult == -2147024891
    assert result.process_context["process_appears_interactive"] is True
    assert result.output_selection["requested_device_idx"] == 0
    assert result.output_selection["requested_bounds"]["width_px"] == 640
    assert result.backend_details["dxcam_output_info"] == "Device[0] Output[0]: Res:(640, 480) Rot:0 Primary:True"
    display = result.to_display_dict()
    assert display["attempts"][0]["hresult"] == -2147024891


def test_dxcam_capture_diagnostic_handles_capture_failure_safely() -> None:
    backend = DeterministicDxcamBackend(
        dxcam_module=FakeDxcamModule(
            behaviors={
                "dxgi": lambda: FakeDxcamCamera(width=640, height=480),
                "winrt": RuntimeError("unused"),
            }
        ),
        environment_details={},
        capture_exception=WindowsCaptureStageError(
            stage="dxcam_grab",
            message="DXcam failed to grab a frame.",
            diagnostics={"backend_name": "dxcam_desktop", "dxcam_backend_used": "dxgi"},
        ),
    )

    result = run_dxcam_capture_diagnostic(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(
                provider_name="FakeScreenMetricsProvider",
                metrics=_single_display_metrics(),
            )
        ),
        capture_backend=backend,
    )

    assert result.backend_available is True
    assert result.capture_attempted is True
    assert result.capture_succeeded is False
    assert result.capture_error_code == "dxcam_grab_failed"
    assert result.capture_error_message == "DXcam failed to grab a frame."
    assert result.capture_details["failing_stage"] == "dxcam_grab"


def test_dxcam_capture_diagnostic_handles_missing_metrics_safely() -> None:
    result = run_dxcam_capture_diagnostic(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.failure(
                provider_name="FakeScreenMetricsProvider",
                error_code="windows_api_error",
                error_message="Monitor enumeration failed.",
            )
        ),
        capture_backend=RaisingBackend(),
    )

    assert result.metrics_lookup_succeeded is False
    assert result.backend_available is False
    assert result.capture_attempted is False
    assert result.error_code == "screen_metrics_unavailable"
    assert result.monitor_metadata["metrics_error_code"] == "windows_api_error"
    assert result.output_selection["requested_bounds"] is None


def test_dxcam_capture_diagnostic_handles_backend_exception_safely() -> None:
    result = run_dxcam_capture_diagnostic(
        screen_metrics_provider=FakeScreenMetricsProvider(
            ScreenMetricsQueryResult.ok(
                provider_name="FakeScreenMetricsProvider",
                metrics=_single_display_metrics(),
            )
        ),
        capture_backend=RaisingBackend(),
    )

    assert result.metrics_lookup_succeeded is True
    assert result.backend_available is False
    assert result.capture_attempted is False
    assert result.error_code == "diagnostic_probe_exception"
    assert result.error_message == "diagnostic probe exploded"
    assert result.monitor_metadata["display_count"] == 1
