"""Semantic extraction input preparation from safe capture results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Self

from universal_visual_os_agent.perception.models import (
    CaptureResult,
    FrameImagePayload,
)

_VIRTUAL_DESKTOP_TARGET = "virtual_desktop"


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticSnapshotPreparation:
    """Metadata seed for a future semantic state snapshot."""

    observed_at: datetime
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticExtractionInput:
    """Prepared input for a semantic extraction step."""

    frame_id: str
    captured_at: datetime
    source: str
    capture_provider_name: str
    capture_target: str
    backend_name: str
    width: int
    height: int
    origin_x_px: int
    origin_y_px: int
    display_count: int
    payload: FrameImagePayload
    snapshot_preparation: SemanticSnapshotPreparation
    frame_metadata: Mapping[str, object] = field(default_factory=dict)
    capture_details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.frame_id:
            raise ValueError("frame_id must not be empty.")
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware.")
        if not self.source:
            raise ValueError("source must not be empty.")
        if not self.capture_provider_name:
            raise ValueError("capture_provider_name must not be empty.")
        if not self.capture_target:
            raise ValueError("capture_target must not be empty.")
        if not self.backend_name:
            raise ValueError("backend_name must not be empty.")
        if self.width <= 0:
            raise ValueError("width must be positive.")
        if self.height <= 0:
            raise ValueError("height must be positive.")
        if self.display_count <= 0:
            raise ValueError("display_count must be positive.")
        if self.payload.width != self.width:
            raise ValueError("payload width must match width.")
        if self.payload.height != self.height:
            raise ValueError("payload height must match height.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticExtractionPreparationResult:
    """Structured result for semantic extraction input preparation."""

    adapter_name: str
    success: bool
    extraction_input: SemanticExtractionInput | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.adapter_name:
            raise ValueError("adapter_name must not be empty.")
        if self.success and self.extraction_input is None:
            raise ValueError("Successful preparation results must include extraction_input.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed preparation results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful preparation results must not include error details.")
        if not self.success and self.extraction_input is not None:
            raise ValueError("Failed preparation results must not include extraction_input.")

    @classmethod
    def ok(
        cls,
        *,
        adapter_name: str,
        extraction_input: SemanticExtractionInput,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        """Build a successful preparation result."""

        return cls(
            adapter_name=adapter_name,
            success=True,
            extraction_input=extraction_input,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        adapter_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        """Build a failed preparation result."""

        return cls(
            adapter_name=adapter_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


class FullDesktopCaptureSemanticInputAdapter:
    """Prepare semantic extraction input from successful full-desktop capture results."""

    adapter_name = "FullDesktopCaptureSemanticInputAdapter"

    def prepare(self, capture_result: CaptureResult) -> SemanticExtractionPreparationResult:
        """Return semantic extraction input or a safe structured failure."""

        if not capture_result.success:
            return SemanticExtractionPreparationResult.failure(
                adapter_name=self.adapter_name,
                error_code="capture_failed",
                error_message=capture_result.error_message or "Capture did not succeed.",
                details={
                    "capture_error_code": capture_result.error_code,
                    "capture_provider_name": capture_result.provider_name,
                },
            )

        frame = capture_result.frame
        if frame is None:
            return SemanticExtractionPreparationResult.failure(
                adapter_name=self.adapter_name,
                error_code="frame_unavailable",
                error_message="Successful capture result is missing frame data.",
                details={"capture_provider_name": capture_result.provider_name},
            )

        if frame.payload is None:
            return SemanticExtractionPreparationResult.failure(
                adapter_name=self.adapter_name,
                error_code="frame_payload_unavailable",
                error_message="Semantic extraction requires an image payload.",
                details={
                    "frame_id": frame.frame_id,
                    "capture_provider_name": capture_result.provider_name,
                },
            )

        capture_target = _normalize_capture_target(capture_result.details.get("capture_target"))
        if capture_target != _VIRTUAL_DESKTOP_TARGET:
            return SemanticExtractionPreparationResult.failure(
                adapter_name=self.adapter_name,
                error_code="unsupported_capture_target",
                error_message="Semantic extraction input requires a successful virtual_desktop capture.",
                details={
                    "capture_target": capture_target,
                    "frame_id": frame.frame_id,
                },
            )

        missing_metadata_fields = _missing_frame_metadata_fields(frame.metadata)
        if missing_metadata_fields:
            return SemanticExtractionPreparationResult.failure(
                adapter_name=self.adapter_name,
                error_code="capture_metadata_unavailable",
                error_message="Capture metadata is incomplete for semantic extraction preparation.",
                details={
                    "frame_id": frame.frame_id,
                    "missing_metadata_fields": missing_metadata_fields,
                },
            )

        backend_name = frame.metadata["backend_name"]
        origin_x_px = frame.metadata["origin_x_px"]
        origin_y_px = frame.metadata["origin_y_px"]
        display_count = frame.metadata["display_count"]

        extraction_input = SemanticExtractionInput(
            frame_id=frame.frame_id,
            captured_at=frame.captured_at,
            source=frame.source,
            capture_provider_name=capture_result.provider_name,
            capture_target=capture_target,
            backend_name=backend_name,
            width=frame.width,
            height=frame.height,
            origin_x_px=origin_x_px,
            origin_y_px=origin_y_px,
            display_count=display_count,
            payload=frame.payload,
            snapshot_preparation=SemanticSnapshotPreparation(
                observed_at=frame.captured_at,
                metadata=_build_snapshot_metadata(
                    capture_result=capture_result,
                    backend_name=backend_name,
                    frame=frame,
                    capture_target=capture_target,
                    origin_x_px=origin_x_px,
                    origin_y_px=origin_y_px,
                    display_count=display_count,
                ),
            ),
            frame_metadata=dict(frame.metadata),
            capture_details=dict(capture_result.details),
        )
        return SemanticExtractionPreparationResult.ok(
            adapter_name=self.adapter_name,
            extraction_input=extraction_input,
            details={
                "frame_id": frame.frame_id,
                "backend_name": backend_name,
                "capture_target": capture_target,
            },
        )


def _build_snapshot_metadata(
    *,
    capture_result: CaptureResult,
    backend_name: str,
    frame,
    capture_target: str,
    origin_x_px: int,
    origin_y_px: int,
    display_count: int,
) -> dict[str, object]:
    snapshot_metadata: dict[str, object] = {
        "source_frame_id": frame.frame_id,
        "capture_provider_name": capture_result.provider_name,
        "capture_source": frame.source,
        "capture_target": capture_target,
        "capture_backend_name": backend_name,
        "capture_origin_x_px": origin_x_px,
        "capture_origin_y_px": origin_y_px,
        "display_count": display_count,
        "frame_width": frame.width,
        "frame_height": frame.height,
        "pixel_format": frame.payload.pixel_format.value,
    }
    for key in ("selected_backend_name", "used_backend_name", "backend_fallback_used"):
        value = capture_result.details.get(key)
        if isinstance(value, str | bool):
            snapshot_metadata[key] = value
    return snapshot_metadata


def _normalize_capture_target(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str) and enum_value:
        return enum_value
    return None


def _missing_frame_metadata_fields(frame_metadata: Mapping[str, object]) -> tuple[str, ...]:
    missing_fields: list[str] = []
    if not isinstance(frame_metadata.get("backend_name"), str) or not frame_metadata["backend_name"]:
        missing_fields.append("backend_name")
    if not isinstance(frame_metadata.get("origin_x_px"), int):
        missing_fields.append("origin_x_px")
    if not isinstance(frame_metadata.get("origin_y_px"), int):
        missing_fields.append("origin_y_px")
    display_count = frame_metadata.get("display_count")
    if not isinstance(display_count, int) or display_count <= 0:
        missing_fields.append("display_count")
    return tuple(missing_fields)
