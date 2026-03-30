"""Observe-only scoring for non-actionable semantic candidates."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Mapping, Self

from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
    SemanticCandidateClass,
    SemanticLayoutRole,
    SemanticLayoutRegion,
    SemanticStateSnapshot,
    SemanticTextBlock,
    SemanticTextRegion,
)

_INPUT_HINTS = frozenset({"email", "filter", "find", "password", "search", "type", "username"})
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
_DISMISS_HINTS = frozenset(
    {"cancel", "dismiss", "later", "no thanks", "not now", "skip"}
)
_CLOSE_HINTS = frozenset({"close", "exit", "quit", "x"})
_TOKEN_SPLIT_PATTERN = re.compile(r"[\s,.:;!?/\\|()\[\]{}\"']+")
_CLASS_PRIORS = {
    SemanticCandidateClass.button_like: 0.72,
    SemanticCandidateClass.input_like: 0.74,
    SemanticCandidateClass.tab_like: 0.76,
    SemanticCandidateClass.close_like: 0.8,
    SemanticCandidateClass.popup_dismiss_like: 0.78,
    SemanticCandidateClass.interactive_region_like: 0.58,
}
_SIGNAL_STATUS_ADJUSTMENTS = {
    "available": 0.0,
    "partial": -0.08,
    "absent": -0.16,
}


@dataclass(slots=True, frozen=True, kw_only=True)
class CandidateScoringResult:
    """Structured result for observe-only candidate scoring."""

    scorer_name: str
    success: bool
    snapshot: SemanticStateSnapshot | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scorer_name:
            raise ValueError("scorer_name must not be empty.")
        if self.success and self.snapshot is None:
            raise ValueError("Successful candidate scoring must include snapshot.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed candidate scoring must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful candidate scoring must not include error details.")
        if not self.success and self.snapshot is not None:
            raise ValueError("Failed candidate scoring must not include snapshot.")

    @classmethod
    def ok(
        cls,
        *,
        scorer_name: str,
        snapshot: SemanticStateSnapshot,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            scorer_name=scorer_name,
            success=True,
            snapshot=snapshot,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        scorer_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            scorer_name=scorer_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class _ScoringArtifacts:
    scored_candidates: tuple[SemanticCandidate, ...]
    missing_layout_region_ids: tuple[str, ...] = ()
    missing_text_region_ids: tuple[str, ...] = ()
    missing_text_block_ids: tuple[str, ...] = ()
    missing_candidate_class_ids: tuple[str, ...] = ()
    candidate_generation_metadata_incomplete: bool = False

    @property
    def signal_status(self) -> str:
        if (
            self.missing_layout_region_ids
            or self.missing_text_region_ids
            or self.missing_text_block_ids
            or self.missing_candidate_class_ids
            or self.candidate_generation_metadata_incomplete
        ):
            return "partial"
        if self.scored_candidates:
            return "available"
        return "absent"


class ObserveOnlyCandidateScorer:
    """Assign conservative scores to generated observe-only candidates."""

    scorer_name = "ObserveOnlyCandidateScorer"

    def score(self, snapshot: SemanticStateSnapshot) -> CandidateScoringResult:
        if snapshot.metadata.get("candidate_generation") is not True:
            return CandidateScoringResult.failure(
                scorer_name=self.scorer_name,
                error_code="candidate_generation_unavailable",
                error_message="Candidate scoring requires candidate generation output.",
            )
        if not snapshot.layout_regions:
            return CandidateScoringResult.failure(
                scorer_name=self.scorer_name,
                error_code="layout_regions_unavailable",
                error_message="Candidate scoring requires semantic layout regions.",
            )

        try:
            generated_candidates = tuple(
                candidate
                for candidate in snapshot.candidates
                if candidate.metadata.get("semantic_origin") == "candidate_generation"
            )
            artifacts = self._score_generated_candidates(snapshot, generated_candidates=generated_candidates)
            scored_by_id = {
                candidate.candidate_id: candidate
                for candidate in artifacts.scored_candidates
            }
            scored_snapshot = replace(
                snapshot,
                candidates=tuple(
                    scored_by_id.get(candidate.candidate_id, candidate)
                    for candidate in snapshot.candidates
                ),
                metadata={
                    **dict(snapshot.metadata),
                    "candidate_scoring": True,
                    "candidate_scorer_name": self.scorer_name,
                    "scored_candidate_ids": tuple(
                        candidate.candidate_id for candidate in artifacts.scored_candidates
                    ),
                    "candidate_score_map": tuple(
                        (candidate.candidate_id, candidate.confidence)
                        for candidate in artifacts.scored_candidates
                    ),
                    "candidate_scoring_signal_status": artifacts.signal_status,
                    "candidate_scoring_missing_layout_region_ids": artifacts.missing_layout_region_ids,
                    "candidate_scoring_missing_text_region_ids": artifacts.missing_text_region_ids,
                    "candidate_scoring_missing_text_block_ids": artifacts.missing_text_block_ids,
                    "candidate_scoring_missing_candidate_class_ids": (
                        artifacts.missing_candidate_class_ids
                    ),
                    "candidate_scoring_generation_metadata_incomplete": (
                        artifacts.candidate_generation_metadata_incomplete
                    ),
                    "candidate_scoring_average_score": _average_score(artifacts.scored_candidates),
                    "candidate_scoring_class_counts": tuple(
                        sorted(
                            Counter(
                                candidate.candidate_class.value
                                for candidate in artifacts.scored_candidates
                                if candidate.candidate_class is not None
                            ).items()
                        )
                    ),
                },
            )
        except Exception as exc:  # noqa: BLE001 - scorer must remain failure-safe
            return CandidateScoringResult.failure(
                scorer_name=self.scorer_name,
                error_code="candidate_scoring_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return CandidateScoringResult.ok(
            scorer_name=self.scorer_name,
            snapshot=scored_snapshot,
            details={
                "scored_candidate_count": len(artifacts.scored_candidates),
                "signal_status": artifacts.signal_status,
                "average_score": _average_score(artifacts.scored_candidates),
            },
        )

    def _score_generated_candidates(
        self,
        snapshot: SemanticStateSnapshot,
        *,
        generated_candidates: tuple[SemanticCandidate, ...],
    ) -> _ScoringArtifacts:
        layout_regions_by_id = {region.region_id: region for region in snapshot.layout_regions}
        text_regions_by_id = {region.region_id: region for region in snapshot.text_regions}
        text_blocks_by_id = {block.text_block_id: block for block in snapshot.text_blocks}

        missing_layout_region_ids: set[str] = set()
        missing_text_region_ids: set[str] = set()
        missing_text_block_ids: set[str] = set()
        missing_candidate_class_ids: set[str] = set()

        expected_generated_ids = snapshot.metadata.get("generated_candidate_ids")
        metadata_incomplete = not isinstance(expected_generated_ids, tuple)

        scored_candidates: list[SemanticCandidate] = []
        for candidate in generated_candidates:
            if candidate.candidate_class is None:
                missing_candidate_class_ids.add(candidate.candidate_id)

            layout_region_id = candidate.metadata.get("source_layout_region_id")
            text_region_id = candidate.metadata.get("source_text_region_id")
            text_block_id = candidate.metadata.get("source_text_block_id")

            layout_region = _lookup_region(layout_regions_by_id, layout_region_id)
            text_region = _lookup_text_region(text_regions_by_id, text_region_id)
            text_block = _lookup_text_block(text_blocks_by_id, text_block_id)

            if isinstance(layout_region_id, str) and layout_region is None:
                missing_layout_region_ids.add(layout_region_id)
            if isinstance(text_region_id, str) and text_region is None:
                missing_text_region_ids.add(text_region_id)
            if isinstance(text_block_id, str) and text_block is None:
                missing_text_block_ids.add(text_block_id)

            scored_candidates.append(
                self._score_candidate(
                    candidate,
                    layout_region=layout_region,
                    text_region=text_region,
                    text_block=text_block,
                    snapshot_generation_signal_status=(
                        snapshot.metadata.get("candidate_generation_signal_status")
                        if isinstance(snapshot.metadata.get("candidate_generation_signal_status"), str)
                        else None
                    ),
                )
            )

        return _ScoringArtifacts(
            scored_candidates=tuple(scored_candidates),
            missing_layout_region_ids=tuple(sorted(missing_layout_region_ids)),
            missing_text_region_ids=tuple(sorted(missing_text_region_ids)),
            missing_text_block_ids=tuple(sorted(missing_text_block_ids)),
            missing_candidate_class_ids=tuple(sorted(missing_candidate_class_ids)),
            candidate_generation_metadata_incomplete=metadata_incomplete,
        )

    def _score_candidate(
        self,
        candidate: SemanticCandidate,
        *,
        layout_region: SemanticLayoutRegion | None,
        text_region: SemanticTextRegion | None,
        text_block: SemanticTextBlock | None,
        snapshot_generation_signal_status: str | None,
    ) -> SemanticCandidate:
        candidate_class = candidate.candidate_class
        class_prior = _CLASS_PRIORS.get(candidate_class, 0.46)
        generation_confidence = candidate.confidence if candidate.confidence is not None else class_prior
        factors: dict[str, float] = {
            "class_prior": round(class_prior, 4),
            "generation_confidence": round(generation_confidence, 4),
        }
        explanations = [
            f"generation stage supplied a starting confidence of {generation_confidence:.2f}",
        ]
        score = generation_confidence

        score = _apply_signal_adjustment(
            score,
            factors=factors,
            explanations=explanations,
            factor_name="layout_region_adjustment",
            value=_confidence_adjustment(
                anchor=generation_confidence,
                source_confidence=None if layout_region is None else layout_region.confidence,
                weight=0.18,
            ),
            positive_explanation=(
                f"layout-region confidence ({layout_region.confidence:.2f}) strengthened the score"
                if layout_region is not None and layout_region.confidence is not None
                else None
            ),
            negative_explanation=(
                f"layout-region confidence ({layout_region.confidence:.2f}) softened the score"
                if layout_region is not None and layout_region.confidence is not None
                else None
            ),
        )
        score = _apply_signal_adjustment(
            score,
            factors=factors,
            explanations=explanations,
            factor_name="text_region_adjustment",
            value=_confidence_adjustment(
                anchor=generation_confidence,
                source_confidence=None if text_region is None else text_region.confidence,
                weight=0.08,
            ),
            positive_explanation=(
                f"text-region confidence ({text_region.confidence:.2f}) supported the score"
                if text_region is not None and text_region.confidence is not None
                else None
            ),
            negative_explanation=(
                f"text-region confidence ({text_region.confidence:.2f}) reduced the score"
                if text_region is not None and text_region.confidence is not None
                else None
            ),
        )
        score = _apply_signal_adjustment(
            score,
            factors=factors,
            explanations=explanations,
            factor_name="text_block_adjustment",
            value=_confidence_adjustment(
                anchor=generation_confidence,
                source_confidence=None if text_block is None else text_block.confidence,
                weight=0.14,
            ),
            positive_explanation=(
                f"text-block confidence ({text_block.confidence:.2f}) supported the score"
                if text_block is not None and text_block.confidence is not None
                else None
            ),
            negative_explanation=(
                f"text-block confidence ({text_block.confidence:.2f}) reduced the score"
                if text_block is not None and text_block.confidence is not None
                else None
            ),
        )

        semantic_role = _semantic_role_for(candidate, layout_region=layout_region)
        score = _apply_signal_adjustment(
            score,
            factors=factors,
            explanations=explanations,
            factor_name="semantic_role_alignment",
            value=_role_alignment_bonus(candidate_class, semantic_role=semantic_role),
            positive_explanation=(
                f"semantic role {semantic_role.value} aligned well with {candidate_class.value}"
                if candidate_class is not None and semantic_role is not None
                else None
            ),
            negative_explanation=None,
        )
        score = _apply_signal_adjustment(
            score,
            factors=factors,
            explanations=explanations,
            factor_name="heuristic_support_bonus",
            value=min(len(candidate.heuristic_explanations), 4) * 0.015,
            positive_explanation="multiple heuristic signals supported the score",
            negative_explanation=None,
        )
        score = _apply_signal_adjustment(
            score,
            factors=factors,
            explanations=explanations,
            factor_name="label_specificity_adjustment",
            value=_label_specificity_adjustment(
                candidate_class,
                candidate=candidate,
                label=candidate.label,
            ),
            positive_explanation="candidate label provided class-specific scoring support",
            negative_explanation="candidate label was less specific than the class prior expected",
        )

        signal_status = _signal_status(
            candidate,
            layout_region=layout_region,
            snapshot_generation_signal_status=snapshot_generation_signal_status,
        )
        score = _apply_signal_adjustment(
            score,
            factors=factors,
            explanations=explanations,
            factor_name="signal_status_adjustment",
            value=_SIGNAL_STATUS_ADJUSTMENTS.get(signal_status, _SIGNAL_STATUS_ADJUSTMENTS["partial"]),
            positive_explanation=None,
            negative_explanation=(
                f"signal status '{signal_status}' reduced certainty"
                if signal_status != "available"
                else None
            ),
        )

        missing_metadata_penalty, missing_metadata_explanations = _missing_metadata_penalty(
            candidate,
            layout_region=layout_region,
            text_region=text_region,
            text_block=text_block,
        )
        score = _apply_signal_adjustment(
            score,
            factors=factors,
            explanations=explanations,
            factor_name="missing_metadata_adjustment",
            value=missing_metadata_penalty,
            positive_explanation=None,
            negative_explanation=None,
        )
        explanations.extend(missing_metadata_explanations)

        final_score = round(_clamp(score, lower=0.0, upper=0.99), 4)
        score_factors = {name: round(value, 4) for name, value in factors.items()}
        score_explanations = tuple(dict.fromkeys(explanations))
        return replace(
            candidate,
            confidence=final_score,
            enabled=False,
            score_explanations=score_explanations,
            score_factors=score_factors,
            metadata={
                **dict(candidate.metadata),
                "candidate_scored": True,
                "candidate_scorer_name": self.scorer_name,
                "candidate_score": final_score,
                "candidate_generation_confidence": generation_confidence,
                "candidate_score_signal_status": signal_status,
                "candidate_score_explanations": score_explanations,
                "candidate_score_factors": score_factors,
                "candidate_score_contributing_factors": tuple(
                    factor_name
                    for factor_name, factor_value in score_factors.items()
                    if abs(factor_value) >= 0.01
                ),
                "observe_only": True,
                "analysis_only": True,
                "non_actionable_candidate": True,
            },
        )


def _lookup_region(
    layout_regions_by_id: Mapping[str, SemanticLayoutRegion],
    region_id: object,
) -> SemanticLayoutRegion | None:
    if not isinstance(region_id, str) or not region_id:
        return None
    return layout_regions_by_id.get(region_id)


def _lookup_text_region(
    text_regions_by_id: Mapping[str, SemanticTextRegion],
    region_id: object,
) -> SemanticTextRegion | None:
    if not isinstance(region_id, str) or not region_id:
        return None
    return text_regions_by_id.get(region_id)


def _lookup_text_block(
    text_blocks_by_id: Mapping[str, SemanticTextBlock],
    block_id: object,
) -> SemanticTextBlock | None:
    if not isinstance(block_id, str) or not block_id:
        return None
    return text_blocks_by_id.get(block_id)


def _average_score(candidates: tuple[SemanticCandidate, ...]) -> float | None:
    valid_scores = tuple(
        candidate.confidence
        for candidate in candidates
        if candidate.confidence is not None
    )
    if not valid_scores:
        return None
    return round(sum(valid_scores) / len(valid_scores), 4)


def _confidence_adjustment(
    *,
    anchor: float,
    source_confidence: float | None,
    weight: float,
) -> float:
    if source_confidence is None:
        return 0.0
    return (source_confidence - anchor) * weight


def _apply_signal_adjustment(
    score: float,
    *,
    factors: dict[str, float],
    explanations: list[str],
    factor_name: str,
    value: float,
    positive_explanation: str | None,
    negative_explanation: str | None,
) -> float:
    if abs(value) < 0.0005:
        return score
    factors[factor_name] = round(value, 4)
    if value > 0.0 and positive_explanation is not None:
        explanations.append(f"{positive_explanation} (+{value:.2f})")
    elif value < 0.0 and negative_explanation is not None:
        explanations.append(f"{negative_explanation} ({value:.2f})")
    return score + value


def _semantic_role_for(
    candidate: SemanticCandidate,
    *,
    layout_region: SemanticLayoutRegion | None,
) -> SemanticLayoutRole | None:
    if layout_region is not None:
        return layout_region.semantic_role
    semantic_role = candidate.metadata.get("semantic_layout_role")
    if not isinstance(semantic_role, str):
        return None
    try:
        return SemanticLayoutRole(semantic_role)
    except ValueError:
        return None


def _role_alignment_bonus(
    candidate_class: SemanticCandidateClass | None,
    *,
    semantic_role: SemanticLayoutRole | None,
) -> float:
    if candidate_class is None or semantic_role is None:
        return 0.0
    if candidate_class is SemanticCandidateClass.tab_like and semantic_role in {
        SemanticLayoutRole.navigation_header,
        SemanticLayoutRole.navigation_sidebar,
    }:
        return 0.1
    if candidate_class is SemanticCandidateClass.input_like and semantic_role in {
        SemanticLayoutRole.primary_content,
        SemanticLayoutRole.header_bar,
        SemanticLayoutRole.navigation_header,
    }:
        return 0.08
    if candidate_class is SemanticCandidateClass.close_like and semantic_role is SemanticLayoutRole.dialog_overlay:
        return 0.12
    if (
        candidate_class is SemanticCandidateClass.popup_dismiss_like
        and semantic_role is SemanticLayoutRole.dialog_overlay
    ):
        return 0.11
    if candidate_class is SemanticCandidateClass.button_like and semantic_role in {
        SemanticLayoutRole.dialog_overlay,
        SemanticLayoutRole.primary_content,
    }:
        return 0.07
    if candidate_class is SemanticCandidateClass.interactive_region_like and semantic_role in {
        SemanticLayoutRole.navigation_header,
        SemanticLayoutRole.navigation_sidebar,
        SemanticLayoutRole.sidebar_panel,
        SemanticLayoutRole.dialog_overlay,
    }:
        return 0.05
    return 0.0


def _label_specificity_adjustment(
    candidate_class: SemanticCandidateClass | None,
    *,
    candidate: SemanticCandidate,
    label: str,
) -> float:
    normalized_label = _normalize_text(label)
    tokens = _tokenize(label)
    if candidate_class is SemanticCandidateClass.tab_like:
        token_count = candidate.metadata.get("candidate_token_count")
        if isinstance(token_count, int) and token_count >= 2 and len(tokens) == 1:
            return 0.05
        if len(tokens) == 1:
            return 0.03
        return -0.02
    if candidate_class is SemanticCandidateClass.input_like:
        return 0.06 if any(hint in normalized_label for hint in _INPUT_HINTS) else -0.01
    if candidate_class is SemanticCandidateClass.close_like:
        return 0.07 if normalized_label in _CLOSE_HINTS else 0.02
    if candidate_class is SemanticCandidateClass.popup_dismiss_like:
        return 0.06 if any(hint in normalized_label for hint in _DISMISS_HINTS) else 0.02
    if candidate_class is SemanticCandidateClass.button_like:
        if normalized_label in _BUTTON_HINTS or len(tokens) <= 2:
            return 0.04
        return -0.02
    if candidate_class is SemanticCandidateClass.interactive_region_like:
        return 0.03 if len(tokens) <= 4 else 0.0
    return 0.0


def _signal_status(
    candidate: SemanticCandidate,
    *,
    layout_region: SemanticLayoutRegion | None,
    snapshot_generation_signal_status: str | None,
) -> str:
    if layout_region is not None:
        signal_status = layout_region.metadata.get("semantic_layout_signal_status")
        if isinstance(signal_status, str) and signal_status:
            return signal_status
    if snapshot_generation_signal_status is not None:
        return snapshot_generation_signal_status
    return "partial"


def _missing_metadata_penalty(
    candidate: SemanticCandidate,
    *,
    layout_region: SemanticLayoutRegion | None,
    text_region: SemanticTextRegion | None,
    text_block: SemanticTextBlock | None,
) -> tuple[float, tuple[str, ...]]:
    penalty = 0.0
    explanations: list[str] = []
    if candidate.metadata.get("source_layout_region_id") and layout_region is None:
        penalty -= 0.12
        explanations.append("missing source layout-region metadata reduced the score (-0.12)")
    if candidate.metadata.get("source_text_region_id") and text_region is None:
        penalty -= 0.05
        explanations.append("missing source text-region metadata reduced the score (-0.05)")
    if candidate.metadata.get("source_text_block_id") and text_block is None:
        penalty -= 0.07
        explanations.append("missing source text-block metadata reduced the score (-0.07)")
    if candidate.candidate_class is None:
        penalty -= 0.06
        explanations.append("missing candidate class metadata reduced the score (-0.06)")
    semantic_role = _semantic_role_for(candidate, layout_region=layout_region)
    if semantic_role is None:
        penalty -= 0.04
        explanations.append("missing semantic role metadata reduced the score (-0.04)")
    return penalty, tuple(explanations)


def _normalize_text(text: str) -> str:
    return " ".join(_tokenize(text))


def _tokenize(text: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in _TOKEN_SPLIT_PATTERN.split(text.lower())
        if token
    )


def _clamp(value: float, *, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
