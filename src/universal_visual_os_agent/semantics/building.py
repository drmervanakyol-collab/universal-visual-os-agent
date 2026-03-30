"""Semantic state building from prepared semantic extraction input."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Self

from universal_visual_os_agent.geometry import NormalizedBBox
from universal_visual_os_agent.semantics.layout import SemanticLayoutTree, SemanticNode
from universal_visual_os_agent.semantics.preparation import (
    SemanticExtractionInput,
    SemanticExtractionPreparationResult,
)
from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
    SemanticRegionBlock,
    SemanticStateSnapshot,
)

_FULL_FRAME_BOUNDS = NormalizedBBox(left=0.0, top=0.0, width=1.0, height=1.0)
_VIRTUAL_DESKTOP_TARGET = "virtual_desktop"
_TOP_REGION_BOUNDS = NormalizedBBox(left=0.0, top=0.0, width=1.0, height=0.2)
_MIDDLE_REGION_BOUNDS = NormalizedBBox(left=0.0, top=0.2, width=1.0, height=0.6)
_BOTTOM_REGION_BOUNDS = NormalizedBBox(left=0.0, top=0.8, width=1.0, height=0.2)


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticStateBuildResult:
    """Structured result for semantic state building."""

    builder_name: str
    success: bool
    snapshot: SemanticStateSnapshot | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.builder_name:
            raise ValueError("builder_name must not be empty.")
        if self.success and self.snapshot is None:
            raise ValueError("Successful build results must include snapshot.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed build results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful build results must not include error details.")
        if not self.success and self.snapshot is not None:
            raise ValueError("Failed build results must not include snapshot.")

    @classmethod
    def ok(
        cls,
        *,
        builder_name: str,
        snapshot: SemanticStateSnapshot,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        """Build a successful semantic state result."""

        return cls(
            builder_name=builder_name,
            success=True,
            snapshot=snapshot,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        builder_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        """Build a failed semantic state result."""

        return cls(
            builder_name=builder_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


class PreparedSemanticStateBuilder:
    """Build a minimal observe-only semantic snapshot from prepared capture input."""

    builder_name = "PreparedSemanticStateBuilder"

    def build(self, preparation_result: SemanticExtractionPreparationResult) -> SemanticStateBuildResult:
        """Build a semantic state snapshot or return a safe structured failure."""

        if not preparation_result.success:
            return SemanticStateBuildResult.failure(
                builder_name=self.builder_name,
                error_code="preparation_failed",
                error_message=preparation_result.error_message or "Semantic preparation did not succeed.",
                details={
                    "preparation_error_code": preparation_result.error_code,
                    "preparation_adapter_name": preparation_result.adapter_name,
                },
            )

        extraction_input = preparation_result.extraction_input
        if extraction_input is None:
            return SemanticStateBuildResult.failure(
                builder_name=self.builder_name,
                error_code="extraction_input_unavailable",
                error_message="Semantic preparation did not provide extraction input.",
                details={"preparation_adapter_name": preparation_result.adapter_name},
            )

        if extraction_input.payload is None:
            return SemanticStateBuildResult.failure(
                builder_name=self.builder_name,
                error_code="payload_unavailable",
                error_message="Semantic state building requires a prepared frame payload.",
                details={"frame_id": extraction_input.frame_id},
            )

        missing_metadata_fields = _missing_snapshot_metadata_fields(
            extraction_input.snapshot_preparation.metadata
        )
        if missing_metadata_fields:
            return SemanticStateBuildResult.failure(
                builder_name=self.builder_name,
                error_code="snapshot_metadata_unavailable",
                error_message="Semantic preparation metadata is incomplete for snapshot building.",
                details={
                    "frame_id": extraction_input.frame_id,
                    "missing_snapshot_metadata_fields": missing_metadata_fields,
                },
            )

        if extraction_input.capture_target != _VIRTUAL_DESKTOP_TARGET:
            return SemanticStateBuildResult.failure(
                builder_name=self.builder_name,
                error_code="unsupported_capture_target",
                error_message="Semantic state building requires virtual_desktop preparation input.",
                details={
                    "frame_id": extraction_input.frame_id,
                    "capture_target": extraction_input.capture_target,
                },
            )

        try:
            snapshot = self._build_snapshot_from_input(extraction_input)
        except Exception as exc:  # noqa: BLE001 - builder must stay failure-safe
            return SemanticStateBuildResult.failure(
                builder_name=self.builder_name,
                error_code="semantic_state_build_exception",
                error_message=str(exc),
                details={
                    "frame_id": extraction_input.frame_id,
                    "exception_type": type(exc).__name__,
                },
            )

        return SemanticStateBuildResult.ok(
            builder_name=self.builder_name,
            snapshot=snapshot,
            details={
                "frame_id": extraction_input.frame_id,
                "candidate_count": len(snapshot.candidates),
                "has_layout_tree": snapshot.layout_tree is not None,
            },
        )

    def _build_snapshot_from_input(
        self,
        extraction_input: SemanticExtractionInput,
    ) -> SemanticStateSnapshot:
        root_node_id = f"{extraction_input.frame_id}:desktop-root"
        surface_node_id = f"{extraction_input.frame_id}:capture-surface"
        region_blocks = _build_region_blocks(extraction_input)
        region_nodes = tuple(
            SemanticNode(
                node_id=block.node_id or f"{block.block_id}:node",
                role=block.role,
                name=block.label,
                bounds=block.bounds,
                visible=block.visible,
                enabled=block.enabled,
                attributes=dict(block.metadata),
            )
            for block in region_blocks
        )

        root_node = SemanticNode(
            node_id=root_node_id,
            role="desktop",
            name="Virtual Desktop",
            bounds=_FULL_FRAME_BOUNDS,
            attributes={
                "capture_provider_name": extraction_input.capture_provider_name,
                "capture_target": extraction_input.capture_target,
                "display_count": extraction_input.display_count,
                "origin_x_px": extraction_input.origin_x_px,
                "origin_y_px": extraction_input.origin_y_px,
            },
            children=(
                SemanticNode(
                    node_id=surface_node_id,
                    role="capture_surface",
                    name="Observed Desktop Surface",
                    bounds=_FULL_FRAME_BOUNDS,
                    enabled=False,
                    attributes={
                        "frame_id": extraction_input.frame_id,
                        "backend_name": extraction_input.backend_name,
                        "pixel_format": extraction_input.payload.pixel_format.value,
                        "row_stride_bytes": extraction_input.payload.row_stride_bytes,
                        "width": extraction_input.width,
                        "height": extraction_input.height,
                        "semantic_scaffold_kind": "capture_surface",
                    },
                    children=region_nodes,
                ),
            ),
        )
        layout_tree = SemanticLayoutTree(root=root_node, display_id="virtual_desktop")
        candidates = tuple(
            SemanticCandidate(
                candidate_id=f"{block.block_id}:candidate",
                label=block.label,
                bounds=block.bounds,
                node_id=block.node_id,
                role=block.role,
                confidence=1.0,
                visible=block.visible,
                enabled=False,
                metadata={
                    **dict(block.metadata),
                    "observe_only": True,
                    "semantic_origin": "prepared_capture_scaffold",
                    "backend_name": extraction_input.backend_name,
                    "frame_id": extraction_input.frame_id,
                    "region_block_id": block.block_id,
                    "analysis_only": True,
                },
            )
            for block in region_blocks
        )
        return SemanticStateSnapshot(
            layout_tree=layout_tree,
            region_blocks=region_blocks,
            candidates=candidates,
            observed_at=extraction_input.snapshot_preparation.observed_at,
            metadata={
                **dict(extraction_input.snapshot_preparation.metadata),
                "semantic_builder_name": self.builder_name,
                "semantic_scaffold": True,
                "semantic_scaffold_version": "enriched-v1",
                "layout_root_node_id": root_node_id,
                "capture_surface_node_id": surface_node_id,
                "region_block_ids": tuple(block.block_id for block in region_blocks),
                "candidate_ids": tuple(candidate.candidate_id for candidate in candidates),
            },
        )


def _build_region_blocks(
    extraction_input: SemanticExtractionInput,
) -> tuple[SemanticRegionBlock, ...]:
    region_specs = (
        ("full", "Observed Desktop Surface", "capture_surface", _FULL_FRAME_BOUNDS),
        ("top-band", "Top Analysis Band", "analysis_region", _TOP_REGION_BOUNDS),
        ("middle-band", "Middle Analysis Band", "analysis_region", _MIDDLE_REGION_BOUNDS),
        ("bottom-band", "Bottom Analysis Band", "analysis_region", _BOTTOM_REGION_BOUNDS),
    )
    return tuple(
        SemanticRegionBlock(
            block_id=f"{extraction_input.frame_id}:{region_key}",
            label=label,
            bounds=bounds,
            node_id=f"{extraction_input.frame_id}:{region_key}",
            role=role,
            enabled=False,
            metadata={
                "observe_only": True,
                "analysis_only": True,
                "region_key": region_key,
                "semantic_scaffold_kind": "capture_region",
                "backend_name": extraction_input.backend_name,
                "frame_id": extraction_input.frame_id,
                "display_count": extraction_input.display_count,
            },
        )
        for region_key, label, role, bounds in region_specs
    )


def _missing_snapshot_metadata_fields(
    snapshot_metadata: Mapping[str, object],
) -> tuple[str, ...]:
    missing_fields: list[str] = []
    required_strings = (
        "source_frame_id",
        "capture_provider_name",
        "capture_target",
        "capture_backend_name",
        "pixel_format",
    )
    for field_name in required_strings:
        value = snapshot_metadata.get(field_name)
        if not isinstance(value, str) or not value:
            missing_fields.append(field_name)

    display_count = snapshot_metadata.get("display_count")
    if not isinstance(display_count, int) or display_count <= 0:
        missing_fields.append("display_count")
    return tuple(missing_fields)
