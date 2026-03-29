"""Backend protocols and selection helpers for Windows capture."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from universal_visual_os_agent.geometry import ScreenBBox
from universal_visual_os_agent.integrations.windows.capture_models import (
    RawWindowsCapture,
    WindowsCaptureBackendCapability,
    WindowsCaptureBackendSelection,
    WindowsCaptureRequest,
    WindowsCaptureStageError,
    WindowsCaptureTarget,
)


class WindowsScreenCaptureApi(Protocol):
    """Legacy bounds-based capture API for virtual desktop requests."""

    def capture_bounds(self, bounds: ScreenBBox) -> RawWindowsCapture:
        """Capture the provided bounds from the current virtual desktop."""


class WindowsCaptureBackend(Protocol):
    """Read-only Windows capture backend contract."""

    backend_name: str

    def detect_capability(self, request: WindowsCaptureRequest) -> WindowsCaptureBackendCapability:
        """Report whether this backend can safely handle the request."""

    def capture(self, request: WindowsCaptureRequest) -> RawWindowsCapture:
        """Perform a read-only capture for the request."""


@dataclass(slots=True)
class BoundsCaptureApiBackendAdapter:
    """Wrap a legacy bounds-based capture API as a backend strategy."""

    capture_api: WindowsScreenCaptureApi
    backend_name: str = "legacy_bounds_capture_api"

    def detect_capability(self, request: WindowsCaptureRequest) -> WindowsCaptureBackendCapability:
        if request.target is not WindowsCaptureTarget.virtual_desktop:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Legacy bounds capture only supports virtual_desktop requests.",
                details={"target": request.target},
            )
        if request.bounds is None:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Virtual desktop bounds are required.",
            )
        return WindowsCaptureBackendCapability.available_backend(
            backend_name=self.backend_name,
            details={"target": request.target},
        )

    def capture(self, request: WindowsCaptureRequest) -> RawWindowsCapture:
        if request.bounds is None:
            raise WindowsCaptureStageError(
                stage="validate_bounds",
                message="Virtual desktop bounds are required.",
            )
        return self.capture_api.capture_bounds(request.bounds)


def select_capture_backends(
    backends: tuple[WindowsCaptureBackend, ...],
    request: WindowsCaptureRequest,
) -> WindowsCaptureBackendSelection:
    """Return a safe backend-selection report for the request."""

    candidates: list[WindowsCaptureBackendCapability] = []
    available_backend_names: list[str] = []

    for backend in backends:
        backend_name = getattr(backend, "backend_name", type(backend).__name__)
        try:
            capability = backend.detect_capability(request)
        except Exception as exc:  # noqa: BLE001 - selection must stay failure-safe
            capability = WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=backend_name,
                reason="Capability detection raised an exception.",
                details={
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )
        candidates.append(capability)
        if capability.available:
            available_backend_names.append(capability.backend_name)

    return WindowsCaptureBackendSelection(
        request_target=request.target,
        candidates=tuple(candidates),
        available_backend_names=tuple(available_backend_names),
    )
