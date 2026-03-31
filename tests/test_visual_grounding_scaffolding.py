from __future__ import annotations

from universal_visual_os_agent.geometry import NormalizedBBox
from universal_visual_os_agent.perception import (
    ObserveOnlyHeuristicVisualGroundingConfig,
    ObserveOnlyHeuristicVisualGroundingProvider,
    VisualGroundingAvailability,
    VisualGroundingRequest,
    VisualGroundingSupportStatus,
)


def test_visual_grounding_provider_infers_close_and_icon_cues() -> None:
    provider = ObserveOnlyHeuristicVisualGroundingProvider()

    result = provider.ground(
        VisualGroundingRequest(
            request_id="visual-grounding-close-1",
            subject_id="dialog-close",
            subject_bounds=NormalizedBBox(left=0.58, top=0.19, width=0.04, height=0.04),
            reference_bounds=NormalizedBBox(left=0.40, top=0.16, width=0.24, height=0.28),
            reference_role="dialog_overlay",
            label_hint="X",
        )
    )

    assert result.success is True
    assert result.assessment is not None
    assessment = result.assessment
    assert assessment.support_status is VisualGroundingSupportStatus.available
    assert assessment.reference_anchor.value == "top_right"
    assert "close_affordance_like" in {cue.value for cue in assessment.cue_kinds}
    assert "icon_like" in {cue.value for cue in assessment.cue_kinds}
    assert assessment.confidence is not None


def test_visual_grounding_provider_supports_partial_window_relative_grounding() -> None:
    provider = ObserveOnlyHeuristicVisualGroundingProvider()

    result = provider.ground(
        VisualGroundingRequest(
            request_id="visual-grounding-partial-1",
            subject_id="wide-input-region",
            subject_bounds=NormalizedBBox(left=0.28, top=0.28, width=0.28, height=0.08),
            label_hint="Search",
        )
    )

    assert result.success is True
    assert result.assessment is not None
    assessment = result.assessment
    assert assessment.support_status is VisualGroundingSupportStatus.partial
    assert assessment.window_anchor.value == "top_center"
    assert "input_affordance_like" in {cue.value for cue in assessment.cue_kinds}


def test_visual_grounding_provider_handles_unavailable_support_safely() -> None:
    provider = ObserveOnlyHeuristicVisualGroundingProvider(
        config=ObserveOnlyHeuristicVisualGroundingConfig(
            availability=VisualGroundingAvailability.unavailable
        )
    )

    result = provider.ground(
        VisualGroundingRequest(
            request_id="visual-grounding-unavailable-1",
            subject_id="dialog-close",
            subject_bounds=NormalizedBBox(left=0.58, top=0.19, width=0.04, height=0.04),
            reference_bounds=NormalizedBBox(left=0.40, top=0.16, width=0.24, height=0.28),
            reference_role="dialog_overlay",
        )
    )

    assert result.success is False
    assert result.error_code == "visual_grounding_unavailable"
