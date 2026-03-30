from __future__ import annotations

from datetime import UTC, datetime

from universal_visual_os_agent.integrations.windows import WindowsCaptureTarget
from universal_visual_os_agent.perception import (
    CaptureResult,
    CapturedFrame,
    FrameImagePayload,
)
from universal_visual_os_agent.semantics import (
    FullDesktopCaptureSemanticInputAdapter,
)


def _payload(*, width: int = 4, height: int = 2) -> FrameImagePayload:
    return FrameImagePayload(
        width=width,
        height=height,
        row_stride_bytes=width * 4,
        image_bytes=b"\x00" * (width * height * 4),
    )


def _frame(
    *,
    payload: FrameImagePayload | None = None,
    metadata: dict[str, object] | None = None,
) -> CapturedFrame:
    return CapturedFrame(
        frame_id="frame-dxcam-1",
        width=4,
        height=2,
        captured_at=datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
        payload=_payload() if payload is None else payload,
        source="WindowsObserveOnlyCaptureProvider",
        metadata={
            "backend_name": "dxcam_desktop",
            "origin_x_px": 0,
            "origin_y_px": 0,
            "display_count": 1,
            "dxcam_backend_used": "dxgi",
            **({} if metadata is None else metadata),
        },
    )


def test_full_desktop_capture_result_prepares_semantic_extraction_input() -> None:
    adapter = FullDesktopCaptureSemanticInputAdapter()
    capture_result = CaptureResult.ok(
        provider_name="WindowsObserveOnlyCaptureProvider",
        frame=_frame(),
        details={
            "capture_target": WindowsCaptureTarget.virtual_desktop,
            "selected_backend_name": "dxcam_desktop",
            "used_backend_name": "dxcam_desktop",
            "backend_fallback_used": False,
        },
    )

    result = adapter.prepare(capture_result)

    assert result.success is True
    assert result.extraction_input is not None
    assert result.extraction_input.capture_target == "virtual_desktop"
    assert result.extraction_input.backend_name == "dxcam_desktop"
    assert result.extraction_input.payload.width == 4
    assert result.extraction_input.snapshot_preparation.observed_at == capture_result.frame.captured_at
    assert result.extraction_input.snapshot_preparation.metadata["source_frame_id"] == "frame-dxcam-1"
    assert result.extraction_input.snapshot_preparation.metadata["capture_backend_name"] == "dxcam_desktop"
    assert result.extraction_input.snapshot_preparation.metadata["used_backend_name"] == "dxcam_desktop"


def test_adapter_handles_failed_capture_result_safely() -> None:
    adapter = FullDesktopCaptureSemanticInputAdapter()
    capture_result = CaptureResult.failure(
        provider_name="WindowsObserveOnlyCaptureProvider",
        error_code="dxcam_backend_unavailable",
        error_message="DXcam could not initialize.",
    )

    result = adapter.prepare(capture_result)

    assert result.success is False
    assert result.error_code == "capture_failed"
    assert result.error_message == "DXcam could not initialize."
    assert result.details["capture_error_code"] == "dxcam_backend_unavailable"


def test_adapter_handles_missing_payload_safely() -> None:
    adapter = FullDesktopCaptureSemanticInputAdapter()
    frame = CapturedFrame(
        frame_id="frame-no-payload",
        width=4,
        height=2,
        captured_at=datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
        payload=None,
        source="WindowsObserveOnlyCaptureProvider",
        metadata={
            "backend_name": "dxcam_desktop",
            "origin_x_px": 0,
            "origin_y_px": 0,
            "display_count": 1,
        },
    )
    capture_result = CaptureResult.ok(
        provider_name="WindowsObserveOnlyCaptureProvider",
        frame=frame,
        details={"capture_target": "virtual_desktop"},
    )

    result = adapter.prepare(capture_result)

    assert result.success is False
    assert result.error_code == "frame_payload_unavailable"
    assert result.details["frame_id"] == "frame-no-payload"


def test_adapter_handles_missing_required_metadata_safely() -> None:
    adapter = FullDesktopCaptureSemanticInputAdapter()
    capture_result = CaptureResult.ok(
        provider_name="WindowsObserveOnlyCaptureProvider",
        frame=_frame(metadata={"backend_name": "", "display_count": 0}),
        details={"capture_target": "virtual_desktop"},
    )

    result = adapter.prepare(capture_result)

    assert result.success is False
    assert result.error_code == "capture_metadata_unavailable"
    assert result.details["missing_metadata_fields"] == ("backend_name", "display_count")


def test_adapter_rejects_non_virtual_desktop_capture_targets_safely() -> None:
    adapter = FullDesktopCaptureSemanticInputAdapter()
    capture_result = CaptureResult.ok(
        provider_name="WindowsObserveOnlyCaptureProvider",
        frame=_frame(),
        details={"capture_target": "foreground_window"},
    )

    result = adapter.prepare(capture_result)

    assert result.success is False
    assert result.error_code == "unsupported_capture_target"
    assert result.details["capture_target"] == "foreground_window"
