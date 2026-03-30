"""Pure OCR-driven semantic enrichment helpers."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Mapping

from universal_visual_os_agent.semantics.layout import SemanticLayoutTree, SemanticNode
from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
    SemanticStateSnapshot,
    SemanticTextBlock,
    SemanticTextRegion,
    SemanticTextStatus,
)


def apply_ocr_semantic_enrichment(
    snapshot: SemanticStateSnapshot,
    *,
    text_regions: tuple[SemanticTextRegion, ...],
    text_blocks: tuple[SemanticTextBlock, ...],
    adapter_name: str,
    backend_name: str | None,
    response_status: str,
) -> SemanticStateSnapshot:
    """Return a snapshot enriched with OCR-aware layout, metadata, and candidates."""

    blocks_by_region_id = _group_text_blocks(text_blocks)
    enriched_layout_tree = _enrich_layout_tree(
        snapshot.layout_tree,
        text_regions=text_regions,
        blocks_by_region_id=blocks_by_region_id,
        backend_name=backend_name,
    )
    base_candidates = _enrich_existing_candidates(
        snapshot.candidates,
        text_regions=text_regions,
        blocks_by_region_id=blocks_by_region_id,
        backend_name=backend_name,
    )
    ocr_candidates = _build_ocr_candidates(
        text_regions=text_regions,
        text_blocks=text_blocks,
        backend_name=backend_name,
    )
    return replace(
        snapshot,
        layout_tree=enriched_layout_tree,
        text_regions=text_regions,
        text_blocks=text_blocks,
        candidates=base_candidates + ocr_candidates,
        metadata={
            **dict(snapshot.metadata),
            "text_extraction_adapter_name": adapter_name,
            "text_extraction_scaffold": True,
            "text_extraction_backend_name": backend_name,
            "text_extraction_response_status": response_status,
            "text_region_ids": tuple(region.region_id for region in text_regions),
            "text_block_ids": tuple(block.text_block_id for block in text_blocks),
            "ocr_enrichment": True,
            "ocr_candidate_ids": tuple(candidate.candidate_id for candidate in ocr_candidates),
            "ocr_extracted_region_ids": tuple(
                region.region_id
                for region in text_regions
                if region.status is SemanticTextStatus.extracted and region.extracted_text
            ),
            "ocr_unavailable_region_ids": tuple(
                region.region_id
                for region in text_regions
                if region.status is SemanticTextStatus.unavailable
            ),
            "ocr_enriched_layout_tree": enriched_layout_tree is not None,
        },
    )


def _group_text_blocks(
    text_blocks: tuple[SemanticTextBlock, ...],
) -> Mapping[str, tuple[SemanticTextBlock, ...]]:
    grouped: defaultdict[str, list[SemanticTextBlock]] = defaultdict(list)
    for block in text_blocks:
        grouped[block.region_id].append(block)
    return {region_id: tuple(blocks) for region_id, blocks in grouped.items()}


def _enrich_layout_tree(
    layout_tree: SemanticLayoutTree | None,
    *,
    text_regions: tuple[SemanticTextRegion, ...],
    blocks_by_region_id: Mapping[str, tuple[SemanticTextBlock, ...]],
    backend_name: str | None,
) -> SemanticLayoutTree | None:
    if layout_tree is None:
        return None
    regions_by_anchor_id = {
        anchor_id: region
        for region in text_regions
        if (anchor_id := region.node_id or region.block_id) is not None
    }
    return replace(
        layout_tree,
        root=_enrich_node(
            layout_tree.root,
            regions_by_anchor_id=regions_by_anchor_id,
            blocks_by_region_id=blocks_by_region_id,
            backend_name=backend_name,
        ),
    )


def _enrich_node(
    node: SemanticNode,
    *,
    regions_by_anchor_id: Mapping[str, SemanticTextRegion],
    blocks_by_region_id: Mapping[str, tuple[SemanticTextBlock, ...]],
    backend_name: str | None,
) -> SemanticNode:
    child_nodes = tuple(
        _enrich_node(
            child,
            regions_by_anchor_id=regions_by_anchor_id,
            blocks_by_region_id=blocks_by_region_id,
            backend_name=backend_name,
        )
        for child in node.children
    )
    attributes = dict(node.attributes)
    region = regions_by_anchor_id.get(node.node_id)
    if region is None:
        if child_nodes == node.children:
            return node
        return replace(node, children=child_nodes)

    region_blocks = blocks_by_region_id.get(region.region_id, ())
    attributes.update(
        {
            "ocr_enriched": True,
            "ocr_text_region_id": region.region_id,
            "ocr_text_status": region.status.value,
            "ocr_text": region.extracted_text,
            "ocr_text_block_ids": tuple(block.text_block_id for block in region_blocks),
            "ocr_backend_name": backend_name,
            "observe_only": True,
            "analysis_only": True,
        }
    )
    if region.status is SemanticTextStatus.extracted and region.extracted_text:
        child_nodes = child_nodes + (_build_text_region_node(region, region_blocks, backend_name=backend_name),)
    return replace(node, children=child_nodes, attributes=attributes)


def _build_text_region_node(
    region: SemanticTextRegion,
    text_blocks: tuple[SemanticTextBlock, ...],
    *,
    backend_name: str | None,
) -> SemanticNode:
    return SemanticNode(
        node_id=f"{region.region_id}:node",
        role="ocr_text_region",
        name=region.extracted_text or region.label,
        bounds=region.bounds,
        visible=region.visible,
        enabled=False,
        children=tuple(
            _build_text_block_node(block, backend_name=backend_name) for block in text_blocks if block.extracted_text
        ),
        attributes={
            **dict(region.metadata),
            "ocr_enriched": True,
            "ocr_region_id": region.region_id,
            "ocr_text": region.extracted_text,
            "ocr_backend_name": backend_name,
            "observe_only": True,
            "analysis_only": True,
        },
    )


def _build_text_block_node(
    block: SemanticTextBlock,
    *,
    backend_name: str | None,
) -> SemanticNode:
    return SemanticNode(
        node_id=f"{block.text_block_id}:node",
        role="ocr_text_block",
        name=block.extracted_text or block.label,
        bounds=block.bounds,
        visible=block.visible,
        enabled=False,
        attributes={
            **dict(block.metadata),
            "ocr_enriched": True,
            "ocr_text_block_id": block.text_block_id,
            "ocr_text": block.extracted_text,
            "ocr_backend_name": backend_name,
            "observe_only": True,
            "analysis_only": True,
        },
    )


def _enrich_existing_candidates(
    candidates: tuple[SemanticCandidate, ...],
    *,
    text_regions: tuple[SemanticTextRegion, ...],
    blocks_by_region_id: Mapping[str, tuple[SemanticTextBlock, ...]],
    backend_name: str | None,
) -> tuple[SemanticCandidate, ...]:
    regions_by_block_id = {
        region.block_id: region
        for region in text_regions
        if region.block_id is not None
    }
    regions_by_node_id = {
        region.node_id: region
        for region in text_regions
        if region.node_id is not None
    }
    enriched_candidates: list[SemanticCandidate] = []
    for candidate in candidates:
        linked_region = None
        block_id = candidate.metadata.get("region_block_id")
        if isinstance(block_id, str):
            linked_region = regions_by_block_id.get(block_id)
        if linked_region is None and candidate.node_id is not None:
            linked_region = regions_by_node_id.get(candidate.node_id)
        if linked_region is None:
            enriched_candidates.append(candidate)
            continue
        region_blocks = blocks_by_region_id.get(linked_region.region_id, ())
        enriched_candidates.append(
            replace(
                candidate,
                enabled=False,
                metadata={
                    **dict(candidate.metadata),
                    "ocr_enriched": True,
                    "ocr_text_region_id": linked_region.region_id,
                    "ocr_text_status": linked_region.status.value,
                    "ocr_text": linked_region.extracted_text,
                    "ocr_text_block_ids": tuple(block.text_block_id for block in region_blocks),
                    "ocr_backend_name": backend_name,
                    "observe_only": True,
                    "analysis_only": True,
                },
            )
        )
    return tuple(enriched_candidates)


def _build_ocr_candidates(
    *,
    text_regions: tuple[SemanticTextRegion, ...],
    text_blocks: tuple[SemanticTextBlock, ...],
    backend_name: str | None,
) -> tuple[SemanticCandidate, ...]:
    candidates: list[SemanticCandidate] = []
    for region in text_regions:
        if region.status is not SemanticTextStatus.extracted or not region.extracted_text:
            continue
        candidates.append(
            SemanticCandidate(
                candidate_id=f"{region.region_id}:candidate",
                label=region.extracted_text,
                bounds=region.bounds,
                node_id=f"{region.region_id}:node",
                role="ocr_text_region",
                confidence=region.confidence,
                visible=region.visible,
                enabled=False,
                metadata={
                    **dict(region.metadata),
                    "ocr_enriched": True,
                    "ocr_text_region_id": region.region_id,
                    "ocr_text": region.extracted_text,
                    "ocr_backend_name": backend_name,
                    "observe_only": True,
                    "analysis_only": True,
                    "semantic_origin": "ocr_enrichment",
                },
            )
        )
    for block in text_blocks:
        if not block.extracted_text:
            continue
        candidates.append(
            SemanticCandidate(
                candidate_id=f"{block.text_block_id}:candidate",
                label=block.extracted_text,
                bounds=block.bounds,
                node_id=f"{block.text_block_id}:node",
                role="ocr_text_block",
                confidence=block.confidence,
                visible=block.visible,
                enabled=False,
                metadata={
                    **dict(block.metadata),
                    "ocr_enriched": True,
                    "ocr_text_block_id": block.text_block_id,
                    "ocr_text": block.extracted_text,
                    "ocr_backend_name": backend_name,
                    "observe_only": True,
                    "analysis_only": True,
                    "semantic_origin": "ocr_enrichment",
                },
            )
        )
    return tuple(candidates)
