"""Windows integration exports."""

from universal_visual_os_agent.integrations.windows.capture import (
    WindowsObserveOnlyCaptureProvider,
)
from universal_visual_os_agent.integrations.windows.capture_backends import (
    WindowsCaptureBackend,
    WindowsScreenCaptureApi,
    select_capture_backends,
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
    "WindowsCaptureBackend",
    "WindowsCaptureBackendCapability",
    "WindowsCaptureBackendSelection",
    "WindowsCaptureRequest",
    "WindowsCaptureUnavailableError",
    "WindowsCaptureStageError",
    "WindowsCaptureTarget",
    "WindowsApiUnavailableError",
    "WindowsForegroundWindowPrintCaptureBackend",
    "WindowsGdiCaptureBackend",
    "WindowsObserveOnlyCaptureProvider",
    "WindowsMonitorApi",
    "WindowsScreenCaptureApi",
    "WindowsScreenMetricsProvider",
    "select_capture_backends",
]
