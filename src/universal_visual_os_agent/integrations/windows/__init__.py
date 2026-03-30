"""Windows integration exports."""

from universal_visual_os_agent.integrations.windows.capture import (
    WindowsObserveOnlyCaptureProvider,
)
from universal_visual_os_agent.integrations.windows.capture_backends import (
    WindowsCaptureBackend,
    WindowsScreenCaptureApi,
    select_capture_backends,
)
from universal_visual_os_agent.integrations.windows.capture_desktop_duplication import (
    WindowsDesktopDuplicationCaptureBackend,
)
from universal_visual_os_agent.integrations.windows.capture_dxcam import (
    WindowsDxcamCaptureBackend,
)
from universal_visual_os_agent.integrations.windows.capture_gdi import (
    CtypesWindowsScreenCaptureApi,
    WindowsGdiCaptureBackend,
)
from universal_visual_os_agent.integrations.windows.capture_models import (
    RawWindowsCapture,
    WindowsCaptureBackendCapability,
    WindowsCaptureBackendSelection,
    WindowsCaptureRequest,
    WindowsCaptureStageError,
    WindowsCaptureTarget,
    WindowsCaptureUnavailableError,
)
from universal_visual_os_agent.integrations.windows.capture_printwindow import (
    WindowsForegroundWindowPrintCaptureBackend,
)
from universal_visual_os_agent.integrations.windows.dxcam_capture_diagnostic import (
    DxcamBackendAttemptDiagnostic,
    DxcamCaptureDiagnosticResult,
    run_dxcam_capture_diagnostic,
)
from universal_visual_os_agent.integrations.windows.foreground_capture_diagnostic import (
    ForegroundCaptureDiagnosticResult,
    ForegroundWindowMetadata,
    ForegroundWindowMetadataReader,
    ForegroundWindowMetadataResult,
    WindowsForegroundWindowMetadataReader,
    run_foreground_window_capture_diagnostic,
)
from universal_visual_os_agent.integrations.windows.screen_metrics import (
    CtypesWindowsMonitorApi,
    RawWindowsMonitorMetrics,
    WindowsApiUnavailableError,
    WindowsMonitorApi,
    WindowsScreenMetricsProvider,
)

__all__ = [
    "CtypesWindowsScreenCaptureApi",
    "CtypesWindowsMonitorApi",
    "RawWindowsCapture",
    "RawWindowsMonitorMetrics",
    "DxcamBackendAttemptDiagnostic",
    "DxcamCaptureDiagnosticResult",
    "ForegroundCaptureDiagnosticResult",
    "ForegroundWindowMetadata",
    "ForegroundWindowMetadataReader",
    "ForegroundWindowMetadataResult",
    "WindowsCaptureBackend",
    "WindowsCaptureBackendCapability",
    "WindowsCaptureBackendSelection",
    "WindowsCaptureRequest",
    "WindowsCaptureUnavailableError",
    "WindowsCaptureStageError",
    "WindowsCaptureTarget",
    "WindowsApiUnavailableError",
    "WindowsDesktopDuplicationCaptureBackend",
    "WindowsDxcamCaptureBackend",
    "WindowsForegroundWindowPrintCaptureBackend",
    "WindowsForegroundWindowMetadataReader",
    "WindowsGdiCaptureBackend",
    "WindowsObserveOnlyCaptureProvider",
    "WindowsMonitorApi",
    "WindowsScreenCaptureApi",
    "WindowsScreenMetricsProvider",
    "run_dxcam_capture_diagnostic",
    "run_foreground_window_capture_diagnostic",
    "select_capture_backends",
]
