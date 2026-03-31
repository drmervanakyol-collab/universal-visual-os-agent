"""Structured observe-only visual-grounding contracts for non-text perception scaffolding."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.geometry.models import NormalizedBBox, NormalizedPoint


class VisualGroundingSupportStatus(StrEnum):
    """Availability/completeness states for non-text visual grounding support."""

    available = "available"
    partial = "partial"
    unavailable = "unavailable"


class VisualAnchor(StrEnum):
    """Stable anchor buckets for window-relative and region-relative grounding."""

    top_left = "top_left"
    top_center = "top_center"
    top_right = "top_right"
    center_left = "center_left"
    center = "center"
    center_right = "center_right"
    bottom_left = "bottom_left"
    bottom_center = "bottom_center"
    bottom_right = "bottom_right"


class VisualCueKind(StrEnum):
    """Structured non-text cue kinds exposed by heuristic visual grounding."""

    icon_like = "icon_like"
    close_affordance_like = "close_affordance_like"
    dialog_action_affordance_like = "dialog_action_affordance_like"
    navigation_affordance_like = "navigation_affordance_like"
    input_affordance_like = "input_affordance_like"
    status_affordance_like = "status_affordance_like"
    container_affordance_like = "container_affordance_like"


@dataclass(slots=True, frozen=True, kw_only=True)
class VisualGroundingRequest:
    """Compact request for observe-only visual grounding support."""

    request_id: str
    subject_id: str
    subject_bounds: NormalizedBBox
    window_bounds: NormalizedBBox = field(
        default_factory=lambda: NormalizedBBox(left=0.0, top=0.0, width=1.0, height=1.0)
    )
    reference_bounds: NormalizedBBox | None = None
    reference_role: str | None = None
    label_hint: str | None = None
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("request_id must not be empty.")
        if not self.subject_id:
            raise ValueError("subject_id must not be empty.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Visual grounding requests must remain safety-first and non-executing.")


@dataclass(slots=True, frozen=True, kw_only=True)
class VisualGroundingAssessment:
    """Structured non-text perception output for one grounded subject."""

    assessment_id: str
    request_id: str
    subject_id: str
    support_status: VisualGroundingSupportStatus
    window_anchor: VisualAnchor
    window_relative_center: NormalizedPoint
    window_area_ratio: float
    cue_kinds: tuple[VisualCueKind, ...] = ()
    confidence: float | None = None
    reference_anchor: VisualAnchor | None = None
    reference_relative_center: NormalizedPoint | None = None
    reference_area_ratio: float | None = None
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.assessment_id:
            raise ValueError("assessment_id must not be empty.")
        if not self.request_id:
            raise ValueError("request_id must not be empty.")
        if not self.subject_id:
            raise ValueError("subject_id must not be empty.")
        if not 0.0 <= self.window_area_ratio <= 1.0:
            raise ValueError("window_area_ratio must be between 0.0 and 1.0 inclusive.")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0 inclusive.")
        if self.reference_area_ratio is not None and not 0.0 <= self.reference_area_ratio <= 1.0:
            raise ValueError("reference_area_ratio must be between 0.0 and 1.0 inclusive.")
        if len(set(self.cue_kinds)) != len(self.cue_kinds):
            raise ValueError("cue_kinds must not contain duplicates.")
        if self.reference_anchor is None and self.reference_relative_center is not None:
            raise ValueError(
                "reference_relative_center requires reference_anchor when provided."
            )
        if self.reference_anchor is not None and self.reference_relative_center is None:
            raise ValueError(
                "reference_anchor requires reference_relative_center when provided."
            )
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Visual grounding assessments must remain safety-first.")


@dataclass(slots=True, frozen=True, kw_only=True)
class VisualGroundingResult:
    """Failure-safe result wrapper for observe-only visual grounding."""

    provider_name: str
    success: bool
    assessment: VisualGroundingAssessment | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.provider_name:
            raise ValueError("provider_name must not be empty.")
        if self.success and self.assessment is None:
            raise ValueError("Successful grounding results must include assessment.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed grounding results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful grounding results must not include error details.")
        if not self.success and self.assessment is not None:
            raise ValueError("Failed grounding results must not include assessment.")

    @classmethod
    def ok(
        cls,
        *,
        provider_name: str,
        assessment: VisualGroundingAssessment,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            provider_name=provider_name,
            success=True,
            assessment=assessment,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        provider_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            provider_name=provider_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )
