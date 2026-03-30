"""Geometric layout and region analysis on top of semantic snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping, Self

from universal_visual_os_agent.geometry import NormalizedBBox
from universal_visual_os_agent.semantics.layout import SemanticLayoutTree, SemanticNode
from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
    SemanticLayoutRegion,
    SemanticLayoutRegionKind,
    SemanticRegionBlock,
    SemanticStateSnapshot,
    SemanticTextBlock,
    SemanticTextStatus,
)


@dataclass(slots=True, frozen=True, kw_only=True)
class LayoutRegionAnalysisResult:
    """Structured result for geometric layout region analysis."""

    analyzer_name: str
    success: bool
    snapshot: SemanticStateSnapshot | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.analyzer_name:
            raise ValueError("analyzer_name must not be empty.")
        if self.success and self.snapshot is None:
            raise ValueError("Successful analysis results must include snapshot.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed analysis results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful analysis results must not include error details.")
        if not self.success and self.snapshot is not None:
            raise ValueError("Failed analysis results must not include snapshot.")

    @classmethod
    def ok(
        cls,
        *,
        analyzer_name: str,
        snapshot: SemanticStateSnapshot,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            analyzer_name=analyzer_name,
            success=True,
            snapshot=snapshot,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        analyzer_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            analyzer_name=analyzer_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


class GeometricLayoutRegionAnalyzer:
    """Derive stable observe-only layout regions from snapshot geometry and OCR metadata."""

    analyzer_name = "GeometricLayoutRegionAnalyzer"

    def analyze(self, snapshot: SemanticStateSnapshot) -> LayoutRegionAnalysisResult:
        if snapshot.layout_tree is None:
            return LayoutRegionAnalysisResult.failure(
                analyzer_name=self.analyzer_name,
                error_code="layout_tree_unavailable",
                error_message="Layout region analysis requires a semantic layout tree.",
            )
        capture_surface_node_id = snapshot.metadata.get("capture_surface_node_id")
        if not isinstance(capture_surface_node_id, str) or not capture_surface_node_id:
            return LayoutRegionAnalysisResult.failure(
                analyzer_name=self.analyzer_name,
                error_code="capture_surface_metadata_unavailable",
                error_message="Snapshot metadata is missing capture_surface_node_id.",
            )
        capture_surface_node = snapshot.layout_tree.find_node(capture_surface_node_id)
        if capture_surface_node is None:
            return LayoutRegionAnalysisResult.failure(
                analyzer_name=self.analyzer_name,
                error_code="capture_surface_node_unavailable",
                error_message="Layout tree does not contain the capture surface node.",
                details={"capture_surface_node_id": capture_surface_node_id},
            )

        region_blocks_by_key = _region_blocks_by_key(snapshot)
        missing_region_keys = tuple(
            region_key
            for region_key in ("full", "top-band", "middle-band", "bottom-band")
            if region_key not in region_blocks_by_key
        )
        if missing_region_keys:
            return LayoutRegionAnalysisResult.failure(
                analyzer_name=self.analyzer_name,
                error_code="required_region_blocks_unavailable",
                error_message="Snapshot does not contain the required geometric region scaffold.",
                details={"missing_region_keys": missing_region_keys},
            )

        try:
            layout_regions = self._build_layout_regions(snapshot, region_blocks_by_key)
            layout_tree = self._enrich_layout_tree(
                snapshot.layout_tree,
                capture_surface_node_id=capture_surface_node_id,
                layout_regions=layout_regions,
            )
            region_candidates = self._build_region_candidates(layout_regions)
            enriched_snapshot = replace(
                snapshot,
                layout_tree=layout_tree,
                layout_regions=layout_regions,
                candidates=snapshot.candidates + region_candidates,
                metadata={
                    **dict(snapshot.metadata),
                    "layout_region_analysis": True,
                    "layout_region_ids": tuple(region.region_id for region in layout_regions),
                    "layout_region_candidate_ids": tuple(
                        candidate.candidate_id for candidate in region_candidates
                    ),
                    "layout_region_analyzer_name": self.analyzer_name,
                },
            )
        except Exception as exc:  # noqa: BLE001 - analyzer must fail safely
            return LayoutRegionAnalysisResult.failure(
                analyzer_name=self.analyzer_name,
                error_code="layout_region_analysis_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return LayoutRegionAnalysisResult.ok(
            analyzer_name=self.analyzer_name,
            snapshot=enriched_snapshot,
            details={
                "layout_region_count": len(layout_regions),
                "layout_region_candidate_count": len(region_candidates),
                "has_modal_like_region": any(
                    region.kind is SemanticLayoutRegionKind.modal_like for region in layout_regions
                ),
            },
        )

    def _build_layout_regions(
        self,
        snapshot: SemanticStateSnapshot,
        region_blocks_by_key: Mapping[str, SemanticRegionBlock],
    ) -> tuple[SemanticLayoutRegion, ...]:
        full_block = region_blocks_by_key["full"]
        top_block = region_blocks_by_key["top-band"]
        middle_block = region_blocks_by_key["middle-band"]
        bottom_block = region_blocks_by_key["bottom-band"]
        frame_id = snapshot.metadata.get("source_frame_id")
        if not isinstance(frame_id, str) or not frame_id:
            raise ValueError("Snapshot metadata is missing source_frame_id.")

        layout_regions: list[SemanticLayoutRegion] = [
            SemanticLayoutRegion(
                region_id=f"{frame_id}:layout:full-surface",
                kind=SemanticLayoutRegionKind.full_surface,
                label="Full Surface Region",
                bounds=full_block.bounds,
                node_id=f"{frame_id}:layout:full-surface",
                source_region_block_ids=(full_block.block_id,),
                metadata={
                    "observe_only": True,
                    "analysis_only": True,
                    "layout_region_analysis": True,
                },
            ),
            SemanticLayoutRegion(
                region_id=f"{frame_id}:layout:header",
                kind=SemanticLayoutRegionKind.header,
                label="Header Region",
                bounds=top_block.bounds,
                node_id=f"{frame_id}:layout:header",
                parent_region_id=f"{frame_id}:layout:full-surface",
                source_region_block_ids=(top_block.block_id,),
                metadata={
                    "observe_only": True,
                    "analysis_only": True,
                    "layout_region_analysis": True,
                },
            ),
            SemanticLayoutRegion(
                region_id=f"{frame_id}:layout:content",
                kind=SemanticLayoutRegionKind.content,
                label="Content Region",
                bounds=middle_block.bounds,
                node_id=f"{frame_id}:layout:content",
                parent_region_id=f"{frame_id}:layout:full-surface",
                source_region_block_ids=(middle_block.block_id,),
                metadata={
                    "observe_only": True,
                    "analysis_only": True,
                    "layout_region_analysis": True,
                },
            ),
            SemanticLayoutRegion(
                region_id=f"{frame_id}:layout:footer",
                kind=SemanticLayoutRegionKind.footer,
                label="Footer Region",
                bounds=bottom_block.bounds,
                node_id=f"{frame_id}:layout:footer",
                parent_region_id=f"{frame_id}:layout:full-surface",
                source_region_block_ids=(bottom_block.block_id,),
                metadata={
                    "observe_only": True,
                    "analysis_only": True,
                    "layout_region_analysis": True,
                },
            ),
        ]

        content_region = layout_regions[2]
        capture_surface_node = snapshot.layout_tree.find_node(
            snapshot.metadata["capture_surface_node_id"]
        )
        aspect_ratio = _capture_surface_aspect_ratio(capture_surface_node)
        if aspect_ratio >= 1.2:
            sidebar_width = min(content_region.bounds.width * 0.18, 0.22)
            left_sidebar_bounds = NormalizedBBox(
                left=content_region.bounds.left,
                top=content_region.bounds.top,
                width=sidebar_width,
                height=content_region.bounds.height,
            )
            right_sidebar_bounds = NormalizedBBox(
                left=(content_region.bounds.left + content_region.bounds.width) - sidebar_width,
                top=content_region.bounds.top,
                width=sidebar_width,
                height=content_region.bounds.height,
            )
            layout_regions.extend(
                (
                    SemanticLayoutRegion(
                        region_id=f"{frame_id}:layout:left-sidebar",
                        kind=SemanticLayoutRegionKind.left_sidebar,
                        label="Left Sidebar Region",
                        bounds=left_sidebar_bounds,
                        node_id=f"{frame_id}:layout:left-sidebar",
                        parent_region_id=content_region.region_id,
                        source_region_block_ids=(middle_block.block_id,),
                        metadata={
                            "observe_only": True,
                            "analysis_only": True,
                            "layout_region_analysis": True,
                        },
                    ),
                    SemanticLayoutRegion(
                        region_id=f"{frame_id}:layout:right-sidebar",
                        kind=SemanticLayoutRegionKind.right_sidebar,
                        label="Right Sidebar Region",
                        bounds=right_sidebar_bounds,
                        node_id=f"{frame_id}:layout:right-sidebar",
                        parent_region_id=content_region.region_id,
                        source_region_block_ids=(middle_block.block_id,),
                        metadata={
                            "observe_only": True,
                            "analysis_only": True,
                            "layout_region_analysis": True,
                        },
                    ),
                )
            )

        modal_region = _derive_modal_like_region(
            snapshot.text_blocks,
            content_region=content_region,
            frame_id=frame_id,
        )
        if modal_region is not None:
            layout_regions.append(modal_region)
        return tuple(layout_regions)

    def _enrich_layout_tree(
        self,
        layout_tree: SemanticLayoutTree,
        *,
        capture_surface_node_id: str,
        layout_regions: tuple[SemanticLayoutRegion, ...],
    ) -> SemanticLayoutTree:
        group_node = _build_layout_region_group(layout_regions)
        return replace(
            layout_tree,
            root=_insert_layout_region_group(
                layout_tree.root,
                capture_surface_node_id=capture_surface_node_id,
                group_node=group_node,
            ),
        )

    def _build_region_candidates(
        self,
        layout_regions: tuple[SemanticLayoutRegion, ...],
    ) -> tuple[SemanticCandidate, ...]:
        return tuple(
            SemanticCandidate(
                candidate_id=f"{region.region_id}:candidate",
                label=region.label,
                bounds=region.bounds,
                node_id=region.node_id,
                role="layout_region",
                confidence=region.confidence,
                visible=region.visible,
                enabled=False,
                metadata={
                    **dict(region.metadata),
                    "layout_region_id": region.region_id,
                    "layout_region_kind": region.kind.value,
                    "semantic_origin": "layout_region_analysis",
                    "observe_only": True,
                    "analysis_only": True,
                },
            )
            for region in layout_regions
        )


def _region_blocks_by_key(snapshot: SemanticStateSnapshot) -> Mapping[str, SemanticRegionBlock]:
    region_blocks: dict[str, SemanticRegionBlock] = {}
    for block in snapshot.region_blocks:
        region_key = block.metadata.get("region_key")
        if isinstance(region_key, str) and region_key:
            region_blocks[region_key] = block
    return region_blocks


def _derive_modal_like_region(
    text_blocks: tuple[SemanticTextBlock, ...],
    *,
    content_region: SemanticLayoutRegion,
    frame_id: str,
) -> SemanticLayoutRegion | None:
    relevant_blocks = tuple(
        block
        for block in text_blocks
        if block.extracted_text
        and _bbox_within(block.bounds, content_region.bounds)
        and _bbox_center_x(block.bounds) >= content_region.bounds.left + (content_region.bounds.width * 0.2)
        and _bbox_center_x(block.bounds)
        <= content_region.bounds.left + (content_region.bounds.width * 0.8)
    )
    if not relevant_blocks:
        return None

    union_bounds = _union_bounds(tuple(block.bounds for block in relevant_blocks))
    padded_bounds = _pad_within_parent(union_bounds, parent=content_region.bounds, padding=0.03)
    return SemanticLayoutRegion(
        region_id=f"{frame_id}:layout:modal-like",
        kind=SemanticLayoutRegionKind.modal_like,
        label="Modal-Like Region",
        bounds=padded_bounds,
        node_id=f"{frame_id}:layout:modal-like",
        parent_region_id=content_region.region_id,
        source_text_region_ids=tuple(block.region_id for block in relevant_blocks),
        confidence=0.7,
        metadata={
            "observe_only": True,
            "analysis_only": True,
            "layout_region_analysis": True,
            "derived_from_ocr": True,
            "derived_text_block_ids": tuple(block.text_block_id for block in relevant_blocks),
        },
    )


def _build_layout_region_group(
    layout_regions: tuple[SemanticLayoutRegion, ...],
) -> SemanticNode:
    group_node_id = f"{layout_regions[0].region_id}:group"
    nodes_by_region_id = {
        region.region_id: _build_layout_region_node(region)
        for region in layout_regions
    }
    regions_by_id = {region.region_id: region for region in layout_regions}
    children_by_parent_id: dict[str | None, list[SemanticNode]] = {}
    for region in layout_regions:
        children_by_parent_id.setdefault(region.parent_region_id, []).append(nodes_by_region_id[region.region_id])

    def _attach_children(region_id: str) -> SemanticNode:
        region = regions_by_id[region_id]
        children = tuple(_attach_children(child.attributes["layout_region_id"]) for child in children_by_parent_id.get(region_id, ()))
        return replace(nodes_by_region_id[region_id], children=children)

    root_region_nodes = tuple(
        _attach_children(region.region_id)
        for region in layout_regions
        if region.parent_region_id is None
    )
    return SemanticNode(
        node_id=group_node_id,
        role="layout_region_group",
        name="Derived Layout Regions",
        enabled=False,
        children=root_region_nodes,
        attributes={"observe_only": True, "analysis_only": True, "layout_region_group": True},
    )


def _build_layout_region_node(region: SemanticLayoutRegion) -> SemanticNode:
    return SemanticNode(
        node_id=region.node_id or f"{region.region_id}:node",
        role=f"layout_region:{region.kind.value}",
        name=region.label,
        bounds=region.bounds,
        visible=region.visible,
        enabled=False,
        attributes={
            **dict(region.metadata),
            "layout_region_id": region.region_id,
            "layout_region_kind": region.kind.value,
            "observe_only": True,
            "analysis_only": True,
        },
    )


def _insert_layout_region_group(
    node: SemanticNode,
    *,
    capture_surface_node_id: str,
    group_node: SemanticNode,
) -> SemanticNode:
    children = tuple(
        _insert_layout_region_group(
            child,
            capture_surface_node_id=capture_surface_node_id,
            group_node=group_node,
        )
        for child in node.children
    )
    if node.node_id != capture_surface_node_id:
        if children == node.children:
            return node
        return replace(node, children=children)
    return replace(node, children=children + (group_node,))


def _bbox_within(inner: NormalizedBBox, outer: NormalizedBBox) -> bool:
    return (
        inner.left >= outer.left
        and inner.top >= outer.top
        and inner.left + inner.width <= outer.left + outer.width
        and inner.top + inner.height <= outer.top + outer.height
    )


def _bbox_center_x(bounds: NormalizedBBox) -> float:
    return bounds.left + (bounds.width / 2.0)


def _union_bounds(bounds: tuple[NormalizedBBox, ...]) -> NormalizedBBox:
    left = min(item.left for item in bounds)
    top = min(item.top for item in bounds)
    right = max(item.left + item.width for item in bounds)
    bottom = max(item.top + item.height for item in bounds)
    return NormalizedBBox(left=left, top=top, width=right - left, height=bottom - top)


def _pad_within_parent(
    bounds: NormalizedBBox,
    *,
    parent: NormalizedBBox,
    padding: float,
) -> NormalizedBBox:
    left = max(parent.left, bounds.left - padding)
    top = max(parent.top, bounds.top - padding)
    right = min(parent.left + parent.width, (bounds.left + bounds.width) + padding)
    bottom = min(parent.top + parent.height, (bounds.top + bounds.height) + padding)
    return NormalizedBBox(left=left, top=top, width=right - left, height=bottom - top)


def _capture_surface_aspect_ratio(capture_surface_node: SemanticNode | None) -> float:
    if capture_surface_node is None:
        return 1.0
    width = capture_surface_node.attributes.get("width")
    height = capture_surface_node.attributes.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        return 1.0
    return width / height
