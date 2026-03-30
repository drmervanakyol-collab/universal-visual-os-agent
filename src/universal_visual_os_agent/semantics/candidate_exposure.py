"""Observe-only exposure layer for generated and scored semantic candidates."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Mapping, Self

from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
    SemanticCandidateClass,
    SemanticStateSnapshot,
)


@dataclass(slots=True, frozen=True, kw_only=True)
class CandidateExposureOptions:
    """Filtering options for stable observe-only candidate exposure."""

    minimum_score: float | None = None
    candidate_classes: tuple[SemanticCandidateClass, ...] = ()
    limit: int | None = None
    include_only_visible: bool = False

    def __post_init__(self) -> None:
        if self.minimum_score is not None and not 0.0 <= self.minimum_score <= 1.0:
            raise ValueError("minimum_score must be between 0.0 and 1.0 inclusive.")
        if self.limit is not None and self.limit <= 0:
            raise ValueError("limit must be positive when provided.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ExposedCandidate:
    """A stable downstream-facing observe-only candidate view."""

    candidate_id: str
    label: str
    candidate_class: SemanticCandidateClass | None
    score: float | None
    rank: int
    visible: bool
    enabled: bool = False
    actionable: bool = False
    observe_only: bool = True
    non_actionable: bool = True
    source_layout_region_id: str | None = None
    source_text_region_id: str | None = None
    source_text_block_id: str | None = None
    semantic_layout_role: str | None = None
    heuristic_explanations: tuple[str, ...] = ()
    score_explanations: tuple[str, ...] = ()
    score_factors: Mapping[str, float] = field(default_factory=dict)
    completeness_status: str = "available"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("candidate_id must not be empty.")
        if not self.label:
            raise ValueError("label must not be empty.")
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0 inclusive.")
        if self.rank <= 0:
            raise ValueError("rank must be positive.")
        if self.enabled:
            raise ValueError("Exposed candidates must remain disabled.")
        if self.actionable:
            raise ValueError("Exposed candidates must remain non-actionable.")
        if not self.observe_only or not self.non_actionable:
            raise ValueError("Exposed candidates must remain observe-only and non-actionable.")
        if self.completeness_status not in {"available", "partial"}:
            raise ValueError("completeness_status must be 'available' or 'partial'.")


@dataclass(slots=True, frozen=True, kw_only=True)
class ExposedCandidateGroup:
    """A stable grouping of exposed candidates."""

    group_key: str
    label: str
    candidates: tuple[ExposedCandidate, ...]
    candidate_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.group_key:
            raise ValueError("group_key must not be empty.")
        if not self.label:
            raise ValueError("label must not be empty.")
        if len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise ValueError("candidate_ids must be unique within a group.")
        if self.candidate_ids != tuple(candidate.candidate_id for candidate in self.candidates):
            raise ValueError("candidate_ids must match candidates in order.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CandidateExposureView:
    """Stable observe-only candidate exposure view for downstream consumers."""

    snapshot_id: str
    candidates: tuple[ExposedCandidate, ...]
    groups: tuple[ExposedCandidateGroup, ...]
    total_scored_candidate_count: int
    exposed_candidate_count: int
    filtered_out_candidate_ids: tuple[str, ...] = ()
    signal_status: str = "absent"
    sort_order: str = "score_desc_then_candidate_id"
    options: CandidateExposureOptions = field(default_factory=CandidateExposureOptions)
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            raise ValueError("snapshot_id must not be empty.")
        if self.total_scored_candidate_count < 0:
            raise ValueError("total_scored_candidate_count must not be negative.")
        if self.exposed_candidate_count != len(self.candidates):
            raise ValueError("exposed_candidate_count must match len(candidates).")
        if self.total_scored_candidate_count < self.exposed_candidate_count:
            raise ValueError("total_scored_candidate_count must be >= exposed_candidate_count.")
        if self.signal_status not in {"available", "partial", "absent"}:
            raise ValueError("signal_status must be available, partial, or absent.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CandidateExposureResult:
    """Structured result for safe observe-only candidate exposure."""

    exposer_name: str
    success: bool
    source_snapshot: SemanticStateSnapshot | None = None
    exposure_view: CandidateExposureView | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.exposer_name:
            raise ValueError("exposer_name must not be empty.")
        if self.success and (self.source_snapshot is None or self.exposure_view is None):
            raise ValueError("Successful candidate exposure must include source_snapshot and exposure_view.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed candidate exposure must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful candidate exposure must not include error details.")
        if not self.success and self.exposure_view is not None:
            raise ValueError("Failed candidate exposure must not include exposure_view.")

    @classmethod
    def ok(
        cls,
        *,
        exposer_name: str,
        source_snapshot: SemanticStateSnapshot,
        exposure_view: CandidateExposureView,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            exposer_name=exposer_name,
            success=True,
            source_snapshot=source_snapshot,
            exposure_view=exposure_view,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        exposer_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            exposer_name=exposer_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class _ExposureArtifacts:
    exposed_candidates: tuple[ExposedCandidate, ...]
    groups: tuple[ExposedCandidateGroup, ...]
    filtered_out_candidate_ids: tuple[str, ...] = ()
    missing_score_candidate_ids: tuple[str, ...] = ()
    missing_candidate_class_ids: tuple[str, ...] = ()
    missing_score_explanation_candidate_ids: tuple[str, ...] = ()
    missing_score_factor_candidate_ids: tuple[str, ...] = ()
    missing_source_layout_candidate_ids: tuple[str, ...] = ()
    unsafe_source_candidate_ids: tuple[str, ...] = ()
    scoring_metadata_incomplete: bool = False

    @property
    def signal_status(self) -> str:
        if (
            self.missing_score_candidate_ids
            or self.missing_candidate_class_ids
            or self.missing_score_explanation_candidate_ids
            or self.missing_score_factor_candidate_ids
            or self.missing_source_layout_candidate_ids
            or self.unsafe_source_candidate_ids
            or self.scoring_metadata_incomplete
        ):
            return "partial"
        if self.exposed_candidates:
            return "available"
        return "absent"


class ObserveOnlyCandidateExposer:
    """Expose scored generated candidates in a stable observe-only view."""

    exposer_name = "ObserveOnlyCandidateExposer"

    def expose(
        self,
        snapshot: SemanticStateSnapshot,
        *,
        options: CandidateExposureOptions | None = None,
    ) -> CandidateExposureResult:
        if snapshot.metadata.get("candidate_scoring") is not True:
            return CandidateExposureResult.failure(
                exposer_name=self.exposer_name,
                error_code="candidate_scoring_unavailable",
                error_message="Candidate exposure requires candidate scoring output.",
            )

        exposure_options = CandidateExposureOptions() if options is None else options
        try:
            scored_generated_candidates = tuple(
                candidate
                for candidate in snapshot.candidates
                if candidate.metadata.get("semantic_origin") == "candidate_generation"
            )
            artifacts = self._build_exposure_view(
                snapshot,
                scored_generated_candidates=scored_generated_candidates,
                options=exposure_options,
            )
            exposure_view = CandidateExposureView(
                snapshot_id=snapshot.snapshot_id,
                candidates=artifacts.exposed_candidates,
                groups=artifacts.groups,
                total_scored_candidate_count=len(scored_generated_candidates),
                exposed_candidate_count=len(artifacts.exposed_candidates),
                filtered_out_candidate_ids=artifacts.filtered_out_candidate_ids,
                signal_status=artifacts.signal_status,
                options=exposure_options,
                metadata={
                    "observe_only": True,
                    "analysis_only": True,
                    "non_actionable": True,
                    "sorted_candidate_ids": tuple(
                        candidate.candidate_id for candidate in artifacts.exposed_candidates
                    ),
                    "group_keys": tuple(group.group_key for group in artifacts.groups),
                    "applied_minimum_score": exposure_options.minimum_score,
                    "applied_candidate_classes": tuple(
                        candidate_class.value for candidate_class in exposure_options.candidate_classes
                    ),
                    "applied_limit": exposure_options.limit,
                    "include_only_visible": exposure_options.include_only_visible,
                    "missing_score_candidate_ids": artifacts.missing_score_candidate_ids,
                    "missing_candidate_class_ids": artifacts.missing_candidate_class_ids,
                    "missing_score_explanation_candidate_ids": (
                        artifacts.missing_score_explanation_candidate_ids
                    ),
                    "missing_score_factor_candidate_ids": (
                        artifacts.missing_score_factor_candidate_ids
                    ),
                    "missing_source_layout_candidate_ids": artifacts.missing_source_layout_candidate_ids,
                    "unsafe_source_candidate_ids": artifacts.unsafe_source_candidate_ids,
                    "scoring_metadata_incomplete": artifacts.scoring_metadata_incomplete,
                    "class_counts": tuple(
                        sorted(
                            Counter(
                                candidate.candidate_class.value
                                for candidate in artifacts.exposed_candidates
                                if candidate.candidate_class is not None
                            ).items()
                        )
                    ),
                },
            )
        except Exception as exc:  # noqa: BLE001 - exposure must remain failure-safe
            return CandidateExposureResult.failure(
                exposer_name=self.exposer_name,
                error_code="candidate_exposure_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return CandidateExposureResult.ok(
            exposer_name=self.exposer_name,
            source_snapshot=snapshot,
            exposure_view=exposure_view,
            details={
                "exposed_candidate_count": len(artifacts.exposed_candidates),
                "filtered_out_candidate_count": len(artifacts.filtered_out_candidate_ids),
                "signal_status": artifacts.signal_status,
            },
        )

    def _build_exposure_view(
        self,
        snapshot: SemanticStateSnapshot,
        *,
        scored_generated_candidates: tuple[SemanticCandidate, ...],
        options: CandidateExposureOptions,
    ) -> _ExposureArtifacts:
        layout_region_ids = {region.region_id for region in snapshot.layout_regions}
        expected_scored_ids = snapshot.metadata.get("scored_candidate_ids")
        scoring_metadata_incomplete = not isinstance(expected_scored_ids, tuple)

        missing_score_candidate_ids: list[str] = []
        missing_candidate_class_ids: list[str] = []
        missing_score_explanation_candidate_ids: list[str] = []
        missing_score_factor_candidate_ids: list[str] = []
        missing_source_layout_candidate_ids: list[str] = []
        unsafe_source_candidate_ids: list[str] = []

        staged_candidates: list[ExposedCandidate] = []
        filtered_out_candidate_ids: list[str] = []

        sorted_candidates = sorted(scored_generated_candidates, key=_candidate_sort_key)
        allowed_classes = set(options.candidate_classes)
        for candidate in sorted_candidates:
            if options.include_only_visible and not candidate.visible:
                filtered_out_candidate_ids.append(candidate.candidate_id)
                continue
            if allowed_classes and candidate.candidate_class not in allowed_classes:
                filtered_out_candidate_ids.append(candidate.candidate_id)
                continue
            if options.minimum_score is not None:
                if candidate.confidence is None or candidate.confidence < options.minimum_score:
                    filtered_out_candidate_ids.append(candidate.candidate_id)
                    continue

            score_explanations = _coerce_score_explanations(candidate)
            score_factors = _coerce_score_factors(candidate)
            source_layout_region_id = _coerce_optional_string(
                candidate.metadata.get("source_layout_region_id")
            )
            if candidate.confidence is None:
                missing_score_candidate_ids.append(candidate.candidate_id)
            if candidate.candidate_class is None:
                missing_candidate_class_ids.append(candidate.candidate_id)
            if not score_explanations:
                missing_score_explanation_candidate_ids.append(candidate.candidate_id)
            if not score_factors:
                missing_score_factor_candidate_ids.append(candidate.candidate_id)
            if source_layout_region_id is None or source_layout_region_id not in layout_region_ids:
                missing_source_layout_candidate_ids.append(candidate.candidate_id)
            if candidate.enabled or candidate.actionable or candidate.metadata.get("observe_only") is not True:
                unsafe_source_candidate_ids.append(candidate.candidate_id)

            completeness_status = _candidate_completeness_status(
                candidate,
                score_explanations=score_explanations,
                score_factors=score_factors,
                source_layout_region_id=source_layout_region_id,
                layout_region_ids=layout_region_ids,
            )
            staged_candidates.append(
                ExposedCandidate(
                    candidate_id=candidate.candidate_id,
                    label=candidate.label,
                    candidate_class=candidate.candidate_class,
                    score=candidate.confidence,
                    rank=1,
                    visible=candidate.visible,
                    enabled=False,
                    actionable=False,
                    observe_only=True,
                    non_actionable=True,
                    source_layout_region_id=source_layout_region_id,
                    source_text_region_id=_coerce_optional_string(
                        candidate.metadata.get("source_text_region_id")
                    ),
                    source_text_block_id=_coerce_optional_string(
                        candidate.metadata.get("source_text_block_id")
                    ),
                    semantic_layout_role=_coerce_optional_string(
                        candidate.metadata.get("semantic_layout_role")
                    ),
                    heuristic_explanations=candidate.heuristic_explanations,
                    score_explanations=score_explanations,
                    score_factors=score_factors,
                    completeness_status=completeness_status,
                    metadata={
                        **dict(candidate.metadata),
                        "candidate_exposed": True,
                        "candidate_exposer_name": self.exposer_name,
                        "candidate_rank": 1,
                        "candidate_exposure_completeness_status": completeness_status,
                        "observe_only": True,
                        "analysis_only": True,
                        "non_actionable_candidate": True,
                    },
                )
            )
        if options.limit is not None and len(staged_candidates) > options.limit:
            filtered_out_candidate_ids.extend(
                candidate.candidate_id for candidate in staged_candidates[options.limit :]
            )
            staged_candidates = staged_candidates[: options.limit]

        exposed_candidates = tuple(
            ExposedCandidate(
                candidate_id=candidate.candidate_id,
                label=candidate.label,
                candidate_class=candidate.candidate_class,
                score=candidate.score,
                rank=index,
                visible=candidate.visible,
                enabled=False,
                actionable=False,
                observe_only=True,
                non_actionable=True,
                source_layout_region_id=candidate.source_layout_region_id,
                source_text_region_id=candidate.source_text_region_id,
                source_text_block_id=candidate.source_text_block_id,
                semantic_layout_role=candidate.semantic_layout_role,
                heuristic_explanations=candidate.heuristic_explanations,
                score_explanations=candidate.score_explanations,
                score_factors=candidate.score_factors,
                completeness_status=candidate.completeness_status,
                metadata={
                    **dict(candidate.metadata),
                    "candidate_rank": index,
                },
            )
            for index, candidate in enumerate(staged_candidates, start=1)
        )

        groups = _build_groups(exposed_candidates)
        return _ExposureArtifacts(
            exposed_candidates=exposed_candidates,
            groups=groups,
            filtered_out_candidate_ids=tuple(filtered_out_candidate_ids),
            missing_score_candidate_ids=tuple(sorted(set(missing_score_candidate_ids))),
            missing_candidate_class_ids=tuple(sorted(set(missing_candidate_class_ids))),
            missing_score_explanation_candidate_ids=tuple(
                sorted(set(missing_score_explanation_candidate_ids))
            ),
            missing_score_factor_candidate_ids=tuple(sorted(set(missing_score_factor_candidate_ids))),
            missing_source_layout_candidate_ids=tuple(sorted(set(missing_source_layout_candidate_ids))),
            unsafe_source_candidate_ids=tuple(sorted(set(unsafe_source_candidate_ids))),
            scoring_metadata_incomplete=scoring_metadata_incomplete,
        )


def _candidate_sort_key(candidate: SemanticCandidate) -> tuple[bool, float, str]:
    return (
        candidate.confidence is None,
        -(candidate.confidence or 0.0),
        candidate.candidate_id,
    )


def _coerce_optional_string(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _coerce_score_explanations(candidate: SemanticCandidate) -> tuple[str, ...]:
    if candidate.score_explanations:
        return candidate.score_explanations
    metadata_value = candidate.metadata.get("candidate_score_explanations")
    if isinstance(metadata_value, tuple) and all(isinstance(item, str) for item in metadata_value):
        return metadata_value
    return ()


def _coerce_score_factors(candidate: SemanticCandidate) -> Mapping[str, float]:
    if candidate.score_factors:
        return candidate.score_factors
    metadata_value = candidate.metadata.get("candidate_score_factors")
    if isinstance(metadata_value, Mapping):
        coerced: dict[str, float] = {}
        for key, value in metadata_value.items():
            if isinstance(key, str) and isinstance(value, float):
                coerced[key] = value
        return coerced
    return {}


def _candidate_completeness_status(
    candidate: SemanticCandidate,
    *,
    score_explanations: tuple[str, ...],
    score_factors: Mapping[str, float],
    source_layout_region_id: str | None,
    layout_region_ids: set[str],
) -> str:
    if candidate.candidate_class is None:
        return "partial"
    if candidate.confidence is None:
        return "partial"
    if not score_explanations:
        return "partial"
    if not score_factors:
        return "partial"
    if source_layout_region_id is None or source_layout_region_id not in layout_region_ids:
        return "partial"
    if candidate.metadata.get("candidate_scored") is not True:
        return "partial"
    if candidate.enabled or candidate.actionable:
        return "partial"
    return "available"


def _build_groups(candidates: tuple[ExposedCandidate, ...]) -> tuple[ExposedCandidateGroup, ...]:
    grouped: dict[str, list[ExposedCandidate]] = {}
    for candidate in candidates:
        group_key = (
            candidate.candidate_class.value
            if candidate.candidate_class is not None
            else "unclassified"
        )
        grouped.setdefault(group_key, []).append(candidate)
    return tuple(
        ExposedCandidateGroup(
            group_key=group_key,
            label=_group_label(group_key),
            candidates=tuple(grouped[group_key]),
            candidate_ids=tuple(candidate.candidate_id for candidate in grouped[group_key]),
        )
        for group_key in sorted(grouped)
    )


def _group_label(group_key: str) -> str:
    return group_key.replace("_", " ").title()
