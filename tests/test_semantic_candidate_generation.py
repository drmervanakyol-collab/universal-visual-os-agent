from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from universal_visual_os_agent.geometry import NormalizedBBox
from universal_visual_os_agent.integrations.windows import WindowsCaptureTarget
from universal_visual_os_agent.perception import (
    CaptureResult,
    CapturedFrame,
    FrameImagePayload,
    ObserveOnlyHeuristicVisualGroundingConfig,
    ObserveOnlyHeuristicVisualGroundingProvider,
    VisualGroundingAvailability,
)
from universal_visual_os_agent.semantics import (
    FullDesktopCaptureSemanticInputAdapter,
    GeometricLayoutRegionAnalyzer,
    OcrAwareSemanticLayoutEnricher,
    ObserveOnlyCandidateGenerator,
    PreparedSemanticStateBuilder,
    PreparedSemanticTextExtractionAdapter,
    SemanticCandidate,
    SemanticCandidateClass,
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
        self.backend_name = "static_candidate_backend"
        self._response_factory = response_factory

    def run(self, request):
        return self._response_factory(request)


class _ExplodingCandidateGenerator(ObserveOnlyCandidateGenerator):
    def _build_generated_candidates(self, snapshot, *, existing_candidate_ids):
        raise RuntimeError("candidate generator exploded")


def _payload(*, width: int = 1400, height: int = 800) -> FrameImagePayload:
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
            frame_id="frame-candidate-generation-1",
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


def _semantic_layout_snapshot() -> SemanticStateSnapshot:
    capture_result = _capture_result(_payload())
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(capture_result)
    state_result = PreparedSemanticStateBuilder().build(preparation)
    text_result = PreparedSemanticTextExtractionAdapter(
        text_backend=_StaticResponseBackend(_candidate_rich_response)
    ).extract(preparation, state_result)
    assert text_result.success is True
    assert text_result.enriched_snapshot is not None
    layout_result = GeometricLayoutRegionAnalyzer().analyze(text_result.enriched_snapshot)
    assert layout_result.success is True
    assert layout_result.snapshot is not None
    semantic_layout_result = OcrAwareSemanticLayoutEnricher().enrich(layout_result.snapshot)
    assert semantic_layout_result.success is True
    assert semantic_layout_result.snapshot is not None
    return semantic_layout_result.snapshot


def _semantic_layout_snapshot_turkish() -> SemanticStateSnapshot:
    capture_result = _capture_result(_payload())
    preparation = FullDesktopCaptureSemanticInputAdapter().prepare(capture_result)
    state_result = PreparedSemanticStateBuilder().build(preparation)
    text_result = PreparedSemanticTextExtractionAdapter(
        text_backend=_StaticResponseBackend(_turkish_candidate_rich_response)
    ).extract(preparation, state_result)
    assert text_result.success is True
    assert text_result.enriched_snapshot is not None
    layout_result = GeometricLayoutRegionAnalyzer().analyze(text_result.enriched_snapshot)
    assert layout_result.success is True
    assert layout_result.snapshot is not None
    semantic_layout_result = OcrAwareSemanticLayoutEnricher().enrich(layout_result.snapshot)
    assert semantic_layout_result.success is True
    assert semantic_layout_result.snapshot is not None
    return semantic_layout_result.snapshot


def _candidate_rich_response(request) -> TextExtractionResponse:
    regions_by_label = {region.label: region for region in request.regions}
    full_region = regions_by_label["Observed Desktop Surface"]
    top_region = regions_by_label["Top Analysis Band"]
    middle_region = regions_by_label["Middle Analysis Band"]
    bottom_region = regions_by_label["Bottom Analysis Band"]
    return TextExtractionResponse(
        status=TextExtractionResponseStatus.completed,
        backend_name="static_candidate_backend",
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
                confidence=0.86,
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
                extracted_text="Home Projects Settings",
                confidence=0.95,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextRegion(
                region_id=middle_region.region_id,
                label=middle_region.label,
                bounds=middle_region.bounds,
                node_id=middle_region.node_id,
                block_id=middle_region.block_id,
                role=middle_region.role,
                status=SemanticTextStatus.extracted,
                enabled=False,
                extracted_text="Search projects Confirm changes Save Cancel X",
                confidence=0.9,
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
                bounds=NormalizedBBox(left=0.04, top=0.04, width=0.36, height=0.08),
                enabled=False,
                extracted_text="Home Projects Settings",
                confidence=0.95,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{middle_region.region_id}:line:1",
                region_id=middle_region.region_id,
                label="Left Navigation",
                bounds=NormalizedBBox(left=0.03, top=0.28, width=0.14, height=0.2),
                enabled=False,
                extracted_text="Overview Tasks Reports",
                confidence=0.9,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{middle_region.region_id}:line:2",
                region_id=middle_region.region_id,
                label="Search Field",
                bounds=NormalizedBBox(left=0.28, top=0.28, width=0.28, height=0.08),
                enabled=False,
                extracted_text="Search projects",
                confidence=0.91,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{middle_region.region_id}:line:3",
                region_id=middle_region.region_id,
                label="Dialog Title",
                bounds=NormalizedBBox(left=0.38, top=0.34, width=0.22, height=0.06),
                enabled=False,
                extracted_text="Confirm changes",
                confidence=0.88,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{middle_region.region_id}:line:4",
                region_id=middle_region.region_id,
                label="Dialog Close",
                bounds=NormalizedBBox(left=0.59, top=0.35, width=0.03, height=0.04),
                enabled=False,
                extracted_text="X",
                confidence=0.94,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{middle_region.region_id}:line:5",
                region_id=middle_region.region_id,
                label="Primary Action",
                bounds=NormalizedBBox(left=0.42, top=0.46, width=0.09, height=0.07),
                enabled=False,
                extracted_text="Save",
                confidence=0.96,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{middle_region.region_id}:line:6",
                region_id=middle_region.region_id,
                label="Dismiss Action",
                bounds=NormalizedBBox(left=0.53, top=0.46, width=0.11, height=0.07),
                enabled=False,
                extracted_text="Cancel",
                confidence=0.95,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{bottom_region.region_id}:line:1",
                region_id=bottom_region.region_id,
                label="Status Footer",
                bounds=NormalizedBBox(left=0.25, top=0.84, width=0.36, height=0.06),
                enabled=False,
                extracted_text="Ready Connected",
                confidence=0.92,
                metadata={"observe_only": True, "analysis_only": True},
            ),
        ),
    )


def _turkish_candidate_rich_response(request) -> TextExtractionResponse:
    regions_by_label = {region.label: region for region in request.regions}
    full_region = regions_by_label["Observed Desktop Surface"]
    top_region = regions_by_label["Top Analysis Band"]
    middle_region = regions_by_label["Middle Analysis Band"]
    bottom_region = regions_by_label["Bottom Analysis Band"]
    return TextExtractionResponse(
        status=TextExtractionResponseStatus.completed,
        backend_name="static_candidate_backend",
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
                confidence=0.86,
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
                extracted_text="Ana sayfa Görevler Ayarlar",
                confidence=0.95,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextRegion(
                region_id=middle_region.region_id,
                label=middle_region.label,
                bounds=middle_region.bounds,
                node_id=middle_region.node_id,
                block_id=middle_region.block_id,
                role=middle_region.role,
                status=SemanticTextStatus.extracted,
                enabled=False,
                extracted_text="Ara öğeler Değişiklikleri onayla Güncelle İptal Çıkış",
                confidence=0.9,
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
                extracted_text="Hazır Bağlandı",
                confidence=0.92,
                metadata={"observe_only": True, "analysis_only": True},
            ),
        ),
        text_blocks=(
            SemanticTextBlock(
                text_block_id=f"{top_region.region_id}:line:1",
                region_id=top_region.region_id,
                label="Top Navigation Turkish",
                bounds=NormalizedBBox(left=0.04, top=0.04, width=0.36, height=0.08),
                enabled=False,
                extracted_text="Ana sayfa Görevler Ayarlar",
                confidence=0.95,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{middle_region.region_id}:line:1",
                region_id=middle_region.region_id,
                label="Search Field Turkish",
                bounds=NormalizedBBox(left=0.28, top=0.28, width=0.28, height=0.08),
                enabled=False,
                extracted_text="Ara öğeler",
                confidence=0.91,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{middle_region.region_id}:line:2",
                region_id=middle_region.region_id,
                label="Dialog Title Turkish",
                bounds=NormalizedBBox(left=0.38, top=0.34, width=0.24, height=0.06),
                enabled=False,
                extracted_text="Değişiklikleri onayla",
                confidence=0.88,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{middle_region.region_id}:line:3",
                region_id=middle_region.region_id,
                label="Dialog Close Turkish",
                bounds=NormalizedBBox(left=0.59, top=0.35, width=0.05, height=0.04),
                enabled=False,
                extracted_text="Çıkış",
                confidence=0.94,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{middle_region.region_id}:line:4",
                region_id=middle_region.region_id,
                label="Primary Action Turkish",
                bounds=NormalizedBBox(left=0.42, top=0.46, width=0.11, height=0.07),
                enabled=False,
                extracted_text="Güncelle",
                confidence=0.96,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{middle_region.region_id}:line:5",
                region_id=middle_region.region_id,
                label="Dismiss Action Turkish",
                bounds=NormalizedBBox(left=0.54, top=0.46, width=0.11, height=0.07),
                enabled=False,
                extracted_text="İptal",
                confidence=0.95,
                metadata={"observe_only": True, "analysis_only": True},
            ),
            SemanticTextBlock(
                text_block_id=f"{bottom_region.region_id}:line:1",
                region_id=bottom_region.region_id,
                label="Status Footer Turkish",
                bounds=NormalizedBBox(left=0.25, top=0.84, width=0.36, height=0.06),
                enabled=False,
                extracted_text="Hazır Bağlandı",
                confidence=0.92,
                metadata={"observe_only": True, "analysis_only": True},
            ),
        ),
    )


