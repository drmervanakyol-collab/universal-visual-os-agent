from __future__ import annotations

from datetime import UTC, datetime

import pytest

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
    SemanticExtractionPreparationResult,
    SemanticStateBuildResult,
    SemanticStateSnapshot,
    SemanticTextBlock,
    SemanticTextRegion,
    SemanticTextStatus,
    TextExtractionResponse,
    TextExtractionResponseStatus,
)


class RaisingTextExtractionAdapter(PreparedSemanticTextExtractionAdapter):
    def _build_request(self, extraction_input, snapshot):
        raise RuntimeError("ocr adapter exploded")


class FakeExtractionInput:
    def __init__(self) -> None:
        self.frame_id = "frame-missing-payload"
        self.captured_at = datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC)
        self.source = "WindowsObserveOnlyCaptureProvider"
        self.capture_provider_name = "WindowsObserveOnlyCaptureProvider"
        self.capture_target = "virtual_desktop"
        self.backend_name = "dxcam_desktop"
        self.width = 4
        self.height = 2
        self.origin_x_px = 0
        self.origin_y_px = 0
        self.display_count = 1
        self.payload = None
        self.snapshot_preparation = type(
            "FakeSnapshotPreparation",
            (),
            {
                "observed_at": datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC),
                "metadata": {
                    "source_frame_id": "frame-missing-payload",
                    "capture_provider_name": "WindowsObserveOnlyCaptureProvider",
                    "capture_target": "virtual_desktop",
                    "capture_backend_name": "dxcam_desktop",
                    "display_count": 1,
                    "pixel_format": "bgra_8888",
                },
            },
        )()
        self.frame_metadata = {}
        self.capture_details = {}


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
            frame_id="frame-dxcam-text-1",
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


def test_successful_semantic_pipeline_builds_text_extraction_placeholders() -> None:
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(_capture_result())
    state_result = PreparedSemanticStateBuilder().build(preparation)

    result = PreparedSemanticTextExtractionAdapter().extract(preparation, state_result)

    assert result.success is True
    assert result.request is not None
    assert result.response is not None
    assert len(result.request.regions) == 4
    assert len(result.text_regions) == 4
    assert len(result.text_blocks) == 4
    assert all(isinstance(region, SemanticTextRegion) for region in result.text_regions)
    assert all(isinstance(block, SemanticTextBlock) for block in result.text_blocks)
    assert all(region.status is SemanticTextStatus.pending for region in result.text_regions)
    assert all(region.extracted_text is None for region in result.text_regions)
    assert all(region.enabled is False for region in result.text_regions)
    assert all(block.extracted_text is None for block in result.text_blocks)
    assert all(block.enabled is False for block in result.text_blocks)
    assert result.response.status is TextExtractionResponseStatus.pending
    assert result.response.backend_name is None
    assert result.enriched_snapshot is not None
    assert len(result.enriched_snapshot.text_regions) == 4
    assert len(result.enriched_snapshot.text_blocks) == 4
    assert result.enriched_snapshot.metadata["text_extraction_scaffold"] is True
    assert result.enriched_snapshot.metadata["text_region_ids"] == tuple(
        region.region_id for region in result.text_regions
    )
    assert result.enriched_snapshot.metadata["text_block_ids"] == tuple(
        block.text_block_id for block in result.text_blocks
    )
    assert all(candidate.actionable is False for candidate in result.enriched_snapshot.candidates)


def test_text_extraction_adapter_handles_failed_preparation_safely() -> None:
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(
        CaptureResult.failure(
            provider_name="WindowsObserveOnlyCaptureProvider",
            error_code="dxcam_backend_unavailable",
            error_message="DXcam could not initialize.",
        )
    )
    state_result = SemanticStateBuildResult.failure(
        builder_name="PreparedSemanticStateBuilder",
        error_code="preparation_failed",
        error_message="Semantic preparation did not succeed.",
    )

    result = PreparedSemanticTextExtractionAdapter().extract(preparation, state_result)

    assert result.success is False
    assert result.error_code == "preparation_failed"
    assert result.details["preparation_error_code"] == "capture_failed"


def test_text_extraction_adapter_handles_failed_state_build_safely() -> None:
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(_capture_result())
    state_result = SemanticStateBuildResult.failure(
        builder_name="PreparedSemanticStateBuilder",
        error_code="snapshot_metadata_unavailable",
        error_message="Semantic preparation metadata is incomplete for snapshot building.",
    )

    result = PreparedSemanticTextExtractionAdapter().extract(preparation, state_result)

    assert result.success is False
    assert result.error_code == "state_build_failed"
    assert result.details["state_error_code"] == "snapshot_metadata_unavailable"


def test_text_extraction_adapter_handles_missing_payload_safely() -> None:
    preparation = SemanticExtractionPreparationResult.ok(
        adapter_name="TestPreparationAdapter",
        extraction_input=FakeExtractionInput(),
    )
    state_result = SemanticStateBuildResult.ok(
        builder_name="PreparedSemanticStateBuilder",
        snapshot=SemanticStateSnapshot(),
    )

    result = PreparedSemanticTextExtractionAdapter().extract(preparation, state_result)

    assert result.success is False
    assert result.error_code == "payload_unavailable"
    assert result.details["frame_id"] == "frame-missing-payload"


def test_text_extraction_adapter_handles_missing_region_blocks_safely() -> None:
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(_capture_result())
    state_result = SemanticStateBuildResult.ok(
        builder_name="PreparedSemanticStateBuilder",
        snapshot=SemanticStateSnapshot(),
    )

    result = PreparedSemanticTextExtractionAdapter().extract(preparation, state_result)

    assert result.success is False
    assert result.error_code == "text_regions_unavailable"
    assert result.details["snapshot_id"] == state_result.snapshot.snapshot_id


def test_text_extraction_adapter_does_not_propagate_unhandled_exceptions() -> None:
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(_capture_result())
    state_result = PreparedSemanticStateBuilder().build(preparation)

    result = RaisingTextExtractionAdapter().extract(preparation, state_result)

    assert result.success is False
    assert result.error_code == "text_extraction_exception"
    assert result.error_message == "ocr adapter exploded"
    assert result.details["exception_type"] == "RuntimeError"


def test_text_extraction_response_requires_error_code_for_failed_status() -> None:
    with pytest.raises(ValueError, match="Failed text extraction responses must include error_code"):
        TextExtractionResponse(status=TextExtractionResponseStatus.failed)
