"""Windows integration exports."""

from universal_visual_os_agent.integrations.windows.capture import (
    CtypesWindowsScreenCaptureApi,
    RawWindowsCapture,
    WindowsCaptureUnavailableError,
    WindowsObserveOnlyCaptureProvider,
    WindowsScreenCaptureApi,
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
    "WindowsCaptureUnavailableError",
    "WindowsApiUnavailableError",
    "WindowsObserveOnlyCaptureProvider",
    "WindowsMonitorApi",
    "WindowsScreenCaptureApi",
    "WindowsScreenMetricsProvider",
]
