"""Observe-only heuristic candidate generation on top of semantic enrichment."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Mapping, Self

from universal_visual_os_agent.geometry import NormalizedBBox
from universal_visual_os_agent.perception import (
    ObserveOnlyHeuristicVisualGroundingProvider,
    VisualAnchor,
    VisualCueKind,
    VisualGroundingRequest,
    VisualGroundingSupportStatus,
)
from universal_visual_os_agent.perception.interfaces import VisualGroundingProvider
from universal_visual_os_agent.semantics.ontology import (
    CandidateProvenanceRecord,
    CandidateSelectionRiskLevel,
    SemanticCandidateSourceType,
    evaluate_candidate_resolver_readiness,
    normalize_provenance,
    normalize_source_of_truth_priority,
    provenance_source_types,
)
from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
    SemanticCandidateClass,
    SemanticLayoutRole,
    SemanticLayoutRegion,
    SemanticStateSnapshot,
    SemanticTextBlock,
)
from universal_visual_os_agent.semantics.text_semantics import (
    BUTTON_TEXT_VOCABULARY,
    CLOSE_TEXT_VOCABULARY,
    DISMISS_TEXT_VOCABULARY,
    INPUT_TEXT_VOCABULARY,
    TextSemanticVocabulary,
    normalize_ui_phrase,
    phrase_matches_vocabulary,
    tokenize_ui_text,
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
_BUTTON_HINTS = BUTTON_TEXT_VOCABULARY
_INPUT_HINTS = INPUT_TEXT_VOCABULARY
_CLOSE_HINTS = CLOSE_TEXT_VOCABULARY
_POPUP_DISMISS_HINTS = DISMISS_TEXT_VOCABULARY


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


@dataclass(slots=True, frozen=True, kw_only=True)
class _VisualGroundingArtifacts:
    support_status: VisualGroundingSupportStatus
    cue_kinds: tuple[VisualCueKind, ...] = ()
    confidence: float | None = None
    window_anchor: VisualAnchor | None = None
    reference_anchor: VisualAnchor | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)


class ObserveOnlyCandidateGenerator:
    """Derive richer, strictly non-actionable candidates from semantic metadata."""

    generator_name = "ObserveOnlyCandidateGenerator"

    def __init__(
        self,
        *,
        visual_grounder: VisualGroundingProvider | None = None,
    ) -> None:
        self._visual_grounder = (
            ObserveOnlyHeuristicVisualGroundingProvider()
            if visual_grounder is None
            else visual_grounder
        )

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
            source_type_counts = Counter(
                candidate.source_type.value
                for candidate in artifacts.generated_candidates
                if candidate.source_type is not None
            )
            risk_level_counts = Counter(
                candidate.selection_risk_level.value
                for candidate in artifacts.generated_candidates
                if candidate.selection_risk_level is not None
            )
            visual_grounding_status_counts = Counter(
                status
                for candidate in artifacts.generated_candidates
                if isinstance(
                    status := candidate.metadata.get("visual_grounding_support_status"),
                    str,
                )
            )
            visual_grounding_cue_counts = Counter(
                cue_kind
                for candidate in artifacts.generated_candidates
                for cue_kind in candidate.metadata.get("visual_grounding_cue_kinds", ())
                if isinstance(cue_kind, str)
            )
            readiness_status_counts = Counter(
                status
                for candidate in artifacts.generated_candidates
                if isinstance(
                    status := candidate.metadata.get("candidate_resolver_readiness_status"),
                    str,
                )
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
                    "generated_candidate_source_type_counts": tuple(sorted(source_type_counts.items())),
                    "generated_candidate_risk_level_counts": tuple(sorted(risk_level_counts.items())),
                    "generated_candidate_visual_grounding_status_counts": tuple(
                        sorted(visual_grounding_status_counts.items())
                    ),
                    "generated_candidate_visual_grounding_cue_counts": tuple(
                        sorted(visual_grounding_cue_counts.items())
                    ),
                    "generated_candidate_resolver_readiness_status_counts": tuple(
                        sorted(readiness_status_counts.items())
                    ),
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
                "source_type_counts": tuple(sorted(source_type_counts.items())),
                "risk_level_counts": tuple(sorted(risk_level_counts.items())),
                "visual_grounding_status_counts": tuple(
                    sorted(visual_grounding_status_counts.items())
                ),
                "visual_grounding_cue_counts": tuple(sorted(visual_grounding_cue_counts.items())),
                "resolver_readiness_status_counts": tuple(sorted(readiness_status_counts.items())),
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
        visual_grounding = self._ground_visual_subject(
            subject_id=f"{region.region_id}:interactive_region",
            bounds=region.bounds,
            reference_bounds=region.bounds,
            reference_role=None if region.semantic_role is None else region.semantic_role.value,
            label_hint=region.label,
        )
        explanations = [
            f"semantic layout role {region.semantic_role.value} indicates a likely interactive container",
            "layout-derived candidate remains observe-only and non-actionable in Phase 3A",
        ]
        explanations.extend(_visual_grounding_explanations(visual_grounding))
        provenance = normalize_provenance(
            (
                CandidateProvenanceRecord(
                    source_type=SemanticCandidateSourceType.layout,
                    source_id=region.region_id,
                    source_label=region.label,
                    confidence=region.confidence,
                ),
                CandidateProvenanceRecord(
                    source_type=SemanticCandidateSourceType.heuristic,
                    source_id=f"{region.region_id}:interactive_region",
                    source_label="interactive_region_heuristic",
                ),
                CandidateProvenanceRecord(
                    source_type=SemanticCandidateSourceType.heuristic,
                    source_id=f"{region.region_id}:visual_grounding",
                    source_label="visual_grounding_heuristic",
                    confidence=visual_grounding.confidence,
                    metadata={
                        "support_status": visual_grounding.support_status.value,
                        "cue_kinds": tuple(cue.value for cue in visual_grounding.cue_kinds),
                        "window_anchor": (
                            None
                            if visual_grounding.window_anchor is None
                            else visual_grounding.window_anchor.value
                        ),
                        "reference_anchor": (
                            None
                            if visual_grounding.reference_anchor is None
                            else visual_grounding.reference_anchor.value
                        ),
                    },
                ),
            )
        )
        source_of_truth_priority = normalize_source_of_truth_priority(
            (
                SemanticCandidateSourceType.layout,
                SemanticCandidateSourceType.heuristic,
            )
        )
        candidate_id = _unique_candidate_id(
            f"{region.region_id}:generated:{SemanticCandidateClass.interactive_region_like.value}",
            existing_candidate_ids,
        )
        candidate = SemanticCandidate(
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
            source_type=SemanticCandidateSourceType.layout,
            selection_risk_level=CandidateSelectionRiskLevel.high,
            disambiguation_needed=True,
            requires_local_resolver=True,
            source_conflict_present=False,
            source_of_truth_priority=source_of_truth_priority,
            provenance=provenance,
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
                "candidate_source_type": SemanticCandidateSourceType.layout.value,
                "candidate_selection_risk_level": CandidateSelectionRiskLevel.high.value,
                "candidate_disambiguation_needed": True,
                "candidate_requires_local_resolver": True,
                "candidate_source_conflict_present": False,
                "candidate_source_of_truth_priority": tuple(
                    source_type.value for source_type in source_of_truth_priority
                ),
                "candidate_provenance": _provenance_metadata(provenance),
                **_visual_grounding_metadata(visual_grounding),
                "observe_only": True,
                "analysis_only": True,
                "non_actionable_candidate": True,
                "non_actionable_reason": (
                    "Phase 3A generated candidates are hypotheses only and never actionable."
                ),
                "heuristic_explanations": tuple(explanations),
            },
        )
        return _with_candidate_resolver_readiness(candidate)

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
        visual_grounding = self._ground_visual_subject(
            subject_id=block.text_block_id,
            bounds=block.bounds,
            reference_bounds=region.bounds,
            reference_role=None if region.semantic_role is None else region.semantic_role.value,
            label_hint=block.extracted_text,
        )

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
                visual_grounding=visual_grounding,
                existing_candidate_ids=existing_candidate_ids,
            )

        candidate_class = _classify_text_block(
            block,
            region=region,
            normalized_text=normalized_text,
            visual_cue_kinds=visual_grounding.cue_kinds,
        )
        if candidate_class is None:
            return ()

        explanations = _heuristic_explanations_for_block(
            block,
            region=region,
            candidate_class=candidate_class,
            normalized_text=normalized_text,
            visual_cue_kinds=visual_grounding.cue_kinds,
        )
        explanations = tuple((*explanations, *_visual_grounding_explanations(visual_grounding)))
        source_type = _candidate_source_type_for_text_block(block=block, region=region)
        source_conflict_present = _source_conflict_present_for_text_block(
            candidate_class,
            region=region,
            normalized_text=normalized_text,
        )
        disambiguation_needed = _disambiguation_needed(
            candidate_class,
            source_conflict_present=source_conflict_present,
            signal_status=_signal_status_for_region(region),
        )
        selection_risk_level = _selection_risk_level(
            candidate_class,
            source_conflict_present=source_conflict_present,
            signal_status=_signal_status_for_region(region),
            token_count=len(tokens),
        )
        requires_local_resolver = _requires_local_resolver(
            selection_risk_level,
            disambiguation_needed=disambiguation_needed,
            source_conflict_present=source_conflict_present,
        )
        provenance = _text_block_provenance(
            block,
            region=region,
            candidate_class=candidate_class,
            visual_grounding=visual_grounding,
        )
        source_of_truth_priority = _source_of_truth_priority_for_text_block()
        candidate_id = _unique_candidate_id(
            f"{block.text_block_id}:generated:{candidate_class.value}",
            existing_candidate_ids,
        )
        candidate = SemanticCandidate(
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
            source_type=source_type,
            selection_risk_level=selection_risk_level,
            disambiguation_needed=disambiguation_needed,
            requires_local_resolver=requires_local_resolver,
            source_conflict_present=source_conflict_present,
            source_of_truth_priority=source_of_truth_priority,
            provenance=provenance,
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
                "candidate_source_type": source_type.value,
                "candidate_selection_risk_level": selection_risk_level.value,
                "candidate_disambiguation_needed": disambiguation_needed,
                "candidate_requires_local_resolver": requires_local_resolver,
                "candidate_source_conflict_present": source_conflict_present,
                "candidate_source_of_truth_priority": tuple(
                    source.value for source in source_of_truth_priority
                ),
                "candidate_provenance": _provenance_metadata(provenance),
                **_visual_grounding_metadata(visual_grounding),
                "observe_only": True,
                "analysis_only": True,
                "non_actionable_candidate": True,
                "non_actionable_reason": (
                    "Phase 3A generated candidates are hypotheses only and never actionable."
                ),
                "heuristic_explanations": tuple(explanations),
            },
        )
        return (_with_candidate_resolver_readiness(candidate),)

    def _build_navigation_tab_candidates(
        self,
        block: SemanticTextBlock,
        *,
        region: SemanticLayoutRegion,
        tokens: tuple[str, ...],
        visual_grounding: _VisualGroundingArtifacts,
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
            explanations = tuple((*explanations, *_visual_grounding_explanations(visual_grounding)))
            candidate_class = SemanticCandidateClass.tab_like
            source_type = _candidate_source_type_for_text_block(block=block, region=region)
            source_conflict_present = _source_conflict_present_for_text_block(
                candidate_class,
                region=region,
                normalized_text=token,
            )
            disambiguation_needed = _disambiguation_needed(
                candidate_class,
                source_conflict_present=source_conflict_present,
                signal_status=_signal_status_for_region(region),
            )
            selection_risk_level = _selection_risk_level(
                candidate_class,
                source_conflict_present=source_conflict_present,
                signal_status=_signal_status_for_region(region),
                token_count=1,
            )
            requires_local_resolver = _requires_local_resolver(
                selection_risk_level,
                disambiguation_needed=disambiguation_needed,
                source_conflict_present=source_conflict_present,
            )
            provenance = _text_block_provenance(
                block,
                region=region,
                candidate_class=candidate_class,
                visual_grounding=visual_grounding,
                token_index=index,
                token_count=len(tokens),
                token_label=token,
            )
            source_of_truth_priority = _source_of_truth_priority_for_text_block()
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
                source_type=source_type,
                selection_risk_level=selection_risk_level,
                disambiguation_needed=disambiguation_needed,
                requires_local_resolver=requires_local_resolver,
                source_conflict_present=source_conflict_present,
                source_of_truth_priority=source_of_truth_priority,
                provenance=provenance,
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
                    "candidate_source_type": source_type.value,
                    "candidate_selection_risk_level": selection_risk_level.value,
                    "candidate_disambiguation_needed": disambiguation_needed,
                    "candidate_requires_local_resolver": requires_local_resolver,
                    "candidate_source_conflict_present": source_conflict_present,
                    "candidate_source_of_truth_priority": tuple(
                        source.value for source in source_of_truth_priority
                    ),
                    "candidate_provenance": _provenance_metadata(provenance),
                    **_visual_grounding_metadata(visual_grounding),
                    "observe_only": True,
                    "analysis_only": True,
                    "non_actionable_candidate": True,
                    "non_actionable_reason": (
                        "Phase 3A generated candidates are hypotheses only and never actionable."
                    ),
                    "heuristic_explanations": explanations,
                },
            )
            candidates.append(_with_candidate_resolver_readiness(candidate))
        return tuple(candidates)

    def _ground_visual_subject(
        self,
        *,
        subject_id: str,
        bounds: NormalizedBBox,
        reference_bounds: NormalizedBBox | None,
        reference_role: str | None,
        label_hint: str | None,
    ) -> _VisualGroundingArtifacts:
        try:
            result = self._visual_grounder.ground(
                VisualGroundingRequest(
                    request_id=f"{subject_id}:visual_grounding_request",
                    subject_id=subject_id,
                    subject_bounds=bounds,
                    reference_bounds=reference_bounds,
                    reference_role=reference_role,
                    label_hint=label_hint,
                )
            )
        except Exception as exc:  # noqa: BLE001 - grounding must remain failure-safe
            return _VisualGroundingArtifacts(
                support_status=VisualGroundingSupportStatus.unavailable,
                metadata={
                    "provider_name": type(self._visual_grounder).__name__,
                    "error_code": "visual_grounding_exception",
                    "error_message": str(exc),
                    "exception_type": type(exc).__name__,
                },
            )
        if not result.success or result.assessment is None:
            return _VisualGroundingArtifacts(
                support_status=VisualGroundingSupportStatus.unavailable,
                metadata={
                    "provider_name": result.provider_name,
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                    **dict(result.details),
                },
            )
        assessment = result.assessment
        return _VisualGroundingArtifacts(
            support_status=assessment.support_status,
            cue_kinds=assessment.cue_kinds,
            confidence=assessment.confidence,
            window_anchor=assessment.window_anchor,
            reference_anchor=assessment.reference_anchor,
            metadata={
                "provider_name": result.provider_name,
                "request_id": assessment.request_id,
                "window_relative_center": (
                    assessment.window_relative_center.x,
                    assessment.window_relative_center.y,
                ),
                "window_area_ratio": assessment.window_area_ratio,
                "reference_relative_center": (
                    None
                    if assessment.reference_relative_center is None
                    else (
                        assessment.reference_relative_center.x,
                        assessment.reference_relative_center.y,
                    )
                ),
                "reference_area_ratio": assessment.reference_area_ratio,
                **dict(assessment.metadata),
            },
        )


def _classify_text_block(
    block: SemanticTextBlock,
    *,
    region: SemanticLayoutRegion,
    normalized_text: str,
    visual_cue_kinds: tuple[VisualCueKind, ...],
) -> SemanticCandidateClass | None:
    if region.semantic_role in _DIALOG_ROLES and _matches_phrase(normalized_text, _POPUP_DISMISS_HINTS):
        return SemanticCandidateClass.popup_dismiss_like
    if VisualCueKind.close_affordance_like in visual_cue_kinds:
        return SemanticCandidateClass.close_like
    if _is_close_like(block, region=region, normalized_text=normalized_text):
        return SemanticCandidateClass.close_like
    if (
        _matches_phrase(normalized_text, _INPUT_HINTS)
        or normalized_text.endswith(":")
        or VisualCueKind.input_affordance_like in visual_cue_kinds
    ):
        return SemanticCandidateClass.input_like
    if _matches_phrase(normalized_text, _BUTTON_HINTS) or (
        region.semantic_role in _DIALOG_ROLES and len(_tokenize_for_candidates(block.extracted_text)) <= 3
    ) or (
        VisualCueKind.dialog_action_affordance_like in visual_cue_kinds
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
    visual_cue_kinds: tuple[VisualCueKind, ...],
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
    if visual_cue_kinds:
        explanations.append(
            "non-text visual cues supported "
            + ", ".join(cue_kind.value for cue_kind in visual_cue_kinds)
        )
    return tuple(explanations)


def _is_close_like(
    block: SemanticTextBlock,
    *,
    region: SemanticLayoutRegion,
    normalized_text: str,
) -> bool:
    if _matches_phrase(normalized_text, _CLOSE_HINTS):
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
    return normalize_ui_phrase(text)


def _tokenize_for_candidates(text: str | None) -> tuple[str, ...]:
    return tokenize_ui_text(text)


def _matches_phrase(text: str, phrases: TextSemanticVocabulary) -> bool:
    return phrase_matches_vocabulary(text, phrases)


def _candidate_source_type_for_text_block(
    *,
    block: SemanticTextBlock,
    region: SemanticLayoutRegion,
) -> SemanticCandidateSourceType:
    del block, region
    return SemanticCandidateSourceType.mixed


def _source_of_truth_priority_for_text_block() -> tuple[SemanticCandidateSourceType, ...]:
    return normalize_source_of_truth_priority(
        (
            SemanticCandidateSourceType.ocr,
            SemanticCandidateSourceType.layout,
            SemanticCandidateSourceType.heuristic,
        )
    )


def _text_block_provenance(
    block: SemanticTextBlock,
    *,
    region: SemanticLayoutRegion,
    candidate_class: SemanticCandidateClass,
    visual_grounding: _VisualGroundingArtifacts,
    token_index: int | None = None,
    token_count: int | None = None,
    token_label: str | None = None,
) -> tuple[CandidateProvenanceRecord, ...]:
    heuristic_metadata: dict[str, object] = {"candidate_class": candidate_class.value}
    if token_index is not None:
        heuristic_metadata["candidate_token_index"] = token_index
    if token_count is not None:
        heuristic_metadata["candidate_token_count"] = token_count
    if token_label is not None:
        heuristic_metadata["candidate_token_label"] = token_label
    return normalize_provenance(
        (
            CandidateProvenanceRecord(
                source_type=SemanticCandidateSourceType.ocr,
                source_id=block.text_block_id,
                source_label=block.label if block.extracted_text is None else block.extracted_text,
                confidence=block.confidence,
                metadata={
                    "text_region_id": block.region_id,
                    "text": block.extracted_text,
                },
            ),
            CandidateProvenanceRecord(
                source_type=SemanticCandidateSourceType.layout,
                source_id=region.region_id,
                source_label=region.label,
                confidence=region.confidence,
                metadata={
                    "semantic_role": None if region.semantic_role is None else region.semantic_role.value,
                },
            ),
            CandidateProvenanceRecord(
                source_type=SemanticCandidateSourceType.heuristic,
                source_id=f"{block.text_block_id}:{candidate_class.value}",
                source_label=f"{candidate_class.value}_heuristic",
                metadata=heuristic_metadata,
            ),
            CandidateProvenanceRecord(
                source_type=SemanticCandidateSourceType.heuristic,
                source_id=f"{block.text_block_id}:visual_grounding",
                source_label="visual_grounding_heuristic",
                confidence=visual_grounding.confidence,
                metadata={
                    "support_status": visual_grounding.support_status.value,
                    "cue_kinds": tuple(cue.value for cue in visual_grounding.cue_kinds),
                    "window_anchor": (
                        None
                        if visual_grounding.window_anchor is None
                        else visual_grounding.window_anchor.value
                    ),
                    "reference_anchor": (
                        None
                        if visual_grounding.reference_anchor is None
                        else visual_grounding.reference_anchor.value
                    ),
                },
            ),
        )
    )


def _source_conflict_present_for_text_block(
    candidate_class: SemanticCandidateClass,
    *,
    region: SemanticLayoutRegion,
    normalized_text: str,
) -> bool:
    if region.semantic_role is None:
        return True
    if candidate_class is SemanticCandidateClass.interactive_region_like:
        return True
    if candidate_class is SemanticCandidateClass.close_like:
        return region.semantic_role not in _DIALOG_ROLES and not _matches_phrase(
            normalized_text, _CLOSE_HINTS
        )
    if candidate_class is SemanticCandidateClass.popup_dismiss_like:
        return region.semantic_role not in _DIALOG_ROLES
    if candidate_class is SemanticCandidateClass.input_like and _matches_phrase(
        normalized_text, _BUTTON_HINTS
    ):
        return True
    if candidate_class is SemanticCandidateClass.button_like and _matches_phrase(
        normalized_text, _INPUT_HINTS
    ):
        return True
    if candidate_class is SemanticCandidateClass.tab_like:
        return region.semantic_role not in _NAVIGATION_ROLES
    return False


def _disambiguation_needed(
    candidate_class: SemanticCandidateClass,
    *,
    source_conflict_present: bool,
    signal_status: str,
) -> bool:
    if source_conflict_present or signal_status != "available":
        return True
    return candidate_class in {
        SemanticCandidateClass.close_like,
        SemanticCandidateClass.popup_dismiss_like,
        SemanticCandidateClass.interactive_region_like,
    }


def _selection_risk_level(
    candidate_class: SemanticCandidateClass,
    *,
    source_conflict_present: bool,
    signal_status: str,
    token_count: int,
) -> CandidateSelectionRiskLevel:
    if (
        source_conflict_present
        or signal_status != "available"
        or candidate_class
        in {
            SemanticCandidateClass.close_like,
            SemanticCandidateClass.popup_dismiss_like,
            SemanticCandidateClass.interactive_region_like,
        }
    ):
        return CandidateSelectionRiskLevel.high
    if candidate_class in {
        SemanticCandidateClass.button_like,
        SemanticCandidateClass.input_like,
    }:
        return CandidateSelectionRiskLevel.medium
    if candidate_class is SemanticCandidateClass.tab_like and token_count == 1:
        return CandidateSelectionRiskLevel.low
    return CandidateSelectionRiskLevel.medium


def _requires_local_resolver(
    selection_risk_level: CandidateSelectionRiskLevel,
    *,
    disambiguation_needed: bool,
    source_conflict_present: bool,
) -> bool:
    return (
        selection_risk_level is CandidateSelectionRiskLevel.high
        or disambiguation_needed
        or source_conflict_present
    )


def _provenance_metadata(
    provenance: tuple[CandidateProvenanceRecord, ...],
) -> tuple[Mapping[str, object], ...]:
    return tuple(
        {
            "source_type": record.source_type.value,
            "source_id": record.source_id,
            "source_label": record.source_label,
            "confidence": record.confidence,
            "metadata": dict(record.metadata),
        }
        for record in provenance
    )


def _visual_grounding_explanations(
    visual_grounding: _VisualGroundingArtifacts,
) -> tuple[str, ...]:
    if visual_grounding.support_status is VisualGroundingSupportStatus.unavailable:
        return ("non-text visual grounding support was unavailable, so text/layout cues stayed primary",)
    if not visual_grounding.cue_kinds:
        return ()
    return (
        "structured non-text grounding inferred "
        + ", ".join(cue_kind.value for cue_kind in visual_grounding.cue_kinds),
    )


def _visual_grounding_metadata(
    visual_grounding: _VisualGroundingArtifacts,
) -> Mapping[str, object]:
    return {
        "visual_grounding_support_status": visual_grounding.support_status.value,
        "visual_grounding_cue_kinds": tuple(
            cue_kind.value for cue_kind in visual_grounding.cue_kinds
        ),
        "visual_grounding_confidence": visual_grounding.confidence,
        "visual_grounding_window_anchor": (
            None
            if visual_grounding.window_anchor is None
            else visual_grounding.window_anchor.value
        ),
        "visual_grounding_reference_anchor": (
            None
            if visual_grounding.reference_anchor is None
            else visual_grounding.reference_anchor.value
        ),
        **dict(visual_grounding.metadata),
    }


def _with_candidate_resolver_readiness(candidate: SemanticCandidate) -> SemanticCandidate:
    readiness = evaluate_candidate_resolver_readiness(candidate)
    return replace(
        candidate,
        metadata={
            **dict(candidate.metadata),
            "candidate_resolver_readiness_status": readiness.status.value,
            "candidate_resolver_readiness_reason_codes": tuple(
                reason.value for reason in readiness.reason_codes
            ),
            "candidate_ontology_completeness_status": readiness.ontology_completeness_status,
            "candidate_resolver_handoff_completeness_status": (
                readiness.handoff_completeness_status
            ),
            "candidate_provenance_source_types": tuple(
                source_type.value for source_type in provenance_source_types(candidate.provenance)
            ),
        },
    )


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
