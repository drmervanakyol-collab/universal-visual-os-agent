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
    GeometricLayoutRegionAnalyzer,
    PreparedSemanticStateBuilder,
    PreparedSemanticTextExtractionAdapter,
    RapidOcrTextExtractionBackend,
    SemanticLayoutRegionKind,
    SemanticStateSnapshot,
    SemanticTextBlock,
    SemanticTextRegion,
    SemanticTextStatus,
    TextExtractionResponse,
    TextExtractionResponseStatus,
)


class _StaticResponseBackend:
    def __init__(self, response_factory) -> None:
        self.backend_name = "static_layout_backend"
        self._response_factory = response_factory

    def run(self, request):
        return self._response_factory(request)


class _ExplodingAnalyzer(GeometricLayoutRegionAnalyzer):
    def _build_layout_regions(self, snapshot, region_blocks_by_key):
        raise RuntimeError("layout analyzer exploded")


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
            frame_id="frame-layout-region-1",
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


def _ocr_enriched_snapshot(*, text_backend) -> SemanticStateSnapshot:
    capture_result = _capture_result(_payload_with_text())
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(capture_result)
    state_result = PreparedSemanticStateBuilder().build(preparation)
    text_result = PreparedSemanticTextExtractionAdapter(text_backend=text_backend).extract(
        preparation,
        state_result,
    )
    assert text_result.success is True
    assert text_result.enriched_snapshot is not None
    return text_result.enriched_snapshot


def _bbox_within(inner, outer) -> bool:
    return (
        inner.left >= outer.left
        and inner.top >= outer.top
        and inner.left + inner.width <= outer.left + outer.width
        and inner.top + inner.height <= outer.top + outer.height
    )


