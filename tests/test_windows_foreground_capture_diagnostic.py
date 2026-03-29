from __future__ import annotations

from datetime import UTC, datetime
from universal_visual_os_agent.geometry import ScreenBBox
from universal_visual_os_agent.integrations.windows import (
    ForegroundWindowMetadata,
    ForegroundWindowMetadataResult,
    run_foreground_window_capture_diagnostic,
)
from universal_visual_os_agent.perception import (
    CaptureResult,
    CapturedFrame,
    FrameImagePayload,
)


class FakeMetadataReader:
    def __init__(self, result: ForegroundWindowMetadataResult) -> None:
        self._result = result

    def read_foreground_window_metadata(self) -> ForegroundWindowMetadataResult:
        return self._result


class RaisingMetadataReader:
    def read_foreground_window_metadata(self) -> ForegroundWindowMetadataResult:
        raise RuntimeError("metadata probe failed")


class FakeCaptureProvider:
    def __init__(self, result: CaptureResult) -> None:
        self._result = result

    def capture_frame(self) -> CaptureResult:
        return self._result


class RaisingCaptureProvider:
    def capture_frame(self) -> CaptureResult:
        raise RuntimeError("capture provider crashed")


def test_foreground_capture_diagnostic_success_shape_and_optional_bmp_output(workspace_tmp_path) -> None:
    output_path = workspace_tmp_path / "foreground-diagnostic.bmp"
    result = run_foreground_window_capture_diagnostic(
        output_path=output_path,
        metadata_reader=FakeMetadataReader(
            ForegroundWindowMetadataResult(
                foreground_window_detected=True,
                foreground_window_handle=1234,
                metadata=ForegroundWindowMetadata(
                    handle=1234,
                    title="Diagnostic Window",
                    class_name="Notepad",
                    bounds=ScreenBBox(left_px=10, top_px=20, width_px=200, height_px=100),
                    is_visible=True,
                    is_minimized=False,
                ),
                details={"bounds_lookup_succeeded": True},
            )
        ),
        capture_provider=FakeCaptureProvider(
            CaptureResult.ok(
                provider_name="FakeCaptureProvider",
                frame=CapturedFrame(
                    frame_id="frame-1",
                    width=2,
                    height=1,
                    captured_at=datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
                    source="FakeCaptureProvider",
                    metadata={"backend_name": "printwindow_foreground"},
                    payload=FrameImagePayload(
                        width=2,
                        height=1,
                        row_stride_bytes=8,
                        image_bytes=b"\x00\x00\xff\xff\x00\xff\x00\xff",
                    ),
                ),
                details={"selected_backend_name": "printwindow_foreground"},
            )
        ),
    )

    assert result.capture_succeeded is True
    assert result.foreground_window_detected is True
    assert result.foreground_window_metadata is not None
    assert result.saved_image_path == str(output_path)
    assert output_path.exists()
    assert output_path.read_bytes()[:2] == b"BM"
    display = result.to_display_dict()
    assert display["foreground_window_metadata"]["title"] == "Diagnostic Window"
    assert display["captured_frame_summary"]["width"] == 2


def test_foreground_capture_diagnostic_reports_no_foreground_window_clearly() -> None:
    result = run_foreground_window_capture_diagnostic(
        metadata_reader=FakeMetadataReader(
            ForegroundWindowMetadataResult(
                foreground_window_detected=False,
                details={"reason": "No foreground window detected."},
            )
        ),
        capture_provider=FakeCaptureProvider(
            CaptureResult.failure(
                provider_name="FakeCaptureProvider",
                error_code="capture_backend_unavailable",
                error_message="No safe capture backend is available for the current request.",
                details={"failing_stage": "backend_selection"},
            )
        ),
    )

    assert result.capture_succeeded is False
    assert result.foreground_window_detected is False
    assert result.foreground_window_handle is None
    assert result.capture_error_code == "capture_backend_unavailable"
    assert result.saved_image_path is None
    assert result.to_display_dict()["metadata_details"]["reason"] == "No foreground window detected."


def test_foreground_capture_diagnostic_handles_provider_exception_safely() -> None:
    result = run_foreground_window_capture_diagnostic(
        metadata_reader=FakeMetadataReader(
            ForegroundWindowMetadataResult(
                foreground_window_detected=True,
                foreground_window_handle=4321,
                metadata=ForegroundWindowMetadata(handle=4321),
            )
        ),
        capture_provider=RaisingCaptureProvider(),
    )

    assert result.capture_succeeded is False
    assert result.capture_error_code == "diagnostic_capture_exception"
    assert result.capture_details["exception_type"] == "RuntimeError"
    assert result.foreground_window_detected is True


def test_foreground_capture_diagnostic_handles_metadata_exception_safely() -> None:
    result = run_foreground_window_capture_diagnostic(
        metadata_reader=RaisingMetadataReader(),
        capture_provider=FakeCaptureProvider(
            CaptureResult.failure(
                provider_name="FakeCaptureProvider",
                error_code="capture_backend_unavailable",
                error_message="No safe capture backend is available for the current request.",
            )
        ),
    )

    assert result.foreground_window_detected is False
    assert result.metadata_error_code == "metadata_probe_exception"
    assert result.metadata_details["exception_type"] == "RuntimeError"
