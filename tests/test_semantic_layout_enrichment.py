from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from universal_visual_os_agent.geometry import NormalizedBBox
from universal_visual_os_agent.integrations.windows import WindowsCaptureTarget
from universal_visual_os_agent.perception import (
    CaptureResult,
    CapturedFrame,
    FrameImagePayload,
)
from universal_visual_os_agent.semantics import (
    FullDesktopCaptureSemanticInputAdapter,
    GeometricLayoutRegionAnalyzer,
    OcrAwareSemanticLayoutEnricher,
    PreparedSemanticStateBuilder,
    PreparedSemanticTextExtractionAdapter,
    SemanticLayoutRole,
    SemanticStateSnapshot,
    SemanticTextBlock,
    SemanticTextRegion,
    SemanticTextStatus,
    TextExtractionResponse,
    TextExtractionResponseStatus,
)


class _StaticResponseBackend:
    def __init__(self, response_factory) -> None:
        self.backend_name = "static_semantic_layout_backend"
        self._response_factory = response_factory

    def run(self, request):
        return self._response_factory(request)


class _ExplodingSemanticLayoutEnricher(OcrAwareSemanticLayoutEnricher):
    def _build_enriched_regions(self, layout_regions, signal_bundles):
        raise RuntimeError("semantic layout enricher exploded")


def _payload(*, width: int = 1200, height: int = 600) -> FrameImagePayload:
    return FrameImagePayload(
        width=width,
        height=height,
        row_stride_bytes=width * 4,
        image_bytes=b"\x00" * (width * height * 4),
    )


