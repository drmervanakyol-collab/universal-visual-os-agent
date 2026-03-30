from __future__ import annotations

from datetime import UTC, datetime

import cv2
import numpy

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
    SemanticTextBlock,
    SemanticTextRegion,
    SemanticTextStatus,
    TextExtractionResponse,
    TextExtractionResponseStatus,
)


class _StaticResponseBackend:
    def __init__(self, response_factory) -> None:
        self.backend_name = "static_test_backend"
        self._response_factory = response_factory

    def run(self, request):
        return self._response_factory(request)


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
            frame_id="frame-ocr-enrichment-1",
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


def _prepared_pipeline(payload: FrameImagePayload):
    capture_result = _capture_result(payload)
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(capture_result)
    state_result = PreparedSemanticStateBuilder().build(preparation)
    return preparation, state_result


def test_real_ocr_enrichment_updates_snapshot_layout_and_candidates() -> None:
    preparation, state_result = _prepared_pipeline(_payload_with_text())

    result = PreparedSemanticTextExtractionAdapter(
        text_backend=RapidOcrTextExtractionBackend()
    ).extract(preparation, state_result)

    assert result.success is True
    assert result.enriched_snapshot is not None
    snapshot = result.enriched_snapshot
    assert snapshot.layout_tree is not None
    full_region_node = snapshot.layout_tree.find_node("frame-ocr-enrichment-1:full")
    assert full_region_node is not None
    assert full_region_node.attributes["ocr_enriched"] is True
    assert full_region_node.attributes["ocr_text_status"] == "extracted"
    assert "HELLO" in (full_region_node.attributes["ocr_text"] or "").upper()
    ocr_region_node = snapshot.layout_tree.find_node("frame-ocr-enrichment-1:full:ocr:node")
    assert ocr_region_node is not None
    assert ocr_region_node.role == "ocr_text_region"
    assert len(ocr_region_node.children) >= 1
    assert snapshot.metadata["ocr_enrichment"] is True
    assert snapshot.metadata["ocr_candidate_ids"]
    assert len(snapshot.candidates) > 4
    assert all(candidate.enabled is False for candidate in snapshot.candidates)
    assert all(candidate.actionable is False for candidate in snapshot.candidates)
    assert any(candidate.role == "ocr_text_block" for candidate in snapshot.candidates)


def test_ocr_enrichment_handles_empty_output_safely() -> None:
    preparation, state_result = _prepared_pipeline(_payload_with_text())

    def _response_factory(request):
        return TextExtractionResponse(
            status=TextExtractionResponseStatus.completed,
            backend_name="static_test_backend",
            text_regions=tuple(
                SemanticTextRegion(
                    region_id=region.region_id,
                    label=region.label,
                    bounds=region.bounds,
                    node_id=region.node_id,
                    block_id=region.block_id,
                    role=region.role,
                    status=SemanticTextStatus.unavailable,
                    enabled=False,
                    extracted_text=None,
                    confidence=None,
                    metadata={"observe_only": True, "analysis_only": True},
                )
                for region in request.regions
            ),
            text_blocks=(),
        )

    result = PreparedSemanticTextExtractionAdapter(
        text_backend=_StaticResponseBackend(_response_factory)
    ).extract(preparation, state_result)

    assert result.success is True
    assert result.enriched_snapshot is not None
    snapshot = result.enriched_snapshot
    assert snapshot.metadata["ocr_candidate_ids"] == ()
    assert len(snapshot.candidates) == 4
    assert snapshot.layout_tree is not None
    full_region_node = snapshot.layout_tree.find_node("frame-ocr-enrichment-1:full")
    assert full_region_node is not None
    assert full_region_node.attributes["ocr_text_status"] == "unavailable"
    assert snapshot.layout_tree.find_node("frame-ocr-enrichment-1:full:ocr:node") is None


def test_ocr_enrichment_handles_partial_output_safely() -> None:
    preparation, state_result = _prepared_pipeline(_payload_with_text())

    def _response_factory(request):
        first_region = request.regions[0]
        other_regions = request.regions[1:]
        return TextExtractionResponse(
            status=TextExtractionResponseStatus.completed,
            backend_name="static_test_backend",
            text_regions=(
                SemanticTextRegion(
                    region_id=first_region.region_id,
                    label=first_region.label,
                    bounds=first_region.bounds,
                    node_id=first_region.node_id,
                    block_id=first_region.block_id,
                    role=first_region.role,
                    status=SemanticTextStatus.extracted,
                    enabled=False,
                    extracted_text="HELLO 123",
                    confidence=0.98,
                    metadata={"observe_only": True, "analysis_only": True},
                ),
                *tuple(
                    SemanticTextRegion(
                        region_id=region.region_id,
                        label=region.label,
                        bounds=region.bounds,
                        node_id=region.node_id,
                        block_id=region.block_id,
                        role=region.role,
                        status=SemanticTextStatus.unavailable,
                        enabled=False,
                        extracted_text=None,
                        confidence=None,
                        metadata={"observe_only": True, "analysis_only": True},
                    )
                    for region in other_regions
                ),
            ),
            text_blocks=(
                SemanticTextBlock(
                    text_block_id=f"{first_region.region_id}:line:1",
                    region_id=first_region.region_id,
                    label="Observed Desktop Surface Line 1",
                    bounds=first_region.bounds,
                    enabled=False,
                    extracted_text="HELLO 123",
                    confidence=0.98,
                    metadata={"observe_only": True, "analysis_only": True},
                ),
            ),
        )

    result = PreparedSemanticTextExtractionAdapter(
        text_backend=_StaticResponseBackend(_response_factory)
    ).extract(preparation, state_result)

    assert result.success is True
    assert result.enriched_snapshot is not None
    snapshot = result.enriched_snapshot
    assert snapshot.layout_tree is not None
    assert snapshot.layout_tree.find_node("frame-ocr-enrichment-1:full:ocr:node") is not None
    assert snapshot.layout_tree.find_node("frame-ocr-enrichment-1:top-band:ocr:node") is None
    assert snapshot.metadata["ocr_extracted_region_ids"] == ("frame-ocr-enrichment-1:full:ocr",)
    assert snapshot.metadata["ocr_unavailable_region_ids"] == (
        "frame-ocr-enrichment-1:top-band:ocr",
        "frame-ocr-enrichment-1:middle-band:ocr",
        "frame-ocr-enrichment-1:bottom-band:ocr",
    )
    assert any(candidate.role == "ocr_text_region" for candidate in snapshot.candidates)
    assert any(candidate.role == "ocr_text_block" for candidate in snapshot.candidates)
    assert all(candidate.actionable is False for candidate in snapshot.candidates)


def test_ocr_enrichment_handles_failed_backend_response_safely() -> None:
    preparation, state_result = _prepared_pipeline(_payload_with_text())

    result = PreparedSemanticTextExtractionAdapter(
        text_backend=_StaticResponseBackend(
            lambda request: TextExtractionResponse(
                status=TextExtractionResponseStatus.failed,
                backend_name="static_test_backend",
                error_code="ocr_runtime_failed",
                error_message="OCR runtime failed.",
            )
        )
    ).extract(preparation, state_result)

    assert result.success is False
    assert result.error_code == "ocr_runtime_failed"
    assert result.enriched_snapshot is None


def test_ocr_enrichment_does_not_propagate_malformed_region_mapping() -> None:
    preparation, state_result = _prepared_pipeline(_payload_with_text())

    result = PreparedSemanticTextExtractionAdapter(
        text_backend=_StaticResponseBackend(
            lambda request: TextExtractionResponse(
                status=TextExtractionResponseStatus.completed,
                backend_name="static_test_backend",
                text_regions=(
                    SemanticTextRegion(
                        region_id="unknown-region",
                        label="Broken",
                        bounds=request.regions[0].bounds,
                        node_id=request.regions[0].node_id,
                        block_id=request.regions[0].block_id,
                        status=SemanticTextStatus.extracted,
                        enabled=False,
                        extracted_text="BROKEN",
                        confidence=0.9,
                    ),
                ),
            )
        )
    ).extract(preparation, state_result)

    assert result.success is False
    assert result.error_code == "text_extraction_exception"
