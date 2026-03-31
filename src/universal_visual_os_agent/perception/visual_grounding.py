"""Observe-only heuristic visual-grounding support for non-text perception scaffolding."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from universal_visual_os_agent.geometry.models import NormalizedBBox, NormalizedPoint
from universal_visual_os_agent.perception.visual_grounding_models import (
    VisualAnchor,
    VisualCueKind,
    VisualGroundingAssessment,
    VisualGroundingRequest,
    VisualGroundingResult,
    VisualGroundingSupportStatus,
)

_DIALOG_ROLES = frozenset({"dialog_overlay"})
_NAVIGATION_ROLES = frozenset(
    {
        "navigation_header",
        "navigation_sidebar",
        "header_bar",
        "sidebar_panel",
    }
)
_INPUT_ROLES = frozenset(
    {
        "primary_content",
        "header_bar",
        "navigation_header",
    }
)
_STATUS_ROLES = frozenset({"status_footer", "footer_bar"})
_CONTAINER_ROLES = frozenset(
    {
        "navigation_header",
        "navigation_sidebar",
        "sidebar_panel",
        "dialog_overlay",
    }
)


class VisualGroundingAvailability(StrEnum):
    """Availability states for the heuristic visual-grounding provider."""

    available = "available"
    unavailable = "unavailable"


@dataclass(slots=True, frozen=True, kw_only=True)
class ObserveOnlyHeuristicVisualGroundingConfig:
    """Deterministic thresholds for compact observe-only visual grounding."""

    availability: VisualGroundingAvailability = VisualGroundingAvailability.available
    icon_max_window_area: float = 0.02
    close_max_reference_area: float = 0.08
    dialog_action_max_reference_area: float = 0.22
    input_min_aspect_ratio: float = 2.4
    input_max_window_area: float = 0.20
    status_min_aspect_ratio: float = 2.0
    container_min_window_area: float = 0.12
    observe_only: bool = True
    read_only: bool = True
    non_executing: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "icon_max_window_area",
            "close_max_reference_area",
            "dialog_action_max_reference_area",
            "input_min_aspect_ratio",
            "input_max_window_area",
            "status_min_aspect_ratio",
            "container_min_window_area",
        ):
            value = getattr(self, field_name)
            if value <= 0.0:
                raise ValueError(f"{field_name} must be positive.")
        if not self.observe_only or not self.read_only or not self.non_executing:
            raise ValueError("Visual grounding config must remain safety-first and non-executing.")


class ObserveOnlyHeuristicVisualGroundingProvider:
    """Infer structured non-text visual cues from normalized geometry only."""

    provider_name = "ObserveOnlyHeuristicVisualGroundingProvider"

    def __init__(
        self,
        *,
        config: ObserveOnlyHeuristicVisualGroundingConfig | None = None,
    ) -> None:
        self._config = (
            ObserveOnlyHeuristicVisualGroundingConfig()
            if config is None
            else config
        )

    @property
    def availability(self) -> VisualGroundingAvailability:
        """Return the explicit provider availability state."""

        return self._config.availability

    def ground(self, request: VisualGroundingRequest) -> VisualGroundingResult:
        if self._config.availability is not VisualGroundingAvailability.available:
            return VisualGroundingResult.failure(
                provider_name=self.provider_name,
                error_code="visual_grounding_unavailable",
                error_message="Visual grounding support is unavailable.",
                details={"request_id": request.request_id, "subject_id": request.subject_id},
            )
        try:
            window_relative_center, window_clamped = _relative_center(
                subject_bounds=request.subject_bounds,
                reference_bounds=request.window_bounds,
            )
            window_area_ratio = _area_ratio(
                subject_bounds=request.subject_bounds,
                reference_bounds=request.window_bounds,
            )
            window_anchor = _anchor_for_point(window_relative_center)

            reference_anchor: VisualAnchor | None = None
            reference_relative_center: NormalizedPoint | None = None
            reference_area_ratio: float | None = None
            reference_clamped = False
            support_status = VisualGroundingSupportStatus.available
            if request.reference_bounds is None or request.reference_role is None:
                support_status = VisualGroundingSupportStatus.partial
            else:
                reference_relative_center, reference_clamped = _relative_center(
                    subject_bounds=request.subject_bounds,
                    reference_bounds=request.reference_bounds,
                )
                reference_area_ratio = _area_ratio(
                    subject_bounds=request.subject_bounds,
                    reference_bounds=request.reference_bounds,
                )
                reference_anchor = _anchor_for_point(reference_relative_center)
                if reference_clamped:
                    support_status = VisualGroundingSupportStatus.partial

            cue_kinds = _infer_cue_kinds(
                config=self._config,
                request=request,
                window_anchor=window_anchor,
                window_area_ratio=window_area_ratio,
                reference_anchor=reference_anchor,
                reference_relative_center=reference_relative_center,
                reference_area_ratio=reference_area_ratio,
            )
            confidence = _confidence_for_cues(
                cue_kinds=cue_kinds,
                support_status=support_status,
            )
            assessment = VisualGroundingAssessment(
                assessment_id=f"{request.request_id}:visual_grounding",
                request_id=request.request_id,
                subject_id=request.subject_id,
                support_status=support_status,
                window_anchor=window_anchor,
                window_relative_center=window_relative_center,
                window_area_ratio=round(window_area_ratio, 6),
                cue_kinds=cue_kinds,
                confidence=confidence,
                reference_anchor=reference_anchor,
                reference_relative_center=reference_relative_center,
                reference_area_ratio=(
                    None if reference_area_ratio is None else round(reference_area_ratio, 6)
                ),
                metadata={
                    "provider_name": self.provider_name,
                    "availability": self._config.availability.value,
                    "reference_role": request.reference_role,
                    "label_hint": request.label_hint,
                    "window_relative_center_clamped": window_clamped,
                    "reference_relative_center_clamped": reference_clamped,
                    "cue_count": len(cue_kinds),
                    "observe_only": True,
                    "read_only": True,
                    "non_executing": True,
                },
            )
        except Exception as exc:  # noqa: BLE001 - grounding must remain failure-safe
            return VisualGroundingResult.failure(
                provider_name=self.provider_name,
                error_code="visual_grounding_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )
        return VisualGroundingResult.ok(
            provider_name=self.provider_name,
            assessment=assessment,
            details={
                "support_status": assessment.support_status.value,
                "cue_kinds": tuple(cue.value for cue in assessment.cue_kinds),
                "window_anchor": assessment.window_anchor.value,
                "reference_anchor": (
                    None if assessment.reference_anchor is None else assessment.reference_anchor.value
                ),
            },
        )


def _infer_cue_kinds(
    *,
    config: ObserveOnlyHeuristicVisualGroundingConfig,
    request: VisualGroundingRequest,
    window_anchor: VisualAnchor,
    window_area_ratio: float,
    reference_anchor: VisualAnchor | None,
    reference_relative_center: NormalizedPoint | None,
    reference_area_ratio: float | None,
) -> tuple[VisualCueKind, ...]:
    cue_kinds: list[VisualCueKind] = []
    aspect_ratio = request.subject_bounds.width / max(request.subject_bounds.height, 0.0001)
    reference_role = request.reference_role

    if 0.75 <= aspect_ratio <= 1.35 and window_area_ratio <= config.icon_max_window_area:
        cue_kinds.append(VisualCueKind.icon_like)

    if (
        reference_role in _DIALOG_ROLES
        and reference_relative_center is not None
        and reference_relative_center.x >= 0.78
        and reference_relative_center.y <= 0.42
        and reference_area_ratio is not None
        and reference_area_ratio <= config.close_max_reference_area
    ):
        cue_kinds.append(VisualCueKind.close_affordance_like)

    if (
        reference_role in _DIALOG_ROLES
        and reference_relative_center is not None
        and reference_relative_center.y >= 0.45
        and reference_area_ratio is not None
        and reference_area_ratio <= config.dialog_action_max_reference_area
    ):
        cue_kinds.append(VisualCueKind.dialog_action_affordance_like)

    if reference_role in _NAVIGATION_ROLES:
        cue_kinds.append(VisualCueKind.navigation_affordance_like)

    if (
        aspect_ratio >= config.input_min_aspect_ratio
        and window_area_ratio <= config.input_max_window_area
        and (
            reference_role in _INPUT_ROLES
            or window_anchor in {
                VisualAnchor.top_center,
                VisualAnchor.center_left,
                VisualAnchor.center,
                VisualAnchor.center_right,
            }
        )
    ):
        cue_kinds.append(VisualCueKind.input_affordance_like)

    if (
        reference_role in _STATUS_ROLES
        and aspect_ratio >= config.status_min_aspect_ratio
    ):
        cue_kinds.append(VisualCueKind.status_affordance_like)

    if (
        reference_role in _CONTAINER_ROLES
        and window_area_ratio >= config.container_min_window_area
    ):
        cue_kinds.append(VisualCueKind.container_affordance_like)

    return tuple(dict.fromkeys(cue_kinds))


def _confidence_for_cues(
    *,
    cue_kinds: tuple[VisualCueKind, ...],
    support_status: VisualGroundingSupportStatus,
) -> float | None:
    if not cue_kinds:
        return None
    confidence = max(
        {
            VisualCueKind.icon_like: 0.58,
            VisualCueKind.close_affordance_like: 0.82,
            VisualCueKind.dialog_action_affordance_like: 0.74,
            VisualCueKind.navigation_affordance_like: 0.72,
            VisualCueKind.input_affordance_like: 0.76,
            VisualCueKind.status_affordance_like: 0.7,
            VisualCueKind.container_affordance_like: 0.66,
        }[cue]
        for cue in cue_kinds
    )
    if support_status is VisualGroundingSupportStatus.partial:
        confidence = max(0.0, confidence - 0.08)
    return round(min(0.99, confidence), 4)


def _relative_center(
    *,
    subject_bounds: NormalizedBBox,
    reference_bounds: NormalizedBBox,
) -> tuple[NormalizedPoint, bool]:
    center_x = subject_bounds.left + (subject_bounds.width / 2.0)
    center_y = subject_bounds.top + (subject_bounds.height / 2.0)
    relative_x = (center_x - reference_bounds.left) / max(reference_bounds.width, 0.0001)
    relative_y = (center_y - reference_bounds.top) / max(reference_bounds.height, 0.0001)
    clamped_x = _clamp(relative_x)
    clamped_y = _clamp(relative_y)
    return (
        NormalizedPoint(x=clamped_x, y=clamped_y),
        clamped_x != relative_x or clamped_y != relative_y,
    )


def _area_ratio(
    *,
    subject_bounds: NormalizedBBox,
    reference_bounds: NormalizedBBox,
) -> float:
    reference_area = max(reference_bounds.width * reference_bounds.height, 0.0001)
    return _clamp((subject_bounds.width * subject_bounds.height) / reference_area)


def _anchor_for_point(point: NormalizedPoint) -> VisualAnchor:
    horizontal = _horizontal_bucket(point.x)
    vertical = _vertical_bucket(point.y)
    if vertical == "center" and horizontal == "center":
        return VisualAnchor.center
    return VisualAnchor(f"{vertical}_{horizontal}")


def _horizontal_bucket(value: float) -> str:
    if value < 0.33:
        return "left"
    if value > 0.67:
        return "right"
    return "center"


def _vertical_bucket(value: float) -> str:
    if value < 0.33:
        return "top"
    if value > 0.67:
        return "bottom"
    return "center"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
