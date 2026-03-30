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


class WindowsCaptureRuntimeMode(StrEnum):
    """Runtime architecture modes for the Windows capture stack."""

    production = "production"
    diagnostic = "diagnostic"


class WindowsCaptureBackendRole(StrEnum):
    """Architectural role for one Windows capture backend."""

    primary = "primary"
    fallback = "fallback"
    diagnostic_only = "diagnostic_only"


class WindowsCaptureBackendIntendedTarget(StrEnum):
    """Target type a backend is intended to serve in the runtime architecture."""

    virtual_desktop = "virtual_desktop"
    foreground_window = "foreground_window"
    generic = "generic"


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
class WindowsCaptureBackendPolicy:
    """Stable runtime-architecture metadata for one Windows capture backend."""

    backend_name: str
    role: WindowsCaptureBackendRole
    priority: int
    intended_target: WindowsCaptureBackendIntendedTarget
    diagnostic_only: bool = False
    description: str = ""
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.backend_name:
            raise ValueError("backend_name must not be empty.")
        if self.priority <= 0:
            raise ValueError("priority must be positive.")
        if self.role is WindowsCaptureBackendRole.diagnostic_only and not self.diagnostic_only:
            raise ValueError("diagnostic_only role must set diagnostic_only=True.")

    @property
    def primary(self) -> bool:
        """Whether this backend is the primary runtime path."""

        return self.role is WindowsCaptureBackendRole.primary

    @property
    def fallback(self) -> bool:
        """Whether this backend is a fallback path."""

        return self.role is WindowsCaptureBackendRole.fallback

    def to_summary(self) -> dict[str, object]:
        """Return a serializable policy summary."""

        return {
            "backend_name": self.backend_name,
            "role": self.role.value,
            "priority": self.priority,
            "intended_target": self.intended_target.value,
            "primary": self.primary,
            "fallback": self.fallback,
            "diagnostic_only": self.diagnostic_only,
            "description": self.description,
            "details": dict(self.details),
        }


@dataclass(slots=True, frozen=True, kw_only=True)
class WindowsCaptureBackendEvaluation:
    """Runtime-policy evaluation for one backend candidate."""

    backend_name: str
    role: WindowsCaptureBackendRole
    priority: int
    intended_target: WindowsCaptureBackendIntendedTarget
    primary: bool
    fallback: bool
    diagnostic_only: bool
    available: bool
    capability_reason: str
    runtime_eligible: bool
    selected: bool = False
    selection_reason: str | None = None
    skip_reason: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.backend_name:
            raise ValueError("backend_name must not be empty.")
        if self.priority <= 0:
            raise ValueError("priority must be positive.")
        if not self.capability_reason:
            raise ValueError("capability_reason must not be empty.")
        if self.selected and not self.runtime_eligible:
            raise ValueError("Selected backend evaluations must be runtime eligible.")
        if self.selected and self.selection_reason is None:
            raise ValueError("Selected backend evaluations must include selection_reason.")
        if not self.selected and self.skip_reason is None:
            raise ValueError("Skipped backend evaluations must include skip_reason.")

    def to_summary(self) -> dict[str, object]:
        """Return a serializable runtime evaluation summary."""

        return {
            "backend_name": self.backend_name,
            "role": self.role.value,
            "priority": self.priority,
            "intended_target": self.intended_target.value,
            "primary": self.primary,
            "fallback": self.fallback,
            "diagnostic_only": self.diagnostic_only,
            "available": self.available,
            "capability_reason": self.capability_reason,
            "runtime_eligible": self.runtime_eligible,
            "selected": self.selected,
            "selection_reason": self.selection_reason,
            "skip_reason": self.skip_reason,
            "details": dict(self.details),
        }


@dataclass(slots=True, frozen=True, kw_only=True)
class WindowsCaptureBackendSelection:
    """Backend selection report for one read-only capture request."""

    request_target: WindowsCaptureTarget
    runtime_mode: WindowsCaptureRuntimeMode
    candidates: tuple[WindowsCaptureBackendEvaluation, ...]
    available_backend_names: tuple[str, ...] = ()
    capability_available_backend_names: tuple[str, ...] = ()

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

    @property
    def selected_backend(self) -> WindowsCaptureBackendEvaluation | None:
        """Return the selected backend evaluation, if any."""

        selected_name = self.selected_backend_name
        if selected_name is None:
            return None
        for candidate in self.candidates:
            if candidate.backend_name == selected_name:
                return candidate
        return None

    def to_details(self) -> dict[str, object]:
        """Return a serializable selection summary."""

        selected_backend = self.selected_backend
        return {
            "capture_target": self.request_target,
            "runtime_mode": self.runtime_mode,
            "backend_candidates": tuple(candidate.to_summary() for candidate in self.candidates),
            "available_backend_names": self.available_backend_names,
            "capability_available_backend_names": self.capability_available_backend_names,
            "selected_backend_name": self.selected_backend_name,
            "selected_backend_role": (
                None if selected_backend is None else selected_backend.role.value
            ),
            "selected_backend_priority": (
                None if selected_backend is None else selected_backend.priority
            ),
            "selected_backend_intended_target": (
                None if selected_backend is None else selected_backend.intended_target.value
            ),
            "selected_backend_selection_reason": (
                None if selected_backend is None else selected_backend.selection_reason
            ),
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
