"""Shared models for read-only Windows capture backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.geometry import ScreenBBox
from universal_visual_os_agent.perception import FramePixelFormat


class WindowsCaptureTarget(StrEnum):
    """Read-only capture targets supported by Windows capture backends."""

    virtual_desktop = "virtual_desktop"
    foreground_window = "foreground_window"


class WindowsCaptureUnavailableError(RuntimeError):
    """Raised when Windows screen capture APIs are unavailable."""


class WindowsCaptureStageError(RuntimeError):
    """Structured low-level capture failure with diagnostics."""

    def __init__(
        self,
        *,
        stage: str,
        message: str,
        win32_error_code: int | None = None,
        diagnostics: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.win32_error_code = win32_error_code
        self.diagnostics = {} if diagnostics is None else dict(diagnostics)


@dataclass(slots=True, frozen=True, kw_only=True)
class WindowsCaptureRequest:
    """Structured request for a safe read-only capture backend."""

    target: WindowsCaptureTarget = WindowsCaptureTarget.virtual_desktop
    bounds: ScreenBBox | None = None
    window_handle: int | None = None

    def __post_init__(self) -> None:
        if self.target is WindowsCaptureTarget.virtual_desktop and self.bounds is None:
            raise ValueError("virtual_desktop capture requires bounds.")
        if self.window_handle is not None and self.window_handle <= 0:
            raise ValueError("window_handle must be positive when provided.")


@dataclass(slots=True, frozen=True, kw_only=True)
class WindowsCaptureBackendCapability:
    """Availability report for one Windows capture backend."""

    backend_name: str
    available: bool
    reason: str
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.backend_name:
            raise ValueError("backend_name must not be empty.")
        if not self.reason:
            raise ValueError("reason must not be empty.")

    @classmethod
    def available_backend(
        cls,
        *,
        backend_name: str,
        reason: str = "Backend is available for the current request.",
        details: Mapping[str, object] | None = None,
    ) -> Self:
        """Build an available capability report."""

        return cls(
            backend_name=backend_name,
            available=True,
            reason=reason,
            details={} if details is None else details,
        )

    @classmethod
    def unavailable_backend(
        cls,
        *,
        backend_name: str,
        reason: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        """Build an unavailable capability report."""

        return cls(
            backend_name=backend_name,
            available=False,
            reason=reason,
            details={} if details is None else details,
        )

    def to_summary(self) -> dict[str, object]:
        """Return a serializable capability summary."""

        return {
            "backend_name": self.backend_name,
            "available": self.available,
            "reason": self.reason,
            "details": dict(self.details),
        }


@dataclass(slots=True, frozen=True, kw_only=True)
class WindowsCaptureBackendSelection:
    """Backend selection report for one read-only capture request."""

    request_target: WindowsCaptureTarget
    candidates: tuple[WindowsCaptureBackendCapability, ...]
    available_backend_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        candidate_names = tuple(candidate.backend_name for candidate in self.candidates)
        if len(set(candidate_names)) != len(candidate_names):
            raise ValueError("Backend candidate names must be unique.")
        for backend_name in self.available_backend_names:
            if backend_name not in candidate_names:
                raise ValueError("available_backend_names must be drawn from candidates.")

    @property
    def selected_backend_name(self) -> str | None:
        """Return the first available backend name, if any."""

        return None if not self.available_backend_names else self.available_backend_names[0]

    def to_details(self) -> dict[str, object]:
        """Return a serializable selection summary."""

        return {
            "capture_target": self.request_target,
            "backend_candidates": tuple(candidate.to_summary() for candidate in self.candidates),
            "available_backend_names": self.available_backend_names,
            "selected_backend_name": self.selected_backend_name,
        }


@dataclass(slots=True, frozen=True, kw_only=True)
class RawWindowsCapture:
    """Raw image data captured from the Windows desktop."""

    width: int
    height: int
    origin_x_px: int
    origin_y_px: int
    row_stride_bytes: int
    image_bytes: bytes
    pixel_format: FramePixelFormat = FramePixelFormat.bgra_8888
    captured_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("width must be positive.")
        if self.height <= 0:
            raise ValueError("height must be positive.")
        if self.row_stride_bytes <= 0:
            raise ValueError("row_stride_bytes must be positive.")
        expected_length = self.row_stride_bytes * self.height
        if len(self.image_bytes) != expected_length:
            raise ValueError("image_bytes length must match row_stride_bytes * height.")
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware.")