def test_ocr_enriched_snapshot_analyzes_into_layout_regions() -> None:
    snapshot = _ocr_enriched_snapshot(text_backend=RapidOcrTextExtractionBackend())

    result = GeometricLayoutRegionAnalyzer().analyze(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    analyzed_snapshot = result.snapshot
    kinds = {region.kind for region in analyzed_snapshot.layout_regions}
    assert SemanticLayoutRegionKind.full_surface in kinds
    assert SemanticLayoutRegionKind.header in kinds
    assert SemanticLayoutRegionKind.content in kinds
    assert SemanticLayoutRegionKind.footer in kinds
    assert SemanticLayoutRegionKind.left_sidebar in kinds
    assert SemanticLayoutRegionKind.right_sidebar in kinds
    assert SemanticLayoutRegionKind.modal_like in kinds
    assert analyzed_snapshot.metadata["layout_region_analysis"] is True
    assert analyzed_snapshot.metadata["layout_region_ids"]
    assert analyzed_snapshot.metadata["layout_region_candidate_ids"]
    assert all(region.enabled is False for region in analyzed_snapshot.layout_regions)
    assert all(candidate.actionable is False for candidate in analyzed_snapshot.candidates)


def test_layout_region_analysis_preserves_layout_tree_relations() -> None:
    snapshot = _ocr_enriched_snapshot(text_backend=RapidOcrTextExtractionBackend())

    result = GeometricLayoutRegionAnalyzer().analyze(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    analyzed_snapshot = result.snapshot
    assert analyzed_snapshot.layout_tree is not None
    capture_surface = analyzed_snapshot.layout_tree.find_node("frame-layout-region-1:capture-surface")
    assert capture_surface is not None
    group_node = next(
        (child for child in capture_surface.children if child.role == "layout_region_group"),
        None,
    )
    assert group_node is not None
    full_surface_node = analyzed_snapshot.layout_tree.find_node("frame-layout-region-1:layout:full-surface")
    assert full_surface_node is not None
    content_node = analyzed_snapshot.layout_tree.find_node("frame-layout-region-1:layout:content")
    assert content_node is not None
    assert any(child.node_id == "frame-layout-region-1:layout:header" for child in full_surface_node.children)
    assert any(child.node_id == "frame-layout-region-1:layout:content" for child in full_surface_node.children)
    assert any(child.node_id == "frame-layout-region-1:layout:footer" for child in full_surface_node.children)
    assert any(child.node_id == "frame-layout-region-1:layout:left-sidebar" for child in content_node.children)


def test_layout_region_analysis_handles_incomplete_metadata_safely() -> None:
    snapshot = _ocr_enriched_snapshot(text_backend=RapidOcrTextExtractionBackend())
    snapshot = SemanticStateSnapshot(
        layout_tree=snapshot.layout_tree,
        region_blocks=snapshot.region_blocks,
        text_regions=snapshot.text_regions,
        text_blocks=snapshot.text_blocks,
        candidates=snapshot.candidates,
        metadata={k: v for k, v in snapshot.metadata.items() if k != "capture_surface_node_id"},
    )

    result = GeometricLayoutRegionAnalyzer().analyze(snapshot)

    assert result.success is False
    assert result.error_code == "capture_surface_metadata_unavailable"


def test_layout_region_analysis_handles_empty_ocr_output_safely() -> None:
    def _response_factory(request):
        return TextExtractionResponse(
            status=TextExtractionResponseStatus.completed,
            backend_name="static_layout_backend",
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

    snapshot = _ocr_enriched_snapshot(text_backend=_StaticResponseBackend(_response_factory))

    result = GeometricLayoutRegionAnalyzer().analyze(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    analyzed_snapshot = result.snapshot
    assert all(region.kind is not SemanticLayoutRegionKind.modal_like for region in analyzed_snapshot.layout_regions)
    content_region = next(
        region
        for region in analyzed_snapshot.layout_regions
        if region.kind is SemanticLayoutRegionKind.content
    )
    for region in analyzed_snapshot.layout_regions:
        if region.kind in {SemanticLayoutRegionKind.left_sidebar, SemanticLayoutRegionKind.right_sidebar}:
            assert _bbox_within(region.bounds, content_region.bounds)


def test_layout_region_analysis_handles_partial_ocr_output_safely() -> None:
    def _response_factory(request):
        extracted_region = request.regions[2]
        other_regions = tuple(
            region for region in request.regions if region.region_id != extracted_region.region_id
        )
        return TextExtractionResponse(
            status=TextExtractionResponseStatus.completed,
            backend_name="static_layout_backend",
            text_regions=(
                SemanticTextRegion(
                    region_id=extracted_region.region_id,
                    label=extracted_region.label,
                    bounds=extracted_region.bounds,
                    node_id=extracted_region.node_id,
                    block_id=extracted_region.block_id,
                    role=extracted_region.role,
                    status=SemanticTextStatus.extracted,
                    enabled=False,
                    extracted_text="CENTER PANEL",
                    confidence=0.92,
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
                    text_block_id=f"{extracted_region.region_id}:line:1",
                    region_id=extracted_region.region_id,
                    label="Middle Analysis Band Line 1",
                    bounds=extracted_region.bounds,
                    enabled=False,
                    extracted_text="CENTER PANEL",
                    confidence=0.92,
                    metadata={"observe_only": True, "analysis_only": True},
                ),
            ),
        )

    snapshot = _ocr_enriched_snapshot(text_backend=_StaticResponseBackend(_response_factory))

    result = GeometricLayoutRegionAnalyzer().analyze(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    analyzed_snapshot = result.snapshot
    assert any(region.kind is SemanticLayoutRegionKind.modal_like for region in analyzed_snapshot.layout_regions)
    assert all(candidate.enabled is False for candidate in analyzed_snapshot.candidates)
    assert all(candidate.actionable is False for candidate in analyzed_snapshot.candidates)


def test_layout_region_analysis_does_not_propagate_unhandled_exceptions() -> None:
    snapshot = _ocr_enriched_snapshot(text_backend=RapidOcrTextExtractionBackend())

    result = _ExplodingAnalyzer().analyze(snapshot)

    assert result.success is False
    assert result.error_code == "layout_region_analysis_exception"
    assert result.error_message == "layout analyzer exploded"
