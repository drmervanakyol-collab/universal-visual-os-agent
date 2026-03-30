"""Windows integration exports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

_EXPORT_MODULES = {
    ".capture": ("WindowsObserveOnlyCaptureProvider",),
    ".capture_backends": (
        "DefaultWindowsCaptureRuntimePolicy",
        "WindowsCaptureBackend",
        "WindowsCaptureRuntimePolicy",
        "WindowsScreenCaptureApi",
        "select_capture_backends",
    ),
    ".capture_desktop_duplication": ("WindowsDesktopDuplicationCaptureBackend",),
    ".capture_dxcam": ("WindowsDxcamCaptureBackend",),
    ".capture_gdi": (
        "CtypesWindowsScreenCaptureApi",
        "WindowsGdiCaptureBackend",
    ),
    ".capture_models": (
        "RawWindowsCapture",
        "WindowsCaptureBackendCapability",
        "WindowsCaptureBackendEvaluation",
        "WindowsCaptureBackendIntendedTarget",
        "WindowsCaptureBackendPolicy",
        "WindowsCaptureBackendRole",
        "WindowsCaptureBackendSelection",
        "WindowsCaptureRequest",
        "WindowsCaptureRuntimeMode",
        "WindowsCaptureStageError",
        "WindowsCaptureTarget",
        "WindowsCaptureUnavailableError",
    ),
    ".capture_printwindow": ("WindowsForegroundWindowPrintCaptureBackend",),
    ".click": ("WindowsUser32ClickTransport",),
    ".dxcam_capture_diagnostic": (
        "DxcamBackendAttemptDiagnostic",
        "DxcamCaptureDiagnosticResult",
        "run_dxcam_capture_diagnostic",
    ),
    ".foreground_capture_diagnostic": (
        "ForegroundCaptureDiagnosticResult",
        "ForegroundWindowMetadata",
        "ForegroundWindowMetadataReader",
        "ForegroundWindowMetadataResult",
        "WindowsForegroundWindowMetadataReader",
        "run_foreground_window_capture_diagnostic",
    ),
    ".screen_metrics": (
        "CtypesWindowsMonitorApi",
        "RawWindowsMonitorMetrics",
        "WindowsApiUnavailableError",
        "WindowsMonitorApi",
        "WindowsScreenMetricsProvider",
    ),
}
_EXPORTS = {
    name: module_name
    for module_name, names in _EXPORT_MODULES.items()
    for name in names
}

__all__ = tuple(name for names in _EXPORT_MODULES.values() for name in names)


def __getattr__(name: str) -> object:
    """Lazily resolve Windows integration exports to keep the facade import-light."""

    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name, __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return a stable view of module globals plus lazy exports."""

    return sorted((*globals(), *__all__))


if TYPE_CHECKING:
    from .capture import WindowsObserveOnlyCaptureProvider
    from .capture_backends import (
        DefaultWindowsCaptureRuntimePolicy,
        WindowsCaptureBackend,
        WindowsCaptureRuntimePolicy,
        WindowsScreenCaptureApi,
        select_capture_backends,
    )
    from .capture_desktop_duplication import WindowsDesktopDuplicationCaptureBackend
    from .capture_dxcam import WindowsDxcamCaptureBackend
    from .capture_gdi import CtypesWindowsScreenCaptureApi, WindowsGdiCaptureBackend
    from .capture_models import (
        RawWindowsCapture,
        WindowsCaptureBackendCapability,
        WindowsCaptureBackendEvaluation,
        WindowsCaptureBackendIntendedTarget,
        WindowsCaptureBackendPolicy,
        WindowsCaptureBackendRole,
        WindowsCaptureBackendSelection,
        WindowsCaptureRequest,
        WindowsCaptureRuntimeMode,
        WindowsCaptureStageError,
        WindowsCaptureTarget,
        WindowsCaptureUnavailableError,
    )
    from .capture_printwindow import WindowsForegroundWindowPrintCaptureBackend
    from .click import WindowsUser32ClickTransport
    from .dxcam_capture_diagnostic import (
        DxcamBackendAttemptDiagnostic,
        DxcamCaptureDiagnosticResult,
        run_dxcam_capture_diagnostic,
    )
    from .foreground_capture_diagnostic import (
        ForegroundCaptureDiagnosticResult,
        ForegroundWindowMetadata,
        ForegroundWindowMetadataReader,
        ForegroundWindowMetadataResult,
        WindowsForegroundWindowMetadataReader,
        run_foreground_window_capture_diagnostic,
    )
    from .screen_metrics import (
        CtypesWindowsMonitorApi,
        RawWindowsMonitorMetrics,
        WindowsApiUnavailableError,
        WindowsMonitorApi,
        WindowsScreenMetricsProvider,
    )
