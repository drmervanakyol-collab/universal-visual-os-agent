"""Perception model types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Mapping


class FramePixelFormat(StrEnum):
    """Supported frame payload pixel formats."""

    bgra_8888 = "bgra_8888"

    @property
    def bytes_per_pixel(self) -> int:
        """Return the byte width of a single pixel for this format."""

        return 4


@dataclass(slots=True, frozen=True, kw_only=True)
class FrameImagePayload:
    """Image payload captured from a read-only screen source."""

    width: int
    height: int
    row_stride_bytes: int
    image_bytes: bytes
    pixel_format: FramePixelFormat = FramePixelFormat.bgra_8888

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("width must be positive.")
        if self.height <= 0:
            raise ValueError("height must be positive.")
        minimum_stride = self.width * self.pixel_format.bytes_per_pixel
        if self.row_stride_bytes < minimum_stride:
            raise ValueError("row_stride_bytes must cover at least one full row of pixels.")
        expected_length = self.row_stride_bytes * self.height
        if len(self.image_bytes) != expected_length:
            raise ValueError("image_bytes length must match row_stride_bytes * height.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CapturedFrame:
    """Metadata for an observed frame."""

    frame_id: str
    width: int
    height: int
    captured_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    payload: FrameImagePayload | None = None
    source: str = "unknown"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.frame_id:
            raise ValueError("frame_id must not be empty.")
        if self.width <= 0:
            raise ValueError("width must be positive.")
        if self.height <= 0:
            raise ValueError("height must be positive.")
        if self.source == "":
            raise ValueError("source must not be empty.")
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware.")
        if self.payload is not None:
            if self.payload.width != self.width:
                raise ValueError("payload width must match frame width.")
            if self.payload.height != self.height:
                raise ValueError("payload height must match frame height.")


@dataclass(slots=True, frozen=True, kw_only=True)
class CaptureResult:
    """Structured result for safe observe-only capture attempts."""

    provider_name: str
    success: bool
    frame: CapturedFrame | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.provider_name:
            raise ValueError("provider_name must not be empty.")
        if self.success and self.frame is None:
            raise ValueError("Successful capture results must include frame data.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed capture results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful capture results must not include error details.")
        if not self.success and self.frame is not None:
            raise ValueError("Failed capture results must not include frame data.")

    @classmethod
    def ok(
        cls,
        *,
        provider_name: str,
        frame: CapturedFrame,
        details: Mapping[str, object] | None = None,
    ) -> CaptureResult:
        """Build a successful capture result."""

        return cls(
            provider_name=provider_name,
            success=True,
            frame=frame,
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
    ) -> CaptureResult:
        """Build a failed capture result."""

        return cls(
            provider_name=provider_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )
