"""Semantic interpretation pass on top of geometric layout-region analysis."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping, Self

from universal_visual_os_agent.geometry import NormalizedBBox
from universal_visual_os_agent.semantics.layout import SemanticLayoutTree, SemanticNode
from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
    SemanticLayoutRegion,
    SemanticLayoutRegionKind,
    SemanticLayoutRole,
    SemanticStateSnapshot,
    SemanticTextBlock,
    SemanticTextRegion,
    SemanticTextStatus,
)

_NAVIGATION_KEYWORDS = frozenset(
    {
        "account",
        "dashboard",
        "edit",
        "file",
        "help",
        "home",
        "menu",
        "profile",
        "search",
        "settings",
        "tools",
        "view",
    }
)
_STATUS_KEYWORDS = frozenset(
    {
        "connected",
        "error",
        "failed",
        "loading",
        "offline",
        "online",
        "ready",
        "saved",
        "saving",
        "sync",
        "updated",
        "warning",
    }
)


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticLayoutEnrichmentResult:
    """Structured result for semantic interpretation of layout regions."""

    enricher_name: str
    success: bool
    snapshot: SemanticStateSnapshot | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.enricher_name:
            raise ValueError("enricher_name must not be empty.")
        if self.success and self.snapshot is None:
            raise ValueError("Successful enrichment results must include snapshot.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed enrichment results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful enrichment results must not include error details.")
        if not self.success and self.snapshot is not None:
            raise ValueError("Failed enrichment results must not include snapshot.")

    @classmethod
    def ok(
        cls,
        *,
        enricher_name: str,
        snapshot: SemanticStateSnapshot,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            enricher_name=enricher_name,
            success=True,
            snapshot=snapshot,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        enricher_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            enricher_name=enricher_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class _RegionSignalBundle:
    """Internal OCR-derived signal bundle for one layout region."""

    text_region_ids: tuple[str, ...]
    text_block_ids: tuple[str, ...]
    extracted_texts: tuple[str, ...]
    missing_source_text_region_ids: tuple[str, ...]
    malformed_text_block_ids: tuple[str, ...]
    navigation_keyword_hits: tuple[str, ...]
    status_keyword_hits: tuple[str, ...]
    signal_status: str

    @property
    def navigation_like(self) -> bool:
        short_text_count = sum(
            1
            for text in self.extracted_texts
            if text and len(text) <= 24 and len(text.split()) <= 4
        )
        return bool(self.navigation_keyword_hits) or short_text_count >= 2

    @property
    def status_like(self) -> bool:
        return bool(self.status_keyword_hits)


class OcrAwareSemanticLayoutEnricher:
    """Refine geometric layout regions into conservative semantic interpretations."""

    enricher_name = "OcrAwareSemanticLayoutEnricher"

    def enrich(self, snapshot: SemanticStateSnapshot) -> SemanticLayoutEnrichmentResult:
        if snapshot.layout_tree is None:
            return SemanticLayoutEnrichmentResult.failure(
                enricher_name=self.enricher_name,
                error_code="layout_tree_unavailable",
                error_message="Semantic layout enrichment requires a semantic layout tree.",
            )
        if not snapshot.layout_regions:
            return SemanticLayoutEnrichmentResult.failure(
                enricher_name=self.enricher_name,
                error_code="layout_regions_unavailable",
                error_message="Semantic layout enrichment requires geometric layout regions.",
            )

        missing_region_ids = tuple(
            region.region_id
            for region in snapshot.layout_regions
            if region.node_id is None or snapshot.layout_tree.find_node(region.node_id) is None
        )
        if missing_region_ids:
            return SemanticLayoutEnrichmentResult.failure(
                enricher_name=self.enricher_name,
                error_code="layout_region_nodes_unavailable",
                error_message="Semantic layout enrichment requires layout-region nodes in the tree.",
                details={"missing_layout_region_ids": missing_region_ids},
            )

        try:
            signal_bundles = self._collect_region_signals(snapshot)
            enriched_regions = self._build_enriched_regions(snapshot.layout_regions, signal_bundles)
            enriched_tree = self._enrich_layout_tree(
                snapshot.layout_tree,
                layout_regions=enriched_regions,
                capture_surface_node_id=snapshot.metadata.get("capture_surface_node_id"),
            )
            enriched_candidates = self._enrich_candidates(snapshot.candidates, enriched_regions)
            enriched_snapshot = replace(
                snapshot,
                layout_tree=enriched_tree,
                layout_regions=enriched_regions,
                candidates=enriched_candidates,
                metadata={
                    **dict(snapshot.metadata),
                    "semantic_layout_enrichment": True,
                    "semantic_layout_enricher_name": self.enricher_name,
                    "semantic_layout_region_ids": tuple(
                        region.region_id for region in enriched_regions
                    ),
                    "semantic_layout_role_map": tuple(
                        (
                            region.region_id,
                            None if region.semantic_role is None else region.semantic_role.value,
                        )
                        for region in enriched_regions
                    ),
                    "semantic_layout_signal_status": _aggregate_signal_status(signal_bundles),
                    "semantic_layout_candidate_ids": tuple(
                        candidate.candidate_id
                        for candidate in enriched_candidates
                        if candidate.role == "semantic_layout_region"
                    ),
                },
            )
        except Exception as exc:  # noqa: BLE001 - enrichment must remain failure-safe
            return SemanticLayoutEnrichmentResult.failure(
                enricher_name=self.enricher_name,
                error_code="semantic_layout_enrichment_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return SemanticLayoutEnrichmentResult.ok(
            enricher_name=self.enricher_name,
            snapshot=enriched_snapshot,
            details={
                "layout_region_count": len(enriched_regions),
                "semantic_role_count": len(
                    {region.semantic_role for region in enriched_regions if region.semantic_role is not None}
                ),
                "semantic_layout_signal_status": _aggregate_signal_status(signal_bundles),
            },
        )

    def _collect_region_signals(
        self,
        snapshot: SemanticStateSnapshot,
    ) -> Mapping[str, _RegionSignalBundle]:
        text_regions_by_id = {region.region_id: region for region in snapshot.text_regions}
        bundles: dict[str, _RegionSignalBundle] = {}
        for region in snapshot.layout_regions:
            source_region_ids = set(region.source_text_region_ids)
            missing_source_text_region_ids = tuple(
                sorted(region_id for region_id in source_region_ids if region_id not in text_regions_by_id)
            )
            relevant_text_regions = tuple(
                text_region
                for text_region in snapshot.text_regions
                if text_region.status is SemanticTextStatus.extracted
                and text_region.extracted_text
                and (
                    text_region.region_id in source_region_ids
                    or _bbox_overlaps(text_region.bounds, region.bounds)
                )
            )
            relevant_region_ids = tuple(
                _unique_items(
                    tuple(source_region_ids)
                    + tuple(text_region.region_id for text_region in relevant_text_regions)
                )
            )
            relevant_text_blocks: list[SemanticTextBlock] = []
            malformed_text_block_ids: list[str] = []
            for text_block in snapshot.text_blocks:
                if not text_block.extracted_text:
                    continue
                if text_block.region_id not in text_regions_by_id:
                    if _bbox_overlaps(text_block.bounds, region.bounds):
                        malformed_text_block_ids.append(text_block.text_block_id)
                    continue
                if text_block.region_id in relevant_region_ids or _bbox_overlaps(
                    text_block.bounds,
                    region.bounds,
                ):
                    relevant_text_blocks.append(text_block)
            extracted_texts = _unique_items(
                tuple(text_region.extracted_text for text_region in relevant_text_regions if text_region.extracted_text)
                + tuple(text_block.extracted_text for text_block in relevant_text_blocks if text_block.extracted_text)
            )
            navigation_keyword_hits = _keyword_hits(extracted_texts, _NAVIGATION_KEYWORDS)
            status_keyword_hits = _keyword_hits(extracted_texts, _STATUS_KEYWORDS)
            signal_status = _signal_status(
                extracted_texts=extracted_texts,
                missing_source_text_region_ids=missing_source_text_region_ids,
                malformed_text_block_ids=tuple(_unique_items(tuple(malformed_text_block_ids))),
            )
            bundles[region.region_id] = _RegionSignalBundle(
                text_region_ids=tuple(relevant_region_ids),
                text_block_ids=tuple(
                    _unique_items(tuple(text_block.text_block_id for text_block in relevant_text_blocks))
                ),
                extracted_texts=tuple(extracted_texts),
                missing_source_text_region_ids=missing_source_text_region_ids,
                malformed_text_block_ids=tuple(_unique_items(tuple(malformed_text_block_ids))),
                navigation_keyword_hits=navigation_keyword_hits,
                status_keyword_hits=status_keyword_hits,
                signal_status=signal_status,
            )
        return bundles

    def _build_enriched_regions(
        self,
        layout_regions: tuple[SemanticLayoutRegion, ...],
        signal_bundles: Mapping[str, _RegionSignalBundle],
    ) -> tuple[SemanticLayoutRegion, ...]:
        return tuple(
            _enrich_layout_region(
                region,
                signals=signal_bundles[region.region_id],
                enricher_name=self.enricher_name,
            )
            for region in layout_regions
        )

    def _enrich_layout_tree(
        self,
        layout_tree: SemanticLayoutTree,
        *,
        layout_regions: tuple[SemanticLayoutRegion, ...],
        capture_surface_node_id: object,
    ) -> SemanticLayoutTree:
        regions_by_node_id = {
            region.node_id: region
            for region in layout_regions
            if region.node_id is not None
        }
        return replace(
            layout_tree,
            root=_enrich_layout_tree_node(
                layout_tree.root,
                regions_by_node_id=regions_by_node_id,
                capture_surface_node_id=(
                    capture_surface_node_id if isinstance(capture_surface_node_id, str) else None
                ),
                layout_regions=layout_regions,
            ),
        )

    def _enrich_candidates(
        self,
        candidates: tuple[SemanticCandidate, ...],
        layout_regions: tuple[SemanticLayoutRegion, ...],
    ) -> tuple[SemanticCandidate, ...]:
        layout_regions_by_id = {region.region_id: region for region in layout_regions}
        enriched_candidates: list[SemanticCandidate] = []
        for candidate in candidates:
            layout_region_id = candidate.metadata.get("layout_region_id")
            if not isinstance(layout_region_id, str):
                enriched_candidates.append(candidate)
                continue
            region = layout_regions_by_id.get(layout_region_id)
            if region is None:
                enriched_candidates.append(candidate)
                continue
            enriched_candidates.append(
                replace(
                    candidate,
                    label=region.label,
                    node_id=region.node_id or candidate.node_id,
                    role="semantic_layout_region",
                    confidence=region.confidence,
                    enabled=False,
                    metadata={
                        **dict(candidate.metadata),
                        "semantic_layout_enriched": True,
                        "semantic_layout_role": (
                            None if region.semantic_role is None else region.semantic_role.value
                        ),
                        "semantic_layout_label": region.label,
                        "semantic_layout_region_id": region.region_id,
                        "observe_only": True,
                        "analysis_only": True,
                    },
                )
            )
        return tuple(enriched_candidates)


def _enrich_layout_region(
    region: SemanticLayoutRegion,
    *,
    signals: _RegionSignalBundle,
    enricher_name: str,
) -> SemanticLayoutRegion:
    semantic_role = _semantic_role_for(region.kind, signals)
    semantic_label = _semantic_label_for(semantic_role)
    semantic_confidence = _semantic_confidence_for(
        region=region,
        semantic_role=semantic_role,
        signals=signals,
    )
    return replace(
        region,
        semantic_role=semantic_role,
        label=semantic_label,
        confidence=semantic_confidence,
        source_text_region_ids=tuple(
            _unique_items(region.source_text_region_ids + signals.text_region_ids)
        ),
        metadata={
            **dict(region.metadata),
            "semantic_layout_enriched": True,
            "semantic_layout_enricher_name": enricher_name,
            "semantic_layout_role": semantic_role.value,
            "semantic_layout_label": semantic_label,
            "semantic_layout_signal_status": signals.signal_status,
            "semantic_layout_texts": signals.extracted_texts,
            "semantic_layout_text_region_ids": signals.text_region_ids,
            "semantic_layout_text_block_ids": signals.text_block_ids,
            "semantic_layout_navigation_keyword_hits": signals.navigation_keyword_hits,
            "semantic_layout_status_keyword_hits": signals.status_keyword_hits,
            "semantic_layout_missing_source_text_region_ids": signals.missing_source_text_region_ids,
            "semantic_layout_malformed_text_block_ids": signals.malformed_text_block_ids,
            "observe_only": True,
            "analysis_only": True,
        },
    )


def _semantic_role_for(
    region_kind: SemanticLayoutRegionKind,
    signals: _RegionSignalBundle,
) -> SemanticLayoutRole:
    if region_kind is SemanticLayoutRegionKind.full_surface:
        return SemanticLayoutRole.application_surface
    if region_kind is SemanticLayoutRegionKind.header:
        if signals.navigation_like:
            return SemanticLayoutRole.navigation_header
        return SemanticLayoutRole.header_bar
    if region_kind is SemanticLayoutRegionKind.content:
        return SemanticLayoutRole.primary_content
    if region_kind is SemanticLayoutRegionKind.footer:
        if signals.status_like:
            return SemanticLayoutRole.status_footer
        return SemanticLayoutRole.footer_bar
    if region_kind in {
        SemanticLayoutRegionKind.left_sidebar,
        SemanticLayoutRegionKind.right_sidebar,
    }:
        if signals.navigation_like:
            return SemanticLayoutRole.navigation_sidebar
        return SemanticLayoutRole.sidebar_panel
    return SemanticLayoutRole.dialog_overlay


def _semantic_label_for(semantic_role: SemanticLayoutRole) -> str:
    return {
        SemanticLayoutRole.application_surface: "Application Surface",
        SemanticLayoutRole.header_bar: "Header Bar",
        SemanticLayoutRole.navigation_header: "Navigation Header",
        SemanticLayoutRole.primary_content: "Primary Content Area",
        SemanticLayoutRole.footer_bar: "Footer Bar",
        SemanticLayoutRole.status_footer: "Status Footer",
        SemanticLayoutRole.sidebar_panel: "Sidebar Panel",
        SemanticLayoutRole.navigation_sidebar: "Navigation Sidebar",
        SemanticLayoutRole.dialog_overlay: "Dialog Overlay",
    }[semantic_role]


def _semantic_confidence_for(
    *,
    region: SemanticLayoutRegion,
    semantic_role: SemanticLayoutRole,
    signals: _RegionSignalBundle,
) -> float | None:
    baseline = {
        SemanticLayoutRole.application_surface: 1.0,
        SemanticLayoutRole.header_bar: 0.72,
        SemanticLayoutRole.navigation_header: 0.84,
        SemanticLayoutRole.primary_content: 0.95,
        SemanticLayoutRole.footer_bar: 0.7,
        SemanticLayoutRole.status_footer: 0.83,
        SemanticLayoutRole.sidebar_panel: 0.68,
        SemanticLayoutRole.navigation_sidebar: 0.82,
        SemanticLayoutRole.dialog_overlay: 0.8,
    }[semantic_role]
    if signals.signal_status == "partial":
        baseline = max(0.0, baseline - 0.1)
    if region.confidence is None:
        return baseline
    return max(region.confidence, baseline)


def _enrich_layout_tree_node(
    node: SemanticNode,
    *,
    regions_by_node_id: Mapping[str, SemanticLayoutRegion],
    capture_surface_node_id: str | None,
    layout_regions: tuple[SemanticLayoutRegion, ...],
) -> SemanticNode:
    child_nodes = tuple(
        _enrich_layout_tree_node(
            child,
            regions_by_node_id=regions_by_node_id,
            capture_surface_node_id=capture_surface_node_id,
            layout_regions=layout_regions,
        )
        for child in node.children
    )
    attributes = dict(node.attributes)
    if node.node_id in regions_by_node_id:
        region = regions_by_node_id[node.node_id]
        attributes.update(
            {
                **dict(region.metadata),
                "semantic_layout_region_id": region.region_id,
                "semantic_layout_role": (
                    None if region.semantic_role is None else region.semantic_role.value
                ),
                "semantic_layout_label": region.label,
                "observe_only": True,
                "analysis_only": True,
            }
        )
        return replace(
            node,
            role=f"semantic_layout_region:{region.semantic_role.value}",
            name=region.label,
            enabled=False,
            children=child_nodes,
            attributes=attributes,
        )
    if capture_surface_node_id is not None and node.node_id == capture_surface_node_id:
        attributes.update(
            {
                "semantic_layout_enrichment": True,
                "semantic_layout_region_ids": tuple(
                    region.region_id for region in layout_regions
                ),
                "semantic_layout_roles": tuple(
                    region.semantic_role.value
                    for region in layout_regions
                    if region.semantic_role is not None
                ),
                "observe_only": True,
                "analysis_only": True,
            }
        )
        return replace(node, enabled=False, children=child_nodes, attributes=attributes)
    if node.role == "layout_region_group":
        attributes.update(
            {
                "semantic_layout_enrichment": True,
                "observe_only": True,
                "analysis_only": True,
            }
        )
        return replace(
            node,
            name="Semantic Layout Regions",
            enabled=False,
            children=child_nodes,
            attributes=attributes,
        )
    if child_nodes == node.children:
        return node
    return replace(node, children=child_nodes)


def _aggregate_signal_status(signal_bundles: Mapping[str, _RegionSignalBundle]) -> str:
    statuses = {signals.signal_status for signals in signal_bundles.values()}
    if "partial" in statuses:
        return "partial"
    if "available" in statuses:
        return "available"
    return "absent"


def _signal_status(
    *,
    extracted_texts: tuple[str, ...],
    missing_source_text_region_ids: tuple[str, ...],
    malformed_text_block_ids: tuple[str, ...],
) -> str:
    if missing_source_text_region_ids or malformed_text_block_ids:
        return "partial"
    if extracted_texts:
        return "available"
    return "absent"


def _keyword_hits(
    texts: tuple[str, ...],
    keywords: frozenset[str],
) -> tuple[str, ...]:
    matched_keywords: list[str] = []
    for text in texts:
        for token in _normalize_text_tokens(text):
            if token in keywords and token not in matched_keywords:
                matched_keywords.append(token)
    return tuple(matched_keywords)


def _normalize_text_tokens(text: str) -> tuple[str, ...]:
    return tuple(
        token.strip(" ,.:;!?/\\|-_()[]{}\"'")
        for token in text.lower().split()
        if token.strip(" ,.:;!?/\\|-_()[]{}\"'")
    )


def _bbox_overlaps(first: NormalizedBBox, second: NormalizedBBox) -> bool:
    first_right = first.left + first.width
    first_bottom = first.top + first.height
    second_right = second.left + second.width
    second_bottom = second.top + second.height
    return not (
        first_right <= second.left
        or second_right <= first.left
        or first_bottom <= second.top
        or second_bottom <= first.top
    )


def _unique_items(items: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for item in items if item))
