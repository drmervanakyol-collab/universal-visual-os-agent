"""Read-only Windows screen metrics provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from universal_visual_os_agent.geometry import (
    ScreenMetrics,
    ScreenMetricsProvider,
    ScreenMetricsQueryResult,
    VirtualDesktopMetrics,
)

_DEFAULT_DPI = 96
_MONITORINFOF_PRIMARY = 0x00000001
_MDT_EFFECTIVE_DPI = 0
_ENUM_CURRENT_SETTINGS = 0xFFFFFFFF


class WindowsApiUnavailableError(RuntimeError):
    """Raised when Windows monitor APIs are unavailable to the provider."""


@dataclass(slots=True, frozen=True, kw_only=True)
class RawWindowsMonitorMetrics:
    """Raw monitor metrics read from Windows APIs."""

    left_px: int
    top_px: int
    right_px: int
    bottom_px: int
    is_primary: bool = False
    dpi_x: int | None = None
    dpi_y: int | None = None
    display_id: str | None = None

    def __post_init__(self) -> None:
        if self.right_px <= self.left_px:
            raise ValueError("right_px must be greater than left_px.")
        if self.bottom_px <= self.top_px:
            raise ValueError("bottom_px must be greater than top_px.")
        if self.dpi_x is not None and self.dpi_x <= 0:
            raise ValueError("dpi_x must be positive when provided.")
        if self.dpi_y is not None and self.dpi_y <= 0:
            raise ValueError("dpi_y must be positive when provided.")

    @property
    def width_px(self) -> int:
        """Return the monitor width in pixels."""

        return self.right_px - self.left_px

    @property
    def height_px(self) -> int:
        """Return the monitor height in pixels."""

        return self.bottom_px - self.top_px

    @property
    def dpi_scale(self) -> float:
        """Return the normalized DPI scale relative to 96 DPI."""

        dpi_x = _DEFAULT_DPI if self.dpi_x is None else self.dpi_x
        return dpi_x / _DEFAULT_DPI


class WindowsMonitorApi(Protocol):
    """Low-level Windows monitor enumeration contract."""

    def list_monitors(self) -> tuple[RawWindowsMonitorMetrics, ...]:
        """Return the current monitor layout from Windows APIs."""


class CtypesWindowsMonitorApi:
    """Win32-backed monitor reader using only the standard library."""

    def list_monitors(self) -> tuple[RawWindowsMonitorMetrics, ...]:
        """Return raw monitor metrics or raise a safe availability error."""

        import sys

        if sys.platform != "win32":
            raise WindowsApiUnavailableError("Windows APIs are not available on this platform.")

        import ctypes
        from ctypes import wintypes

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        class MONITORINFOEXW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
                ("szDevice", wintypes.WCHAR * 32),
            ]

        class POINTL(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class _PrinterSettings(ctypes.Structure):
            _fields_ = [
                ("dmOrientation", wintypes.SHORT),
                ("dmPaperSize", wintypes.SHORT),
                ("dmPaperLength", wintypes.SHORT),
                ("dmPaperWidth", wintypes.SHORT),
                ("dmScale", wintypes.SHORT),
                ("dmCopies", wintypes.SHORT),
                ("dmDefaultSource", wintypes.SHORT),
                ("dmPrintQuality", wintypes.SHORT),
            ]

        class _DisplaySettings(ctypes.Structure):
            _fields_ = [
                ("dmPosition", POINTL),
                ("dmDisplayOrientation", wintypes.DWORD),
                ("dmDisplayFixedOutput", wintypes.DWORD),
            ]

        class _DeviceModeUnion(ctypes.Union):
            _fields_ = [
                ("printer", _PrinterSettings),
                ("display", _DisplaySettings),
            ]

        class _DisplayFlagsUnion(ctypes.Union):
            _fields_ = [
                ("dmDisplayFlags", wintypes.DWORD),
                ("dmNup", wintypes.DWORD),
            ]

        class DEVMODEW(ctypes.Structure):
            _fields_ = [
                ("dmDeviceName", wintypes.WCHAR * 32),
                ("dmSpecVersion", wintypes.WORD),
                ("dmDriverVersion", wintypes.WORD),
                ("dmSize", wintypes.WORD),
                ("dmDriverExtra", wintypes.WORD),
                ("dmFields", wintypes.DWORD),
                ("settings", _DeviceModeUnion),
                ("dmColor", wintypes.SHORT),
                ("dmDuplex", wintypes.SHORT),
                ("dmYResolution", wintypes.SHORT),
                ("dmTTOption", wintypes.SHORT),
                ("dmCollate", wintypes.SHORT),
                ("dmFormName", wintypes.WCHAR * 32),
                ("dmLogPixels", wintypes.WORD),
                ("dmBitsPerPel", wintypes.DWORD),
                ("dmPelsWidth", wintypes.DWORD),
                ("dmPelsHeight", wintypes.DWORD),
                ("display_flags", _DisplayFlagsUnion),
                ("dmDisplayFrequency", wintypes.DWORD),
                ("dmICMMethod", wintypes.DWORD),
                ("dmICMIntent", wintypes.DWORD),
                ("dmMediaType", wintypes.DWORD),
                ("dmDitherType", wintypes.DWORD),
                ("dmReserved1", wintypes.DWORD),
                ("dmReserved2", wintypes.DWORD),
                ("dmPanningWidth", wintypes.DWORD),
                ("dmPanningHeight", wintypes.DWORD),
            ]

        hmonitor_type = wintypes.HANDLE
        hdc_type = getattr(wintypes, "HDC", wintypes.HANDLE)
        monitor_enum_proc = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            hmonitor_type,
            hdc_type,
            ctypes.POINTER(RECT),
            wintypes.LPARAM,
        )

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        try:
            shcore = ctypes.WinDLL("shcore", use_last_error=True)
        except OSError:
            shcore = None

        enum_display_monitors = user32.EnumDisplayMonitors
        enum_display_monitors.argtypes = [
            hdc_type,
            ctypes.POINTER(RECT),
            monitor_enum_proc,
            wintypes.LPARAM,
        ]
        enum_display_monitors.restype = wintypes.BOOL

        get_monitor_info = user32.GetMonitorInfoW
        get_monitor_info.argtypes = [hmonitor_type, ctypes.POINTER(MONITORINFOEXW)]
        get_monitor_info.restype = wintypes.BOOL

        enum_display_settings = user32.EnumDisplaySettingsW
        enum_display_settings.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(DEVMODEW)]
        enum_display_settings.restype = wintypes.BOOL

        get_dpi_for_monitor = None
        if shcore is not None:
            get_dpi_for_monitor = shcore.GetDpiForMonitor
            get_dpi_for_monitor.argtypes = [
                hmonitor_type,
                ctypes.c_int,
                ctypes.POINTER(wintypes.UINT),
                ctypes.POINTER(wintypes.UINT),
            ]
            get_dpi_for_monitor.restype = ctypes.HRESULT

        monitors: list[RawWindowsMonitorMetrics] = []

        def _read_display_bounds(device_name: str) -> tuple[int, int, int, int] | None:
            device_mode = DEVMODEW()
            device_mode.dmSize = ctypes.sizeof(DEVMODEW)
            if not enum_display_settings(device_name, _ENUM_CURRENT_SETTINGS, ctypes.byref(device_mode)):
                return None

            left_px = int(device_mode.settings.display.dmPosition.x)
            top_px = int(device_mode.settings.display.dmPosition.y)
            width_px = int(device_mode.dmPelsWidth)
            height_px = int(device_mode.dmPelsHeight)
            return (
                left_px,
                top_px,
                left_px + width_px,
                top_px + height_px,
            )

        def _callback(
            hmonitor: int,
            _hdc: int,
            _monitor_rect: ctypes.Array[RECT],
            _lparam: int,
        ) -> int:
            info = MONITORINFOEXW()
            info.cbSize = ctypes.sizeof(MONITORINFOEXW)
            if not get_monitor_info(hmonitor, ctypes.byref(info)):
                return 0

            display_id = info.szDevice.rstrip("\x00") or None
            display_bounds = None if display_id is None else _read_display_bounds(display_id)
            if display_bounds is None:
                display_bounds = (
                    int(info.rcMonitor.left),
                    int(info.rcMonitor.top),
                    int(info.rcMonitor.right),
                    int(info.rcMonitor.bottom),
                )

            dpi_x = _DEFAULT_DPI
            dpi_y = _DEFAULT_DPI
            if get_dpi_for_monitor is not None:
                dpi_x_value = wintypes.UINT()
                dpi_y_value = wintypes.UINT()
                result = get_dpi_for_monitor(
                    hmonitor,
                    _MDT_EFFECTIVE_DPI,
                    ctypes.byref(dpi_x_value),
                    ctypes.byref(dpi_y_value),
                )
                if result == 0:
                    dpi_x = int(dpi_x_value.value)
                    dpi_y = int(dpi_y_value.value)

            monitors.append(
                RawWindowsMonitorMetrics(
                    left_px=display_bounds[0],
                    top_px=display_bounds[1],
                    right_px=display_bounds[2],
                    bottom_px=display_bounds[3],
                    is_primary=bool(info.dwFlags & _MONITORINFOF_PRIMARY),
                    dpi_x=dpi_x,
                    dpi_y=dpi_y,
                    display_id=display_id,
                )
            )
            return 1

        callback = monitor_enum_proc(_callback)
        if not enum_display_monitors(None, None, callback, 0):
            error_code = ctypes.get_last_error()
            raise OSError(error_code, "EnumDisplayMonitors failed.")
        if not monitors:
            raise OSError("Windows returned no monitor metrics.")

        return tuple(monitors)


class WindowsScreenMetricsProvider(ScreenMetricsProvider):
    """Read-only adapter that exposes Windows monitor layout safely."""

    def __init__(self, api: WindowsMonitorApi | None = None) -> None:
        self._api = CtypesWindowsMonitorApi() if api is None else api

    def get_virtual_desktop_metrics(self) -> ScreenMetricsQueryResult:
        """Return structured Windows monitor metrics or a safe failure result."""

        try:
            raw_monitors = self._api.list_monitors()
            metrics = _build_virtual_desktop_metrics(raw_monitors)
        except WindowsApiUnavailableError as exc:
            return ScreenMetricsQueryResult.failure(
                provider_name=self.__class__.__name__,
                error_code="windows_api_unavailable",
                error_message=str(exc),
            )
        except ValueError as exc:
            return ScreenMetricsQueryResult.failure(
                provider_name=self.__class__.__name__,
                error_code="invalid_monitor_data",
                error_message=str(exc),
            )
        except OSError as exc:
            return ScreenMetricsQueryResult.failure(
                provider_name=self.__class__.__name__,
                error_code="windows_api_error",
                error_message=str(exc),
            )

        return ScreenMetricsQueryResult.ok(
            provider_name=self.__class__.__name__,
            metrics=metrics,
            details={"display_count": len(metrics.displays)},
        )


def _build_virtual_desktop_metrics(
    raw_monitors: tuple[RawWindowsMonitorMetrics, ...],
) -> VirtualDesktopMetrics:
    if not raw_monitors:
        raise ValueError("At least one monitor must be returned.")

    displays = tuple(_screen_metrics_from_raw(raw_monitor, index=index) for index, raw_monitor in enumerate(raw_monitors))
    return VirtualDesktopMetrics(displays=displays)


def _screen_metrics_from_raw(raw_monitor: RawWindowsMonitorMetrics, *, index: int) -> ScreenMetrics:
    display_id = raw_monitor.display_id or f"monitor-{index}"
    return ScreenMetrics(
        width_px=raw_monitor.width_px,
        height_px=raw_monitor.height_px,
        origin_x_px=raw_monitor.left_px,
        origin_y_px=raw_monitor.top_px,
        dpi_scale=raw_monitor.dpi_scale,
        display_id=display_id,
        is_primary=raw_monitor.is_primary,
    )
