"""Backend protocols and runtime-selection helpers for Windows capture."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from universal_visual_os_agent.geometry import ScreenBBox
from universal_visual_os_agent.integrations.windows.capture_models import (
    RawWindowsCapture,
    WindowsCaptureBackendEvaluation,
    WindowsCaptureBackendCapability,
    WindowsCaptureBackendIntendedTarget,
    WindowsCaptureBackendPolicy,
    WindowsCaptureBackendRole,
    WindowsCaptureBackendSelection,
    WindowsCaptureRequest,
    WindowsCaptureRuntimeMode,
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


class WindowsCaptureRuntimePolicy(Protocol):
    """Contract for stable runtime architecture metadata and eligibility decisions."""

    def policy_for_backend(self, backend_name: str) -> WindowsCaptureBackendPolicy:
        """Return the architecture policy entry for one backend."""


@dataclass(slots=True, frozen=True)
class DefaultWindowsCaptureRuntimePolicy:
    """Built-in runtime architecture for the existing Windows capture stack."""

    def policy_for_backend(self, backend_name: str) -> WindowsCaptureBackendPolicy:
        if backend_name == "dxcam_desktop":
            return WindowsCaptureBackendPolicy(
                backend_name=backend_name,
                role=WindowsCaptureBackendRole.primary,
                priority=100,
                intended_target=WindowsCaptureBackendIntendedTarget.virtual_desktop,
                diagnostic_only=False,
                description="Primary DXcam/DXGI full-desktop runtime path.",
            )
        if backend_name == "desktop_duplication_dxgi":
            return WindowsCaptureBackendPolicy(
                backend_name=backend_name,
                role=WindowsCaptureBackendRole.fallback,
                priority=150,
                intended_target=WindowsCaptureBackendIntendedTarget.virtual_desktop,
                diagnostic_only=False,
                description="DXGI desktop duplication candidate reserved for future full-desktop runtime use.",
            )
        if backend_name == "gdi_bitblt":
            return WindowsCaptureBackendPolicy(
                backend_name=backend_name,
                role=WindowsCaptureBackendRole.fallback,
                priority=200,
                intended_target=WindowsCaptureBackendIntendedTarget.virtual_desktop,
                diagnostic_only=True,
                description="Diagnostic and compatibility BitBlt fallback for full-desktop capture only.",
            )
        if backend_name == "printwindow_foreground":
            return WindowsCaptureBackendPolicy(
                backend_name=backend_name,
                role=WindowsCaptureBackendRole.diagnostic_only,
                priority=100,
                intended_target=WindowsCaptureBackendIntendedTarget.foreground_window,
                diagnostic_only=True,
                description="Limited diagnostic PrintWindow path for the current foreground window only.",
            )
        return WindowsCaptureBackendPolicy(
            backend_name=backend_name,
            role=WindowsCaptureBackendRole.fallback,
            priority=900,
            intended_target=WindowsCaptureBackendIntendedTarget.generic,
            diagnostic_only=False,
            description="Explicit custom backend outside the built-in Windows runtime architecture registry.",
        )


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
    *,
    runtime_mode: WindowsCaptureRuntimeMode = WindowsCaptureRuntimeMode.production,
    runtime_policy: WindowsCaptureRuntimePolicy | None = None,
) -> WindowsCaptureBackendSelection:
    """Return a safe backend-selection report for the request."""

    resolved_runtime_policy = (
        DefaultWindowsCaptureRuntimePolicy()
        if runtime_policy is None
        else runtime_policy
    )
    raw_entries: list[tuple[int, WindowsCaptureBackendCapability, WindowsCaptureBackendPolicy]] = []
    capability_available_backend_names: list[str] = []

    for index, backend in enumerate(backends):
        backend_name = getattr(backend, "backend_name", type(backend).__name__)
        backend_policy = resolved_runtime_policy.policy_for_backend(backend_name)
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
        if capability.available:
            capability_available_backend_names.append(capability.backend_name)
        raw_entries.append((index, capability, backend_policy))

    ordered_entries = sorted(
        raw_entries,
        key=lambda item: (item[2].priority, item[0], item[1].backend_name),
    )
    selected_backend_name: str | None = None
    candidates: list[WindowsCaptureBackendEvaluation] = []
    available_backend_names: list[str] = []

    for _, capability, backend_policy in ordered_entries:
        runtime_eligible, skip_reason = _runtime_eligibility(
            backend_policy=backend_policy,
            capability=capability,
            request=request,
            runtime_mode=runtime_mode,
        )
        if runtime_eligible:
            available_backend_names.append(capability.backend_name)
        selected = runtime_eligible and selected_backend_name is None
        if selected:
            selected_backend_name = capability.backend_name
        candidates.append(
            WindowsCaptureBackendEvaluation(
                backend_name=capability.backend_name,
                role=backend_policy.role,
                priority=backend_policy.priority,
                intended_target=backend_policy.intended_target,
                primary=backend_policy.primary,
                fallback=backend_policy.fallback,
                diagnostic_only=backend_policy.diagnostic_only,
                available=capability.available,
                capability_reason=capability.reason,
                runtime_eligible=runtime_eligible,
                selected=selected,
                selection_reason=(
                    None
                    if not selected
                    else _selection_reason(
                        backend_policy=backend_policy,
                        request=request,
                        runtime_mode=runtime_mode,
                    )
                ),
                skip_reason=(
                    None
                    if selected
                    else _skip_reason(
                        capability=capability,
                        backend_policy=backend_policy,
                        runtime_eligible=runtime_eligible,
                        runtime_skip_reason=skip_reason,
                        selected_backend_name=selected_backend_name,
                    )
                ),
                details={
                    **backend_policy.to_summary(),
                    **dict(capability.details),
                },
            )
        )

    return WindowsCaptureBackendSelection(
        request_target=request.target,
        runtime_mode=runtime_mode,
        candidates=tuple(candidates),
        available_backend_names=tuple(available_backend_names),
        capability_available_backend_names=tuple(capability_available_backend_names),
    )


def _runtime_eligibility(
    *,
    backend_policy: WindowsCaptureBackendPolicy,
    capability: WindowsCaptureBackendCapability,
    request: WindowsCaptureRequest,
    runtime_mode: WindowsCaptureRuntimeMode,
) -> tuple[bool, str | None]:
    if not capability.available:
        return False, capability.reason
    if (
        backend_policy.intended_target
        is WindowsCaptureBackendIntendedTarget.virtual_desktop
        and request.target is not WindowsCaptureTarget.virtual_desktop
    ):
        return False, "Backend is intended for virtual_desktop capture only."
    if (
        backend_policy.intended_target
        is WindowsCaptureBackendIntendedTarget.foreground_window
        and request.target is not WindowsCaptureTarget.foreground_window
    ):
        return False, "Backend is intended for foreground_window capture only."
    if (
        backend_policy.diagnostic_only
        and runtime_mode is WindowsCaptureRuntimeMode.production
    ):
        return (
            False,
            "Diagnostic-only backend is disabled in the production capture runtime.",
        )
    return True, None


def _selection_reason(
    *,
    backend_policy: WindowsCaptureBackendPolicy,
    request: WindowsCaptureRequest,
    runtime_mode: WindowsCaptureRuntimeMode,
) -> str:
    if (
        backend_policy.role is WindowsCaptureBackendRole.primary
        and request.target is WindowsCaptureTarget.virtual_desktop
        and runtime_mode is WindowsCaptureRuntimeMode.production
    ):
        return "Selected as the primary production full-desktop backend."
    if backend_policy.backend_name == "printwindow_foreground":
        return "Selected as the diagnostic foreground-window backend."
    if backend_policy.diagnostic_only:
        return "Selected as the highest-priority diagnostic-compatible backend."
    return "Selected as the highest-priority runtime-eligible backend."


def _skip_reason(
    *,
    capability: WindowsCaptureBackendCapability,
    backend_policy: WindowsCaptureBackendPolicy,
    runtime_eligible: bool,
    runtime_skip_reason: str | None,
    selected_backend_name: str | None,
) -> str:
    if not capability.available:
        return capability.reason
    if not runtime_eligible and runtime_skip_reason is not None:
        return runtime_skip_reason
    if selected_backend_name is not None:
        return "A higher-priority runtime-eligible backend was selected first."
    return (
        "Backend was not selected by the current runtime policy."
        if backend_policy.diagnostic_only
        else "Backend was not selected."
    )