def _generated_candidates(snapshot: SemanticStateSnapshot) -> tuple[SemanticCandidate, ...]:
    return tuple(
        candidate
        for candidate in snapshot.candidates
        if candidate.metadata.get("semantic_origin") == "candidate_generation"
    )


def test_candidate_generation_builds_non_actionable_candidates_from_enriched_snapshot() -> None:
    snapshot = _semantic_layout_snapshot()

    result = ObserveOnlyCandidateGenerator().generate(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    generated_snapshot = result.snapshot
    generated_candidates = _generated_candidates(generated_snapshot)
    generated_classes = {candidate.candidate_class for candidate in generated_candidates}
    assert generated_snapshot.metadata["candidate_generation"] is True
    assert generated_snapshot.metadata["generated_candidate_ids"]
    assert {
        SemanticCandidateClass.button_like,
        SemanticCandidateClass.input_like,
        SemanticCandidateClass.tab_like,
        SemanticCandidateClass.close_like,
        SemanticCandidateClass.popup_dismiss_like,
        SemanticCandidateClass.interactive_region_like,
    }.issubset(generated_classes)
    assert all(candidate.enabled is False for candidate in generated_candidates)


def test_candidate_generation_adds_visual_grounding_metadata_safely() -> None:
    snapshot = _semantic_layout_snapshot()

    result = ObserveOnlyCandidateGenerator().generate(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    generated_candidates = {
        candidate.label: candidate
        for candidate in _generated_candidates(result.snapshot)
    }
    close_candidate = generated_candidates["X"]
    input_candidate = generated_candidates["Search projects"]
    assert close_candidate.metadata["visual_grounding_support_status"] == "available"
    assert "close_affordance_like" in close_candidate.metadata["visual_grounding_cue_kinds"]
    assert close_candidate.metadata["visual_grounding_reference_anchor"] == "center_right"
    assert input_candidate.metadata["visual_grounding_support_status"] == "available"
    assert "input_affordance_like" in input_candidate.metadata["visual_grounding_cue_kinds"]
    assert result.snapshot.metadata["generated_candidate_visual_grounding_status_counts"]
    assert result.snapshot.metadata["generated_candidate_visual_grounding_cue_counts"]


def test_candidate_generation_handles_unavailable_visual_grounding_support_safely() -> None:
    snapshot = _semantic_layout_snapshot()
    generator = ObserveOnlyCandidateGenerator(
        visual_grounder=ObserveOnlyHeuristicVisualGroundingProvider(
            config=ObserveOnlyHeuristicVisualGroundingConfig(
                availability=VisualGroundingAvailability.unavailable
            )
        )
    )

    result = generator.generate(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    generated_candidates = _generated_candidates(result.snapshot)
    assert generated_candidates
    assert all(
        candidate.metadata["visual_grounding_support_status"] == "unavailable"
        for candidate in generated_candidates
    )
    assert ("unavailable", len(generated_candidates)) in result.snapshot.metadata[
        "generated_candidate_visual_grounding_status_counts"
    ]
    assert all(candidate.actionable is False for candidate in generated_candidates)


def test_candidate_generation_candidate_metadata_is_consistent() -> None:
    snapshot = _semantic_layout_snapshot()

    result = ObserveOnlyCandidateGenerator().generate(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    generated_snapshot = result.snapshot
    layout_region_ids = {region.region_id for region in generated_snapshot.layout_regions}
    text_region_ids = {region.region_id for region in generated_snapshot.text_regions}
    text_block_ids = {block.text_block_id for block in generated_snapshot.text_blocks}
    generated_candidates = _generated_candidates(generated_snapshot)
    assert generated_snapshot.metadata["candidate_ids"] == tuple(
        candidate.candidate_id for candidate in generated_snapshot.candidates
    )
    for candidate in generated_candidates:
        assert candidate.candidate_class is not None
        assert candidate.heuristic_explanations
        assert candidate.metadata["candidate_class"] == candidate.candidate_class.value
        assert candidate.metadata["heuristic_explanations"] == candidate.heuristic_explanations
        assert candidate.metadata["source_layout_region_id"] in layout_region_ids
        source_text_region_id = candidate.metadata["source_text_region_id"]
        if source_text_region_id is not None:
            assert source_text_region_id in text_region_ids
        source_text_block_id = candidate.metadata["source_text_block_id"]
        if source_text_block_id is not None:
            assert source_text_block_id in text_block_ids


def test_candidate_generation_handles_turkish_ui_text_safely() -> None:
    snapshot = _semantic_layout_snapshot_turkish()

    result = ObserveOnlyCandidateGenerator().generate(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    generated_candidates = _generated_candidates(result.snapshot)
    candidates_by_label = {candidate.label: candidate for candidate in generated_candidates}
    assert candidates_by_label["Ara öğeler"].candidate_class is SemanticCandidateClass.input_like
    assert candidates_by_label["Güncelle"].candidate_class is SemanticCandidateClass.button_like
    assert candidates_by_label["İptal"].candidate_class is SemanticCandidateClass.popup_dismiss_like
    assert candidates_by_label["Çıkış"].candidate_class is SemanticCandidateClass.close_like
    assert candidates_by_label["ayarlar"].candidate_class is SemanticCandidateClass.tab_like
    assert all(candidate.actionable is False for candidate in generated_candidates)


def test_candidate_generation_handles_partial_inputs_safely() -> None:
    snapshot = _semantic_layout_snapshot()
    dialog_region = next(
        region
        for region in snapshot.layout_regions
        if region.semantic_role is SemanticLayoutRole.dialog_overlay
    )
    partial_snapshot = replace(
        snapshot,
        layout_regions=tuple(
            replace(
                region,
                semantic_role=None,
                metadata={
                    key: value
                    for key, value in region.metadata.items()
                    if key != "semantic_layout_signal_status"
                },
            )
            if region.region_id == dialog_region.region_id
            else region
            for region in snapshot.layout_regions
        ),
        text_blocks=(
            replace(snapshot.text_blocks[0], extracted_text=None, confidence=None),
            *snapshot.text_blocks[1:],
        ),
    )

    result = ObserveOnlyCandidateGenerator().generate(partial_snapshot)

    assert result.success is True
    assert result.snapshot is not None
    generated_snapshot = result.snapshot
    assert generated_snapshot.metadata["candidate_generation_signal_status"] == "partial"
    assert dialog_region.region_id in generated_snapshot.metadata[
        "candidate_generation_missing_semantic_role_region_ids"
    ]
    assert snapshot.text_blocks[0].text_block_id in generated_snapshot.metadata[
        "candidate_generation_ignored_text_block_ids"
    ]
    assert all(candidate.actionable is False for candidate in _generated_candidates(generated_snapshot))


def test_candidate_generation_requires_semantic_layout_enrichment_output() -> None:
    snapshot = _semantic_layout_snapshot()
    incomplete_snapshot = replace(
        snapshot,
        metadata={
            key: value
            for key, value in snapshot.metadata.items()
            if key != "semantic_layout_enrichment"
        },
    )

    result = ObserveOnlyCandidateGenerator().generate(incomplete_snapshot)

    assert result.success is False
    assert result.error_code == "semantic_layout_enrichment_unavailable"


def test_candidate_generation_preserves_observe_only_semantics() -> None:
    snapshot = _semantic_layout_snapshot()

    result = ObserveOnlyCandidateGenerator().generate(snapshot)

    assert result.success is True
    assert result.snapshot is not None
    for candidate in _generated_candidates(result.snapshot):
        assert candidate.metadata["observe_only"] is True
        assert candidate.metadata["analysis_only"] is True
        assert candidate.metadata["non_actionable_candidate"] is True
        assert candidate.metadata["non_actionable_reason"]
        assert candidate.enabled is False
        assert candidate.actionable is False


def test_candidate_generation_does_not_propagate_unhandled_exceptions() -> None:
    snapshot = _semantic_layout_snapshot()

    result = _ExplodingCandidateGenerator().generate(snapshot)

    assert result.success is False
    assert result.error_code == "candidate_generation_exception"
    assert result.error_message == "candidate generator exploded"
