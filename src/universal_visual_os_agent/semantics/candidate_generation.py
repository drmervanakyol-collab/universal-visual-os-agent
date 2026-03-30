"""Observe-only heuristic candidate generation on top of semantic enrichment."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Mapping, Self

from universal_visual_os_agent.geometry import NormalizedBBox
from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
    SemanticCandidateClass,
    SemanticLayoutRole,
    SemanticLayoutRegion,
    SemanticStateSnapshot,
    SemanticTextBlock,
)

_NAVIGATION_ROLES = frozenset(
    {
        SemanticLayoutRole.navigation_header,
        SemanticLayoutRole.navigation_sidebar,
    }
)
_INTERACTIVE_REGION_ROLES = frozenset(
    {
        SemanticLayoutRole.navigation_header,
        SemanticLayoutRole.navigation_sidebar,
        SemanticLayoutRole.sidebar_panel,
        SemanticLayoutRole.header_bar,
        SemanticLayoutRole.footer_bar,
        SemanticLayoutRole.status_footer,
        SemanticLayoutRole.dialog_overlay,
    }
)
_DIALOG_ROLES = frozenset({SemanticLayoutRole.dialog_overlay})
_BUTTON_HINTS = frozenset(
    {
        "accept",
        "add",
        "apply",
        "confirm",
        "continue",
        "create",
        "delete",
        "done",
        "install",
        "launch",
        "next",
        "ok",
        "okay",
        "open",
        "remove",
        "retry",
        "save",
        "submit",
        "update",
    }
)
_INPUT_HINTS = frozenset(
    {
        "email",
        "filter",
        "find",
        "password",
        "search",
        "search projects",
        "type",
        "type here",
        "username",
    }
)
_CLOSE_HINTS = frozenset({"close", "exit", "quit", "x"})
_POPUP_DISMISS_HINTS = frozenset(
    {
        "cancel",
        "dismiss",
        "got it",
        "later",
        "maybe later",
        "no thanks",
        "not now",
        "skip",
    }
)
_TOKEN_SPLIT_PATTERN = re.compile(r"[\s,.:;!?/\\|()\[\]{}\"']+")


@dataclass(slots=True, frozen=True, kw_only=True)
class CandidateGenerationResult:
    """Structured result for observe-only heuristic candidate generation."""

    generator_name: str
    success: bool
    snapshot: SemanticStateSnapshot | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.generator_name:
            raise ValueError("generator_name must not be empty.")
        if self.success and self.snapshot is None:
            raise ValueError("Successful candidate generation must include snapshot.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed candidate generation must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful candidate generation must not include error details.")
        if not self.success and self.snapshot is not None:
            raise ValueError("Failed candidate generation must not include snapshot.")

    @classmethod
    def ok(
        cls,
        *,
        generator_name: str,
        snapshot: SemanticStateSnapshot,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            generator_name=generator_name,
            success=True,
            snapshot=snapshot,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        generator_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            generator_name=generator_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class _GenerationArtifacts:
    generated_candidates: tuple[SemanticCandidate, ...]
    missing_semantic_role_region_ids: tuple[str, ...] = ()
    unmatched_text_block_ids: tuple[str, ...] = ()
    ignored_text_block_ids: tuple[str, ...] = ()

    @property
    def signal_status(self) -> str:
        if (
            self.missing_semantic_role_region_ids
            or self.unmatched_text_block_ids
            or self.ignored_text_block_ids
        ):
            return "partial"
        if self.generated_candidates:
            return "available"
        return "absent"


class ObserveOnlyCandidateGenerator:
    """Derive richer, strictly non-actionable candidates from semantic metadata."""

    generator_name = "ObserveOnlyCandidateGenerator"

    def generate(self, snapshot: SemanticStateSnapshot) -> CandidateGenerationResult:
        if snapshot.layout_tree is None:
            return CandidateGenerationResult.failure(
                generator_name=self.generator_name,
                error_code="layout_tree_unavailable",
                error_message="Candidate generation requires a semantic layout tree.",
            )
        if not snapshot.layout_regions:
            return CandidateGenerationResult.failure(
                generator_name=self.generator_name,
                error_code="layout_regions_unavailable",
                error_message="Candidate generation requires semantic layout regions.",
            )
        if snapshot.metadata.get("semantic_layout_enrichment") is not True:
            return CandidateGenerationResult.failure(
                generator_name=self.generator_name,
                error_code="semantic_layout_enrichment_unavailable",
                error_message="Candidate generation requires semantic layout enrichment output.",
            )

        try:
            base_candidates = tuple(
                candidate
                for candidate in snapshot.candidates
                if candidate.metadata.get("semantic_origin") != "candidate_generation"
            )
            artifacts = self._build_generated_candidates(
                snapshot,
                existing_candidate_ids={candidate.candidate_id for candidate in base_candidates},
            )
            all_candidates = base_candidates + artifacts.generated_candidates
            class_counts = Counter(
                candidate.candidate_class.value
                for candidate in artifacts.generated_candidates
                if candidate.candidate_class is not None
            )
            generated_snapshot = replace(
                snapshot,
                candidates=all_candidates,
                metadata={
                    **dict(snapshot.metadata),
                    "candidate_generation": True,
                    "candidate_generator_name": self.generator_name,
                    "generated_candidate_ids": tuple(
                        candidate.candidate_id for candidate in artifacts.generated_candidates
                    ),
                    "generated_candidate_class_counts": tuple(sorted(class_counts.items())),
                    "candidate_generation_signal_status": artifacts.signal_status,
                    "candidate_generation_missing_semantic_role_region_ids": (
                        artifacts.missing_semantic_role_region_ids
                    ),
                    "candidate_generation_unmatched_text_block_ids": (
                        artifacts.unmatched_text_block_ids
                    ),
                    "candidate_generation_ignored_text_block_ids": artifacts.ignored_text_block_ids,
                    "candidate_ids": tuple(candidate.candidate_id for candidate in all_candidates),
                },
            )
        except Exception as exc:  # noqa: BLE001 - generator must remain failure-safe
            return CandidateGenerationResult.failure(
                generator_name=self.generator_name,
                error_code="candidate_generation_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return CandidateGenerationResult.ok(
            generator_name=self.generator_name,
            snapshot=generated_snapshot,
            details={
                "generated_candidate_count": len(artifacts.generated_candidates),
                "signal_status": artifacts.signal_status,
                "class_counts": tuple(sorted(class_counts.items())),
            },
        )

    def _build_generated_candidates(
        self,
        snapshot: SemanticStateSnapshot,
        *,
        existing_candidate_ids: set[str],
    ) -> _GenerationArtifacts:
        generated_candidates: list[SemanticCandidate] = []
        missing_semantic_role_region_ids: list[str] = []
        unmatched_text_block_ids: list[str] = []
        ignored_text_block_ids: list[str] = []

        for region in snapshot.layout_regions:
            if region.semantic_role is None:
                missing_semantic_role_region_ids.append(region.region_id)
            candidate = self._build_interactive_region_candidate(region, existing_candidate_ids)
            if candidate is None:
                continue
            generated_candidates.append(candidate)
            existing_candidate_ids.add(candidate.candidate_id)

        for block in snapshot.text_blocks:
            if not block.extracted_text or not block.extracted_text.strip():
                ignored_text_block_ids.append(block.text_block_id)
                continue
            region = _best_region_for_bounds(snapshot.layout_regions, block.bounds)
            if region is None:
                unmatched_text_block_ids.append(block.text_block_id)
                continue
            block_candidates = self._build_text_block_candidates(
                block,
                region=region,
                existing_candidate_ids=existing_candidate_ids,
            )
            if not block_candidates:
                ignored_text_block_ids.append(block.text_block_id)
                continue
            generated_candidates.extend(block_candidates)
            existing_candidate_ids.update(candidate.candidate_id for candidate in block_candidates)

        return _GenerationArtifacts(
            generated_candidates=tuple(generated_candidates),
            missing_semantic_role_region_ids=tuple(sorted(set(missing_semantic_role_region_ids))),
            unmatched_text_block_ids=tuple(sorted(set(unmatched_text_block_ids))),
            ignored_text_block_ids=tuple(sorted(set(ignored_text_block_ids))),
        )

    def _build_interactive_region_candidate(
        self,
        region: SemanticLayoutRegion,
        existing_candidate_ids: set[str],
    ) -> SemanticCandidate | None:
        if region.semantic_role not in _INTERACTIVE_REGION_ROLES:
            return None
        explanations = [
            f"semantic layout role {region.semantic_role.value} indicates a likely interactive container",
            "layout-derived candidate remains observe-only and non-actionable in Phase 3A",
        ]
        candidate_id = _unique_candidate_id(
            f"{region.region_id}:generated:{SemanticCandidateClass.interactive_region_like.value}",
            existing_candidate_ids,
        )
        return SemanticCandidate(
            candidate_id=candidate_id,
            label=f"{region.label} Interactive Region",
            bounds=region.bounds,
            node_id=region.node_id,
            role=SemanticCandidateClass.interactive_region_like.value,
            candidate_class=SemanticCandidateClass.interactive_region_like,
            confidence=_confidence_for(
                candidate_class=SemanticCandidateClass.interactive_region_like,
                source_confidences=(region.confidence,),
                signal_status=_signal_status_for_region(region),
            ),
            visible=region.visible,
            enabled=False,
            heuristic_explanations=tuple(explanations),
            metadata={
                **dict(region.metadata),
                "semantic_origin": "candidate_generation",
                "candidate_generator_name": self.generator_name,
                "candidate_class": SemanticCandidateClass.interactive_region_like.value,
                "source_layout_region_id": region.region_id,
                "source_text_region_id": None,
                "source_text_block_id": None,
                "semantic_layout_role": (
                    None if region.semantic_role is None else region.semantic_role.value
                ),
                "observe_only": True,
                "analysis_only": True,
                "non_actionable_candidate": True,
                "non_actionable_reason": (
                    "Phase 3A generated candidates are hypotheses only and never actionable."
                ),
                "heuristic_explanations": tuple(explanations),
            },
        )

    def _build_text_block_candidates(
        self,
        block: SemanticTextBlock,
        *,
        region: SemanticLayoutRegion,
        existing_candidate_ids: set[str],
    ) -> tuple[SemanticCandidate, ...]:
        normalized_text = _normalize_phrase(block.extracted_text)
        if not normalized_text:
            return ()

        tokens = _tokenize_for_candidates(block.extracted_text)
        if (
            region.semantic_role in _NAVIGATION_ROLES
            and len(tokens) >= 2
            and all(len(token) <= 18 for token in tokens)
        ):
            return self._build_navigation_tab_candidates(
                block,
                region=region,
                tokens=tokens,
                existing_candidate_ids=existing_candidate_ids,
            )

        candidate_class = _classify_text_block(block, region=region, normalized_text=normalized_text)
        if candidate_class is None:
            return ()

        explanations = _heuristic_explanations_for_block(
            block,
            region=region,
            candidate_class=candidate_class,
            normalized_text=normalized_text,
        )
        candidate_id = _unique_candidate_id(
            f"{block.text_block_id}:generated:{candidate_class.value}",
            existing_candidate_ids,
        )
        return (
            SemanticCandidate(
                candidate_id=candidate_id,
                label=block.extracted_text or block.label,
                bounds=block.bounds,
                node_id=f"{block.text_block_id}:node",
                role=candidate_class.value,
                candidate_class=candidate_class,
                confidence=_confidence_for(
                    candidate_class=candidate_class,
                    source_confidences=(block.confidence, region.confidence),
                    signal_status=_signal_status_for_region(region),
                ),
                visible=block.visible,
                enabled=False,
                heuristic_explanations=tuple(explanations),
                metadata={
                    **dict(block.metadata),
                    "semantic_origin": "candidate_generation",
                    "candidate_generator_name": self.generator_name,
                    "candidate_class": candidate_class.value,
                    "source_layout_region_id": region.region_id,
                    "source_text_region_id": block.region_id,
                    "source_text_block_id": block.text_block_id,
                    "semantic_layout_role": (
                        None if region.semantic_role is None else region.semantic_role.value
                    ),
                    "observe_only": True,
                    "analysis_only": True,
                    "non_actionable_candidate": True,
                    "non_actionable_reason": (
                        "Phase 3A generated candidates are hypotheses only and never actionable."
                    ),
                    "heuristic_explanations": tuple(explanations),
                },
            ),
        )

    def _build_navigation_tab_candidates(
        self,
        block: SemanticTextBlock,
        *,
        region: SemanticLayoutRegion,
        tokens: tuple[str, ...],
        existing_candidate_ids: set[str],
    ) -> tuple[SemanticCandidate, ...]:
        token_bounds = _segment_bounds(block.bounds, len(tokens))
        candidates: list[SemanticCandidate] = []
        for index, (token, bounds) in enumerate(zip(tokens, token_bounds, strict=True), start=1):
            explanations = (
                f"text block token {index} came from multi-token navigation text",
                f"semantic layout role {region.semantic_role.value if region.semantic_role else 'unknown'} "
                "suggests tab-like navigation",
            )
            candidate_class = SemanticCandidateClass.tab_like
            candidate = SemanticCandidate(
                candidate_id=_unique_candidate_id(
                    f"{block.text_block_id}:generated:{candidate_class.value}:{index}",
                    existing_candidate_ids,
                ),
                label=token,
                bounds=bounds,
                node_id=f"{block.text_block_id}:node",
                role=candidate_class.value,
                candidate_class=candidate_class,
                confidence=_confidence_for(
                    candidate_class=candidate_class,
                    source_confidences=(block.confidence, region.confidence),
                    signal_status=_signal_status_for_region(region),
                ),
                visible=block.visible,
                enabled=False,
                heuristic_explanations=explanations,
                metadata={
                    **dict(block.metadata),
                    "semantic_origin": "candidate_generation",
                    "candidate_generator_name": self.generator_name,
                    "candidate_class": candidate_class.value,
                    "source_layout_region_id": region.region_id,
                    "source_text_region_id": block.region_id,
                    "source_text_block_id": block.text_block_id,
                    "semantic_layout_role": (
                        None if region.semantic_role is None else region.semantic_role.value
                    ),
                    "candidate_token_index": index,
                    "candidate_token_count": len(tokens),
                    "observe_only": True,
                    "analysis_only": True,
                    "non_actionable_candidate": True,
                    "non_actionable_reason": (
                        "Phase 3A generated candidates are hypotheses only and never actionable."
                    ),
                    "heuristic_explanations": explanations,
                },
            )
            candidates.append(candidate)
        return tuple(candidates)


def _classify_text_block(
    block: SemanticTextBlock,
    *,
    region: SemanticLayoutRegion,
    normalized_text: str,
) -> SemanticCandidateClass | None:
    if region.semantic_role in _DIALOG_ROLES and normalized_text in _POPUP_DISMISS_HINTS:
        return SemanticCandidateClass.popup_dismiss_like
    if _is_close_like(block, region=region, normalized_text=normalized_text):
        return SemanticCandidateClass.close_like
    if _matches_phrase(normalized_text, _INPUT_HINTS) or normalized_text.endswith(":"):
        return SemanticCandidateClass.input_like
    if _matches_phrase(normalized_text, _BUTTON_HINTS) or (
        region.semantic_role in _DIALOG_ROLES and len(_tokenize_for_candidates(block.extracted_text)) <= 3
    ):
        return SemanticCandidateClass.button_like
    if region.semantic_role in _INTERACTIVE_REGION_ROLES:
        return SemanticCandidateClass.interactive_region_like
    return None


def _heuristic_explanations_for_block(
    block: SemanticTextBlock,
    *,
    region: SemanticLayoutRegion,
    candidate_class: SemanticCandidateClass,
    normalized_text: str,
) -> tuple[str, ...]:
    explanations = [
        f"text block '{block.extracted_text}' matched heuristic class {candidate_class.value}",
        (
            f"block overlaps semantic layout role {region.semantic_role.value}"
            if region.semantic_role is not None
            else "block overlaps a semantic layout region with incomplete role metadata"
        ),
    ]
    if candidate_class is SemanticCandidateClass.close_like:
        explanations.append("text or position resembles a close affordance")
    elif candidate_class is SemanticCandidateClass.popup_dismiss_like:
        explanations.append("dialog text resembles a popup dismissal affordance")
    elif candidate_class is SemanticCandidateClass.input_like:
        explanations.append("text resembles a search or form-entry affordance")
    elif candidate_class is SemanticCandidateClass.button_like:
        explanations.append("text resembles a short action label or dialog button")
    elif candidate_class is SemanticCandidateClass.interactive_region_like:
        explanations.append("region context is interactive but text is not specific enough for a stronger class")
    if normalized_text.endswith(":"):
        explanations.append("trailing colon suggests label-input pairing")
    return tuple(explanations)


def _is_close_like(
    block: SemanticTextBlock,
    *,
    region: SemanticLayoutRegion,
    normalized_text: str,
) -> bool:
    if normalized_text in _CLOSE_HINTS:
        return True
    if region.semantic_role not in _DIALOG_ROLES:
        return False
    center_x = block.bounds.left + (block.bounds.width / 2.0)
    center_y = block.bounds.top + (block.bounds.height / 2.0)
    region_right = region.bounds.left + region.bounds.width
    region_top_limit = region.bounds.top + (region.bounds.height * 0.35)
    return center_x >= region_right - (region.bounds.width * 0.18) and center_y <= region_top_limit


def _best_region_for_bounds(
    layout_regions: tuple[SemanticLayoutRegion, ...],
    bounds: NormalizedBBox,
) -> SemanticLayoutRegion | None:
    contained_regions = tuple(
        region
        for region in layout_regions
        if _bbox_contains(region.bounds, bounds)
    )
    if contained_regions:
        return min(contained_regions, key=lambda region: region.bounds.width * region.bounds.height)

    overlapping_regions = tuple(
        region
        for region in layout_regions
        if _bbox_overlaps(region.bounds, bounds)
    )
    if not overlapping_regions:
        return None
    return max(
        overlapping_regions,
        key=lambda region: (
            _overlap_area(region.bounds, bounds),
            -(region.bounds.width * region.bounds.height),
        ),
    )


def _normalize_phrase(text: str | None) -> str:
    if text is None:
        return ""
    tokens = _tokenize_for_candidates(text)
    return " ".join(tokens)


def _tokenize_for_candidates(text: str | None) -> tuple[str, ...]:
    if text is None:
        return ()
    return tuple(
        token
        for token in _TOKEN_SPLIT_PATTERN.split(text.lower())
        if token
    )


def _matches_phrase(text: str, phrases: frozenset[str]) -> bool:
    if text in phrases:
        return True
    return any(phrase in text for phrase in phrases)


def _segment_bounds(
    bounds: NormalizedBBox,
    segment_count: int,
) -> tuple[NormalizedBBox, ...]:
    if segment_count <= 1:
        return (bounds,)

    segments: list[NormalizedBBox] = []
    horizontal = bounds.width >= bounds.height
    for index in range(segment_count):
        if horizontal:
            segment_width = bounds.width / segment_count
            left = bounds.left + (segment_width * index)
            segments.append(
                NormalizedBBox(
                    left=left,
                    top=bounds.top,
                    width=segment_width,
                    height=bounds.height,
                )
            )
            continue
        segment_height = bounds.height / segment_count
        top = bounds.top + (segment_height * index)
        segments.append(
            NormalizedBBox(
                left=bounds.left,
                top=top,
                width=bounds.width,
                height=segment_height,
            )
        )
    return tuple(segments)


def _unique_candidate_id(base_candidate_id: str, existing_candidate_ids: set[str]) -> str:
    if base_candidate_id not in existing_candidate_ids:
        return base_candidate_id
    suffix = 2
    candidate_id = f"{base_candidate_id}:{suffix}"
    while candidate_id in existing_candidate_ids:
        suffix += 1
        candidate_id = f"{base_candidate_id}:{suffix}"
    return candidate_id


def _signal_status_for_region(region: SemanticLayoutRegion) -> str:
    signal_status = region.metadata.get("semantic_layout_signal_status")
    if isinstance(signal_status, str) and signal_status:
        return signal_status
    return "partial" if region.semantic_role is None else "available"


def _confidence_for(
    *,
    candidate_class: SemanticCandidateClass,
    source_confidences: tuple[float | None, ...],
    signal_status: str,
) -> float:
    baseline = {
        SemanticCandidateClass.button_like: 0.78,
        SemanticCandidateClass.input_like: 0.74,
        SemanticCandidateClass.tab_like: 0.76,
        SemanticCandidateClass.close_like: 0.84,
        SemanticCandidateClass.popup_dismiss_like: 0.82,
        SemanticCandidateClass.interactive_region_like: 0.6,
    }[candidate_class]
    valid_confidences = tuple(
        confidence
        for confidence in source_confidences
        if confidence is not None
    )
    if valid_confidences:
        baseline = max(baseline, sum(valid_confidences) / len(valid_confidences))
    if signal_status == "partial":
        baseline = max(0.0, baseline - 0.12)
    if signal_status == "absent":
        baseline = max(0.0, baseline - 0.2)
    return min(0.99, baseline)


def _bbox_contains(outer: NormalizedBBox, inner: NormalizedBBox) -> bool:
    return (
        inner.left >= outer.left
        and inner.top >= outer.top
        and inner.left + inner.width <= outer.left + outer.width
        and inner.top + inner.height <= outer.top + outer.height
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


def _overlap_area(first: NormalizedBBox, second: NormalizedBBox) -> float:
    if not _bbox_overlaps(first, second):
        return 0.0
    overlap_left = max(first.left, second.left)
    overlap_top = max(first.top, second.top)
    overlap_right = min(first.left + first.width, second.left + second.width)
    overlap_bottom = min(first.top + first.height, second.top + second.height)
    return max(0.0, overlap_right - overlap_left) * max(0.0, overlap_bottom - overlap_top)
