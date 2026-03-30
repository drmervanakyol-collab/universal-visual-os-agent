from __future__ import annotations

from datetime import UTC, datetime

import cv2
import numpy

from universal_visual_os_agent.geometry import NormalizedBBox
from universal_visual_os_agent.integrations.windows import WindowsCaptureTarget
from universal_visual_os_agent.perception import (
    CaptureResult,
    CapturedFrame,
    FrameImagePayload,
)
from universal_visual_os_agent.semantics import (
    FullDesktopCaptureSemanticInputAdapter,
    PreparedSemanticStateBuilder,
    PreparedSemanticTextExtractionAdapter,
    RapidOcrTextExtractionBackend,
    SemanticTextStatus,
    TextExtractionRegionRequest,
    TextExtractionRequest,
    TextExtractionResponseStatus,
)


class _FakeRapidOcrOutput:
    def __init__(
        self,
        *,
        boxes: tuple[tuple[tuple[float, float], ...], ...],
        txts: tuple[str, ...],
        scores: tuple[float, ...],
    ) -> None:
        self.boxes = boxes
        self.txts = txts
        self.scores = scores


class _ExplodingBackend:
    backend_name = "exploding_backend"

    def run(self, request: TextExtractionRequest):
        raise RuntimeError("backend exploded")


def _payload_with_text(*, text: str = "HELLO 123") -> FrameImagePayload:
    width = 900
    height = 260
    image = numpy.full((height, width, 4), 255, dtype=numpy.uint8)
    cv2.putText(
        image,
        text,
        (40, 165),
        cv2.FONT_HERSHEY_SIMPLEX,
        3.0,
        (0, 0, 0, 255),
        5,
        cv2.LINE_AA,
    )
    return FrameImagePayload(
        width=width,
        height=height,
        row_stride_bytes=width * 4,
        image_bytes=image.tobytes(),
    )


def _capture_result(payload: FrameImagePayload) -> CaptureResult:
    return CaptureResult.ok(
        provider_name="WindowsObserveOnlyCaptureProvider",
        frame=CapturedFrame(
            frame_id="frame-rapidocr-1",
            width=payload.width,
            height=payload.height,
            captured_at=datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
            payload=payload,
            source="WindowsObserveOnlyCaptureProvider",
            metadata={
                "backend_name": "dxcam_desktop",
                "origin_x_px": 0,
                "origin_y_px": 0,
                "display_count": 1,
            },
        ),
        details={
            "capture_target": WindowsCaptureTarget.virtual_desktop,
            "selected_backend_name": "dxcam_desktop",
            "used_backend_name": "dxcam_desktop",
            "backend_fallback_used": False,
        },
    )


def _single_region_request(payload: FrameImagePayload) -> TextExtractionRequest:
    return TextExtractionRequest(
        frame_id="frame-rapidocr-direct",
        snapshot_id="snapshot-rapidocr-direct",
        captured_at=datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
        payload=payload,
        backend_name="dxcam_desktop",
        capture_target="virtual_desktop",
        regions=(
            TextExtractionRegionRequest(
                region_id="full-region:ocr",
                label="Observed Desktop Surface",
                bounds=NormalizedBBox(left=0.0, top=0.0, width=1.0, height=1.0),
                block_id="full-region",
                node_id="full-region",
            ),
        ),
        metadata={"observe_only": True},
    )


def _prepared_pipeline(payload: FrameImagePayload):
    capture_result = _capture_result(payload)
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(capture_result)
    state_result = PreparedSemanticStateBuilder().build(preparation)
    return preparation, state_result


def test_rapidocr_backend_extracts_text_from_synthetic_pipeline() -> None:
    preparation, state_result = _prepared_pipeline(_payload_with_text())

    result = PreparedSemanticTextExtractionAdapter(
        text_backend=RapidOcrTextExtractionBackend()
    ).extract(preparation, state_result)

    assert result.success is True
    assert result.response is not None
    assert result.response.status is TextExtractionResponseStatus.completed
    assert result.response.backend_name == "rapidocr_onnxruntime"
    assert any(region.status is SemanticTextStatus.extracted for region in result.text_regions)
    assert any(block.extracted_text for block in result.text_blocks)
    aggregate_text = " ".join(
        block.extracted_text or ""
        for block in result.text_blocks
    ).upper()
    assert "HELLO" in aggregate_text
    assert all(region.enabled is False for region in result.text_regions)
    assert all(block.enabled is False for block in result.text_blocks)


def test_rapidocr_backend_handles_unavailable_engine_safely() -> None:
    backend = RapidOcrTextExtractionBackend(
        engine_factory=lambda: (_ for _ in ()).throw(RuntimeError("onnxruntime unavailable"))
    )

    response = backend.run(_single_region_request(_payload_with_text()))

    assert response.status is TextExtractionResponseStatus.failed
    assert response.error_code == "ocr_backend_unavailable"
    assert response.error_message == "onnxruntime unavailable"


def test_rapidocr_backend_handles_empty_output_safely() -> None:
    backend = RapidOcrTextExtractionBackend(
        engine_factory=lambda: (
            lambda img_content, **kwargs: _FakeRapidOcrOutput(boxes=(), txts=(), scores=())
        )
    )
    preparation, state_result = _prepared_pipeline(_payload_with_text())

    result = PreparedSemanticTextExtractionAdapter(text_backend=backend).extract(
        preparation,
        state_result,
    )

    assert result.success is True
    assert result.response is not None
    assert result.response.status is TextExtractionResponseStatus.completed
    assert all(region.status is SemanticTextStatus.unavailable for region in result.text_regions)
    assert result.text_blocks == ()
    assert all(region.enabled is False for region in result.text_regions)


def test_rapidocr_backend_handles_malformed_output_safely() -> None:
    backend = RapidOcrTextExtractionBackend(
        engine_factory=lambda: (
            lambda img_content, **kwargs: _FakeRapidOcrOutput(
                boxes=((((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))),),
                txts=("HELLO", "EXTRA"),
                scores=(0.99,),
            )
        )
    )

    response = backend.run(_single_region_request(_payload_with_text()))

    assert response.status is TextExtractionResponseStatus.failed
    assert response.error_code == "ocr_backend_malformed_output"


def test_text_extraction_adapter_catches_backend_exception_safely() -> None:
    preparation, state_result = _prepared_pipeline(_payload_with_text())

    result = PreparedSemanticTextExtractionAdapter(text_backend=_ExplodingBackend()).extract(
        preparation,
        state_result,
    )

    assert result.success is False
    assert result.error_code == "text_extraction_backend_exception"
    assert result.error_message == "backend exploded"