def _capture_result(payload: FrameImagePayload) -> CaptureResult:
    return CaptureResult.ok(
        provider_name="WindowsObserveOnlyCaptureProvider",
        frame=CapturedFrame(
            frame_id="frame-layout-enrichment-1",
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


def _prepared_state(text_backend) -> SemanticStateSnapshot:
    capture_result = _capture_result(_payload())
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(capture_result)
    state_result = PreparedSemanticStateBuilder().build(preparation)
    text_result = PreparedSemanticTextExtractionAdapter(text_backend=text_backend).extract(
        preparation,
        state_result,
    )
    assert text_result.success is True
    assert text_result.enriched_snapshot is not None
    analysis_result = GeometricLayoutRegionAnalyzer().analyze(text_result.enriched_snapshot)
    assert analysis_result.success is True
    assert analysis_result.snapshot is not None
    return analysis_result.snapshot


def _rich_semantic_response(request) -> TextExtractionResponse:
    regions_by_label = {region.label: region for region in request.regions}
    full_region = regions_by_label["Observed Desktop Surface"]
    top_region = regions_by_label["Top Analysis Band"]
    middle_region = regions_by_label["Middle Analysis Band"]
    bottom_region = regions_by_label["Bottom Analysis Band"]
    return TextExtractionResponse(
        status=TextExtractionResponseStatus.completed,
        backend_name="static_semantic_layout_backend",
        text_regions=(
            SemanticTextRegion(
                region_id=full_region.region_id,
                label=full_region.label,
                bounds=full_region.bounds,
                node_id=full_region.node_id,
                block_id=full_region.block_id,
                role=full_region.role,
                status=SemanticTextStatus.extracted,
                enabled=False,
                extracted_text="Workspace",
                confidence=0.9,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextRegion(
                region_id=top_region.region_id,
                label=top_region.label,
                bounds=top_region.bounds,
                node_id=top_region.node_id,
                block_id=top_region.block_id,
                role=top_region.role,
                status=SemanticTextStatus.extracted,
                enabled=False,
                extracted_text="File Edit View Search",
                confidence=0.96,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextRegion(
                region_id=middle_region.region_id,
                label=middle_region.label,
                bounds=middle_region.bounds,
                node_id=middle_region.node_id,
                block_id=middle_region.block_id,
                role=middle_region.role,
                status=SemanticTextStatus.unavailable,
                enabled=False,
                extracted_text=None,
                confidence=None,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextRegion(
                region_id=bottom_region.region_id,
                label=bottom_region.label,
                bounds=bottom_region.bounds,
                node_id=bottom_region.node_id,
                block_id=bottom_region.block_id,
                role=bottom_region.role,
                status=SemanticTextStatus.extracted,
                enabled=False,
                extracted_text="Ready Connected",
                confidence=0.92,
                metadata={"observe_only": True, "analysis_only": True},
            ),
        ),
        text_blocks=(
            SemanticTextBlock(
                text_block_id=f"{top_region.region_id}:line:1",
                region_id=top_region.region_id,
                label="Top Navigation",
                bounds=NormalizedBBox(left=0.02, top=0.03, width=0.48, height=0.1),
                enabled=False,
                extracted_text="File Edit View Search",
                confidence=0.96,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{middle_region.region_id}:line:1",
                region_id=middle_region.region_id,
                label="Left Navigation",
                bounds=NormalizedBBox(left=0.03, top=0.28, width=0.14, height=0.2),
                enabled=False,
                extracted_text="Home Menu Settings",
                confidence=0.91,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{middle_region.region_id}:line:2",
                region_id=middle_region.region_id,
                label="Centered Dialog",
                bounds=NormalizedBBox(left=0.37, top=0.34, width=0.26, height=0.2),
                enabled=False,
                extracted_text="Confirm Save",
                confidence=0.88,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{bottom_region.region_id}:line:1",
                region_id=bottom_region.region_id,
                label="Status Footer",
                bounds=NormalizedBBox(left=0.24, top=0.84, width=0.5, height=0.08),
                enabled=False,
                extracted_text="Ready Connected",
                confidence=0.92,
                metadata={"observe_only": True, "analysis_only": True},
            ),
        ),
    )


def _empty_semantic_response(request) -> TextExtractionResponse:
    return TextExtractionResponse(
        status=TextExtractionResponseStatus.completed,
        backend_name="static_semantic_layout_backend",
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


def _turkish_semantic_response(request) -> TextExtractionResponse:
    regions_by_label = {region.label: region for region in request.regions}
    full_region = regions_by_label["Observed Desktop Surface"]
    top_region = regions_by_label["Top Analysis Band"]
    middle_region = regions_by_label["Middle Analysis Band"]
    bottom_region = regions_by_label["Bottom Analysis Band"]
    return TextExtractionResponse(
        status=TextExtractionResponseStatus.completed,
        backend_name="static_semantic_layout_backend",
        text_regions=(
            SemanticTextRegion(
                region_id=full_region.region_id,
                label=full_region.label,
                bounds=full_region.bounds,
                node_id=full_region.node_id,
                block_id=full_region.block_id,
                role=full_region.role,
                status=SemanticTextStatus.extracted,
                enabled=False,
                extracted_text="Çalışma alanı",
                confidence=0.9,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextRegion(
                region_id=top_region.region_id,
                label=top_region.label,
                bounds=top_region.bounds,
                node_id=top_region.node_id,
                block_id=top_region.block_id,
                role=top_region.role,
                status=SemanticTextStatus.extracted,
                enabled=False,
                extracted_text="Dosya Görünüm Ayarlar",
                confidence=0.96,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextRegion(
                region_id=middle_region.region_id,
                label=middle_region.label,
                bounds=middle_region.bounds,
                node_id=middle_region.node_id,
                block_id=middle_region.block_id,
                role=middle_region.role,
                status=SemanticTextStatus.unavailable,
                enabled=False,
                extracted_text=None,
                confidence=None,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextRegion(
                region_id=bottom_region.region_id,
                label=bottom_region.label,
                bounds=bottom_region.bounds,
                node_id=bottom_region.node_id,
                block_id=bottom_region.block_id,
                role=bottom_region.role,
                status=SemanticTextStatus.extracted,
                enabled=False,
                extracted_text="Hazir Baglandi",
                confidence=0.92,
                metadata={"observe_only": True, "analysis_only": True},
            ),
        ),
        text_blocks=(
            SemanticTextBlock(
                text_block_id=f"{top_region.region_id}:line:1",
                region_id=top_region.region_id,
                label="Top Navigation Turkish",
                bounds=NormalizedBBox(left=0.02, top=0.03, width=0.48, height=0.1),
                enabled=False,
                extracted_text="Dosya Görünüm Ayarlar",
                confidence=0.96,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{bottom_region.region_id}:line:1",
                region_id=bottom_region.region_id,
                label="Status Footer Turkish",
                bounds=NormalizedBBox(left=0.24, top=0.84, width=0.5, height=0.08),
                enabled=False,
                extracted_text="Hazir Baglandi",
                confidence=0.92,
                metadata={"observe_only": True, "analysis_only": True},
            ),
        ),
    )


def test_semantic_layout_enrichment_refines_region_roles_and_metadata() -> None:
    snapshot = _prepared_state(text_backend=_StaticResponseBackend(_rich_semantic_response))

    result = OcrAwareSemanticLayoutEnricher().enrich(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    enriched_snapshot = result.snapshot
    roles_by_kind = {region.kind.value: region.semantic_role for region in enriched_snapshot.layout_regions}
    assert roles_by_kind["full_surface"] is SemanticLayoutRole.application_surface
    assert roles_by_kind["header"] is SemanticLayoutRole.navigation_header
    assert roles_by_kind["content"] is SemanticLayoutRole.primary_content
    assert roles_by_kind["footer"] is SemanticLayoutRole.status_footer
    assert roles_by_kind["left_sidebar"] is SemanticLayoutRole.navigation_sidebar
    assert roles_by_kind["right_sidebar"] is SemanticLayoutRole.sidebar_panel
    assert roles_by_kind["modal_like"] is SemanticLayoutRole.dialog_overlay
    assert enriched_snapshot.metadata["semantic_layout_enrichment"] is True
    assert enriched_snapshot.metadata["semantic_layout_signal_status"] == "available"
    assert all(region.enabled is False for region in enriched_snapshot.layout_regions)
    assert all(candidate.enabled is False for candidate in enriched_snapshot.candidates)
    assert all(candidate.actionable is False for candidate in enriched_snapshot.candidates)
    assert enriched_snapshot.layout_tree is not None
    header_node = enriched_snapshot.layout_tree.find_node("frame-layout-enrichment-1:layout:header")
    assert header_node is not None
    assert header_node.role == "semantic_layout_region:navigation_header"
    assert header_node.attributes["semantic_layout_role"] == "navigation_header"
    assert "file" in header_node.attributes["semantic_layout_navigation_keyword_hits"]


def test_semantic_layout_enrichment_handles_turkish_navigation_and_status_text() -> None:
    snapshot = _prepared_state(text_backend=_StaticResponseBackend(_turkish_semantic_response))

    result = OcrAwareSemanticLayoutEnricher().enrich(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    enriched_snapshot = result.snapshot
    roles_by_kind = {region.kind.value: region.semantic_role for region in enriched_snapshot.layout_regions}
    assert roles_by_kind["header"] is SemanticLayoutRole.navigation_header
    assert roles_by_kind["footer"] is SemanticLayoutRole.status_footer
    header_region = next(region for region in enriched_snapshot.layout_regions if region.kind.value == "header")
    footer_region = next(region for region in enriched_snapshot.layout_regions if region.kind.value == "footer")
    assert "dosya" in header_region.metadata["semantic_layout_navigation_keyword_hits"]
    assert "görünüm" in header_region.metadata["semantic_layout_navigation_keyword_hits"]
    assert "ayarlar" in header_region.metadata["semantic_layout_navigation_keyword_hits"]
    assert "hazır" in footer_region.metadata["semantic_layout_status_keyword_hits"]
    assert "bağlandı" in footer_region.metadata["semantic_layout_status_keyword_hits"]


def test_semantic_layout_enrichment_preserves_parent_child_layout_relations() -> None:
    snapshot = _prepared_state(text_backend=_StaticResponseBackend(_rich_semantic_response))

    result = OcrAwareSemanticLayoutEnricher().enrich(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    enriched_snapshot = result.snapshot
    assert enriched_snapshot.layout_tree is not None
    capture_surface = enriched_snapshot.layout_tree.find_node("frame-layout-enrichment-1:capture-surface")
    assert capture_surface is not None
    group_node = next(
        (child for child in capture_surface.children if child.role == "layout_region_group"),
        None,
    )
    assert group_node is not None
    full_surface_node = enriched_snapshot.layout_tree.find_node(
        "frame-layout-enrichment-1:layout:full-surface"
    )
    content_node = enriched_snapshot.layout_tree.find_node("frame-layout-enrichment-1:layout:content")
    assert full_surface_node is not None
    assert content_node is not None
    assert any(child.node_id == "frame-layout-enrichment-1:layout:header" for child in full_surface_node.children)
    assert any(child.node_id == "frame-layout-enrichment-1:layout:content" for child in full_surface_node.children)
    assert any(child.node_id == "frame-layout-enrichment-1:layout:footer" for child in full_surface_node.children)
    assert any(child.node_id == "frame-layout-enrichment-1:layout:left-sidebar" for child in content_node.children)
    assert any(child.node_id == "frame-layout-enrichment-1:layout:modal-like" for child in content_node.children)


def test_semantic_layout_enrichment_handles_missing_region_node_metadata_safely() -> None:
    snapshot = _prepared_state(text_backend=_StaticResponseBackend(_rich_semantic_response))
    broken_regions = (
        replace(snapshot.layout_regions[0], node_id=None),
        *snapshot.layout_regions[1:],
    )
    broken_snapshot = replace(snapshot, layout_regions=broken_regions)

    result = OcrAwareSemanticLayoutEnricher().enrich(broken_snapshot)

    assert result.success is False
    assert result.error_code == "layout_region_nodes_unavailable"
    assert snapshot.layout_regions[0].region_id in result.details["missing_layout_region_ids"]


def test_semantic_layout_enrichment_handles_missing_ocr_signals_safely() -> None:
    snapshot = _prepared_state(text_backend=_StaticResponseBackend(_empty_semantic_response))

    result = OcrAwareSemanticLayoutEnricher().enrich(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    enriched_snapshot = result.snapshot
    roles_by_kind = {region.kind.value: region.semantic_role for region in enriched_snapshot.layout_regions}
    assert roles_by_kind["full_surface"] is SemanticLayoutRole.application_surface
    assert roles_by_kind["header"] is SemanticLayoutRole.header_bar
    assert roles_by_kind["content"] is SemanticLayoutRole.primary_content
    assert roles_by_kind["footer"] is SemanticLayoutRole.footer_bar
    assert roles_by_kind["left_sidebar"] is SemanticLayoutRole.sidebar_panel
    assert roles_by_kind["right_sidebar"] is SemanticLayoutRole.sidebar_panel
    assert "modal_like" not in roles_by_kind
    assert enriched_snapshot.metadata["semantic_layout_signal_status"] == "absent"
    assert all(candidate.actionable is False for candidate in enriched_snapshot.candidates)


def test_semantic_layout_enrichment_does_not_propagate_unhandled_exceptions() -> None:
    snapshot = _prepared_state(text_backend=_StaticResponseBackend(_rich_semantic_response))

    result = _ExplodingSemanticLayoutEnricher().enrich(snapshot)

    assert result.success is False
    assert result.error_code == "semantic_layout_enrichment_exception"
    assert result.error_message == "semantic layout enricher exploded"
