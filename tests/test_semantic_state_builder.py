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
    PreparedSemanticStateBuilder,
    SemanticExtractionInput,
    SemanticExtractionPreparationResult,
    SemanticRegionBlock,
    SemanticSnapshotPreparation,
)


class RaisingSemanticStateBuilder(PreparedSemanticStateBuilder):
    def _build_snapshot_from_input(self, extraction_input: SemanticExtractionInput):
        raise RuntimeError("builder exploded")


def _payload(*, width: int = 4, height: int = 2) -> FrameImagePayload:
    return FrameImagePayload(
        width=width,
        height=height,
        row_stride_bytes=width * 4,
        image_bytes=b"\x00" * (width * height * 4),
    )


def _capture_result() -> CaptureResult:
    return CaptureResult.ok(
        provider_name="WindowsObserveOnlyCaptureProvider",
        frame=CapturedFrame(
            frame_id="frame-dxcam-2",
            width=4,
            height=2,
            captured_at=datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
            payload=_payload(),
            source="WindowsObserveOnlyCaptureProvider",
            metadata={
                "backend_name": "dxcam_desktop",
                "origin_x_px": 0,
                "origin_y_px": 0,
                "display_count": 1,
                "dxcam_backend_used": "dxgi",
            },
        ),
        details={
            "capture_target": WindowsCaptureTarget.virtual_desktop,
            "selected_backend_name": "dxcam_desktop",
            "used_backend_name": "dxcam_desktop",
            "backend_fallback_used": False,
        },
    )


def test_prepared_capture_input_builds_semantic_state_snapshot() -> None:
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(_capture_result())

    result = PreparedSemanticStateBuilder().build(preparation)

    assert result.success is True
    assert result.snapshot is not None
    assert result.snapshot.layout_tree is not None
    assert tuple(node.node_id for node in result.snapshot.layout_tree.walk()) == (
        "frame-dxcam-2:desktop-root",
        "frame-dxcam-2:capture-surface",
        "frame-dxcam-2:full",
        "frame-dxcam-2:top-band",
        "frame-dxcam-2:middle-band",
        "frame-dxcam-2:bottom-band",
    )
    assert result.snapshot.layout_tree.find_node("frame-dxcam-2:capture-surface") is not None
    assert len(result.snapshot.region_blocks) == 4
    assert all(isinstance(block, SemanticRegionBlock) for block in result.snapshot.region_blocks)
    assert [block.block_id for block in result.snapshot.region_blocks] == [
        "frame-dxcam-2:full",
        "frame-dxcam-2:top-band",
        "frame-dxcam-2:middle-band",
        "frame-dxcam-2:bottom-band",
    ]
    assert len(result.snapshot.candidates) == 4
    assert all(candidate.actionable is False for candidate in result.snapshot.candidates)
    assert all(candidate.enabled is False for candidate in result.snapshot.candidates)
    assert all(candidate.metadata["observe_only"] is True for candidate in result.snapshot.candidates)
    assert all(candidate.metadata["analysis_only"] is True for candidate in result.snapshot.candidates)
    assert result.snapshot.candidates[0].role == "capture_surface"
    assert result.snapshot.candidates[1].role == "analysis_region"
    assert result.snapshot.metadata["semantic_builder_name"] == "PreparedSemanticStateBuilder"
    assert result.snapshot.metadata["semantic_scaffold"] is True
    assert result.snapshot.metadata["semantic_scaffold_version"] == "enriched-v1"
    assert result.snapshot.metadata["region_block_ids"] == (
        "frame-dxcam-2:full",
        "frame-dxcam-2:top-band",
        "frame-dxcam-2:middle-band",
        "frame-dxcam-2:bottom-band",
    )
    assert result.snapshot.metadata["candidate_ids"] == (
        "frame-dxcam-2:full:candidate",
        "frame-dxcam-2:top-band:candidate",
        "frame-dxcam-2:middle-band:candidate",
        "frame-dxcam-2:bottom-band:candidate",
    )


def test_builder_handles_failed_preparation_result_safely() -> None:
    failed_preparation = FullDesktopCaptureSemanticInputAdapter().prepare(
        CaptureResult.failure(
            provider_name="WindowsObserveOnlyCaptureProvider",
            error_code="dxcam_backend_unavailable",
            error_message="DXcam could not initialize.",
        )
    )

    result = PreparedSemanticStateBuilder().build(failed_preparation)

    assert result.success is False
    assert result.error_code == "preparation_failed"
    assert result.error_message == "DXcam could not initialize."
    assert result.details["preparation_error_code"] == "capture_failed"


def test_builder_handles_partial_preparation_input_safely() -> None:
    partial_input = SemanticExtractionInput(
        frame_id="frame-partial",
        captured_at=datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
        source="WindowsObserveOnlyCaptureProvider",
        capture_provider_name="WindowsObserveOnlyCaptureProvider",
        capture_target="virtual_desktop",
        backend_name="dxcam_desktop",
        width=4,
        height=2,
        origin_x_px=0,
        origin_y_px=0,
        display_count=1,
        payload=_payload(),
        snapshot_preparation=SemanticSnapshotPreparation(
            observed_at=datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
            metadata={
                "source_frame_id": "frame-partial",
                "capture_provider_name": "WindowsObserveOnlyCaptureProvider",
                "capture_target": "virtual_desktop",
                "pixel_format": "bgra_8888",
            },
        ),
    )
    preparation = SemanticExtractionPreparationResult.ok(
        adapter_name="TestPreparationAdapter",
        extraction_input=partial_input,
    )

    result = PreparedSemanticStateBuilder().build(preparation)

    assert result.success is False
    assert result.error_code == "snapshot_metadata_unavailable"
    assert result.details["missing_snapshot_metadata_fields"] == (
        "capture_backend_name",
        "display_count",
    )


def test_enriched_layout_tree_preserves_parent_child_consistency() -> None:
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(_capture_result())

    result = PreparedSemanticStateBuilder().build(preparation)

    assert result.success is True
    assert result.snapshot is not None
    tree = result.snapshot.layout_tree
    assert tree is not None
    root = tree.root
    assert len(root.children) == 1
    surface = root.children[0]
    assert surface.node_id == "frame-dxcam-2:capture-surface"
    assert tuple(child.node_id for child in surface.children) == (
        "frame-dxcam-2:full",
        "frame-dxcam-2:top-band",
        "frame-dxcam-2:middle-band",
        "frame-dxcam-2:bottom-band",
    )


def test_builder_does_not_propagate_unhandled_exceptions() -> None:
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(_capture_result())

    result = RaisingSemanticStateBuilder().build(preparation)

    assert result.success is False
    assert result.error_code == "semantic_state_build_exception"
    assert result.error_message == "builder exploded"
    assert result.details["exception_type"] == "RuntimeError"
