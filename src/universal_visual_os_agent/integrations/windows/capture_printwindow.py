"""PrintWindow-backed foreground-window capture backend."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol
import sys

from universal_visual_os_agent.geometry import ScreenBBox
from universal_visual_os_agent.integrations.windows.capture_models import (
    RawWindowsCapture,
    WindowsCaptureBackendCapability,
    WindowsCaptureRequest,
    WindowsCaptureStageError,
    WindowsCaptureTarget,
    WindowsCaptureUnavailableError,
)
from universal_visual_os_agent.perception import FramePixelFormat

_BI_RGB = 0
_DIB_RGB_COLORS = 0


@dataclass(slots=True)
class _PrintWindowAttemptState:
    """Mutable state for one PrintWindow capture attempt."""

    stage: str = "not_started"
    target_window_resolved: bool = False
    source_dc_acquired: bool = False
    memory_dc_created: bool = False
    bitmap_created: bool = False
    bitmap_selected: bool = False

    def to_details(self, *, backend_name: str, bounds: ScreenBBox | None, window_handle: int | None) -> dict[str, object]:
        details: dict[str, object] = {
            "backend_name": backend_name,
            "failing_stage": self.stage,
            "target_window_resolved": self.target_window_resolved,
            "source_dc_acquired": self.source_dc_acquired,
            "memory_dc_created": self.memory_dc_created,
            "bitmap_created": self.bitmap_created,
            "bitmap_selected": self.bitmap_selected,
        }
        if window_handle is not None:
            details["target_window_handle"] = window_handle
        if bounds is not None:
            details["bounds_left_px"] = bounds.left_px
            details["bounds_top_px"] = bounds.top_px
            details["bounds_width_px"] = bounds.width_px
            details["bounds_height_px"] = bounds.height_px
        return details


class _WindowCaptureFunctions(Protocol):
    """Minimal Win32 hooks used by the PrintWindow backend."""

    def get_foreground_window_handle(self) -> int | None:
        """Return the current foreground window handle."""


class WindowsForegroundWindowPrintCaptureBackend:
    """Read-only PrintWindow backend for the current foreground window."""

    backend_name = "printwindow_foreground"

    def detect_capability(self, request: WindowsCaptureRequest) -> WindowsCaptureBackendCapability:
        if not self._is_windows_platform():
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="PrintWindow capture is unavailable on this platform.",
                details={"platform": sys.platform},
            )
        if request.target is not WindowsCaptureTarget.foreground_window:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="PrintWindow backend only supports foreground_window requests.",
                details={"target": request.target},
            )

        window_handle = request.window_handle or self._detect_foreground_window_handle()
        if window_handle is None:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="No foreground window is available for PrintWindow capture.",
            )

        return WindowsCaptureBackendCapability.available_backend(
            backend_name=self.backend_name,
            details={
                "target": request.target,
                "target_window_handle": window_handle,
            },
        )

    def capture(self, request: WindowsCaptureRequest) -> RawWindowsCapture:
        if not self._is_windows_platform():
            raise WindowsCaptureUnavailableError("Windows capture APIs are not available on this platform.")
        if request.target is not WindowsCaptureTarget.foreground_window:
            raise WindowsCaptureStageError(
                stage="unsupported_request_target",
                message="PrintWindow backend only supports foreground_window requests.",
                diagnostics={"backend_name": self.backend_name, "target": request.target},
            )

        import ctypes
        from ctypes import wintypes

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        class RGBQUAD(ctypes.Structure):
            _fields_ = [
                ("rgbBlue", wintypes.BYTE),
                ("rgbGreen", wintypes.BYTE),
                ("rgbRed", wintypes.BYTE),
                ("rgbReserved", wintypes.BYTE),
            ]

        class BITMAPINFO(ctypes.Structure):
            _fields_ = [
                ("bmiHeader", BITMAPINFOHEADER),
                ("bmiColors", RGBQUAD * 1),
            ]

        handle_type = wintypes.HANDLE
        hdc_type = getattr(wintypes, "HDC", handle_type)
        hwnd_type = getattr(wintypes, "HWND", handle_type)
        hgdi_error = ctypes.c_void_p(-1).value

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

        get_foreground_window = user32.GetForegroundWindow
        get_foreground_window.argtypes = []
        get_foreground_window.restype = hwnd_type

        get_window_rect = user32.GetWindowRect
        get_window_rect.argtypes = [hwnd_type, ctypes.POINTER(RECT)]
        get_window_rect.restype = wintypes.BOOL

        get_window_dc = user32.GetWindowDC
        get_window_dc.argtypes = [hwnd_type]
        get_window_dc.restype = hdc_type

        release_dc = user32.ReleaseDC
        release_dc.argtypes = [hwnd_type, hdc_type]
        release_dc.restype = ctypes.c_int

        print_window = user32.PrintWindow
        print_window.argtypes = [hwnd_type, hdc_type, wintypes.UINT]
        print_window.restype = wintypes.BOOL

        create_compatible_dc = gdi32.CreateCompatibleDC
        create_compatible_dc.argtypes = [hdc_type]
        create_compatible_dc.restype = hdc_type

        delete_dc = gdi32.DeleteDC
        delete_dc.argtypes = [hdc_type]
        delete_dc.restype = wintypes.BOOL

        create_compatible_bitmap = gdi32.CreateCompatibleBitmap
        create_compatible_bitmap.argtypes = [hdc_type, ctypes.c_int, ctypes.c_int]
        create_compatible_bitmap.restype = handle_type

        select_object = gdi32.SelectObject
        select_object.argtypes = [hdc_type, handle_type]
        select_object.restype = handle_type

        get_dibits = gdi32.GetDIBits
        get_dibits.argtypes = [
            hdc_type,
            handle_type,
            wintypes.UINT,
            wintypes.UINT,
            ctypes.c_void_p,
            ctypes.POINTER(BITMAPINFO),
            wintypes.UINT,
        ]
        get_dibits.restype = ctypes.c_int

        delete_object = gdi32.DeleteObject
        delete_object.argtypes = [handle_type]
        delete_object.restype = wintypes.BOOL

        attempt = _PrintWindowAttemptState()
        source_dc = None
        memory_dc = None
        bitmap = None
        previous_object = None
        bounds = None
        window_handle: int | None = None

        try:
            attempt.stage = "detect_target_window"
            _reset_last_error(ctypes)
            window_handle = request.window_handle or _normalize_handle(get_foreground_window())
            if window_handle is None:
                raise _stage_error(
                    ctypes_module=ctypes,
                    stage=attempt.stage,
                    message="No foreground window is available for PrintWindow capture.",
                    attempt=attempt,
                    backend_name=self.backend_name,
                    bounds=bounds,
                    window_handle=window_handle,
                )
            attempt.target_window_resolved = True

            attempt.stage = "get_window_rect"
            rect = RECT()
            _reset_last_error(ctypes)
            if not get_window_rect(window_handle, ctypes.byref(rect)):
                raise _stage_error(
                    ctypes_module=ctypes,
                    stage=attempt.stage,
                    message="GetWindowRect failed.",
                    attempt=attempt,
                    backend_name=self.backend_name,
                    bounds=bounds,
                    window_handle=window_handle,
                )
            bounds = ScreenBBox(
                left_px=int(rect.left),
                top_px=int(rect.top),
                width_px=int(rect.right) - int(rect.left),
                height_px=int(rect.bottom) - int(rect.top),
            )
            if bounds.width_px <= 0 or bounds.height_px <= 0:
                raise _stage_error(
                    ctypes_module=ctypes,
                    stage="validate_bounds",
                    message="Foreground window bounds must be positive.",
                    attempt=attempt,
                    backend_name=self.backend_name,
                    bounds=bounds,
                    window_handle=window_handle,
                )

            attempt.stage = "acquire_source_dc"
            _reset_last_error(ctypes)
            source_dc = get_window_dc(window_handle)
            if not source_dc:
                raise _stage_error(
                    ctypes_module=ctypes,
                    stage=attempt.stage,
                    message="GetWindowDC failed.",
                    attempt=attempt,
                    backend_name=self.backend_name,
                    bounds=bounds,
                    window_handle=window_handle,
                )
            attempt.source_dc_acquired = True

            attempt.stage = "create_memory_dc"
            _reset_last_error(ctypes)
            memory_dc = create_compatible_dc(source_dc)
            if not memory_dc:
                raise _stage_error(
                    ctypes_module=ctypes,
                    stage=attempt.stage,
                    message="CreateCompatibleDC failed.",
                    attempt=attempt,
                    backend_name=self.backend_name,
                    bounds=bounds,
                    window_handle=window_handle,
                )
            attempt.memory_dc_created = True

            attempt.stage = "create_bitmap"
            _reset_last_error(ctypes)
            bitmap = create_compatible_bitmap(source_dc, bounds.width_px, bounds.height_px)
            if not bitmap:
                raise _stage_error(
                    ctypes_module=ctypes,
                    stage=attempt.stage,
                    message="CreateCompatibleBitmap failed.",
                    attempt=attempt,
                    backend_name=self.backend_name,
                    bounds=bounds,
                    window_handle=window_handle,
                )
            attempt.bitmap_created = True

            attempt.stage = "select_bitmap"
            _reset_last_error(ctypes)
            previous_object = select_object(memory_dc, bitmap)
            if previous_object in (None, 0, hgdi_error):
                raise _stage_error(
                    ctypes_module=ctypes,
                    stage=attempt.stage,
                    message="SelectObject failed.",
                    attempt=attempt,
                    backend_name=self.backend_name,
                    bounds=bounds,
                    window_handle=window_handle,
                )
            attempt.bitmap_selected = True

            attempt.stage = "print_window"
            _reset_last_error(ctypes)
            printed = print_window(window_handle, memory_dc, 0)
            if not printed:
                raise _stage_error(
                    ctypes_module=ctypes,
                    stage=attempt.stage,
                    message="PrintWindow failed.",
                    attempt=attempt,
                    backend_name=self.backend_name,
                    bounds=bounds,
                    window_handle=window_handle,
                )

            attempt.stage = "get_dibits"
            row_stride_bytes = bounds.width_px * FramePixelFormat.bgra_8888.bytes_per_pixel
            image_buffer = ctypes.create_string_buffer(row_stride_bytes * bounds.height_px)
            bitmap_info = BITMAPINFO()
            bitmap_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bitmap_info.bmiHeader.biWidth = bounds.width_px
            bitmap_info.bmiHeader.biHeight = -bounds.height_px
            bitmap_info.bmiHeader.biPlanes = 1
            bitmap_info.bmiHeader.biBitCount = 32
            bitmap_info.bmiHeader.biCompression = _BI_RGB
            bitmap_info.bmiHeader.biSizeImage = row_stride_bytes * bounds.height_px

            _reset_last_error(ctypes)
            scan_lines = get_dibits(
                memory_dc,
                bitmap,
                0,
                bounds.height_px,
                ctypes.cast(image_buffer, ctypes.c_void_p),
                ctypes.byref(bitmap_info),
                _DIB_RGB_COLORS,
            )
            if scan_lines != bounds.height_px:
                raise _stage_error(
                    ctypes_module=ctypes,
                    stage=attempt.stage,
                    message="GetDIBits failed.",
                    attempt=attempt,
                    backend_name=self.backend_name,
                    bounds=bounds,
                    window_handle=window_handle,
                )

            return RawWindowsCapture(
                width=bounds.width_px,
                height=bounds.height_px,
                origin_x_px=bounds.left_px,
                origin_y_px=bounds.top_px,
                row_stride_bytes=row_stride_bytes,
                image_bytes=image_buffer.raw,
                metadata={
                    "backend_name": self.backend_name,
                    "capture_source_strategy": "print_window",
                    "target_window_handle": window_handle,
                },
            )
        finally:
            if attempt.bitmap_selected and previous_object not in (None, 0, hgdi_error) and memory_dc:
                select_object(memory_dc, previous_object)
            if bitmap:
                delete_object(bitmap)
            if memory_dc:
                delete_dc(memory_dc)
            if source_dc and window_handle is not None:
                release_dc(window_handle, source_dc)

    def _is_windows_platform(self) -> bool:
        return sys.platform == "win32"

    def _detect_foreground_window_handle(self) -> int | None:
        if not self._is_windows_platform():
            return None

        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        get_foreground_window = user32.GetForegroundWindow
        get_foreground_window.argtypes = []
        get_foreground_window.restype = getattr(wintypes, "HWND", wintypes.HANDLE)
        return _normalize_handle(get_foreground_window())


def _normalize_handle(handle: object) -> int | None:
    if handle in (None, 0):
        return None
    if hasattr(handle, "value"):
        value = getattr(handle, "value")
        return None if value in (None, 0) else int(value)
    return int(handle)


def _reset_last_error(ctypes_module: object) -> None:
    set_last_error = getattr(ctypes_module, "set_last_error", None)
    if callable(set_last_error):
        set_last_error(0)


def _format_win32_error(ctypes_module: object, error_code: int) -> str:
    try:
        return str(ctypes_module.FormatError(error_code)).strip()
    except (AttributeError, OSError):
        return ""


def _stage_error(
    *,
    ctypes_module: object,
    stage: str,
    message: str,
    attempt: _PrintWindowAttemptState,
    backend_name: str,
    bounds: ScreenBBox | None,
    window_handle: int | None,
) -> WindowsCaptureStageError:
    win32_error_code = getattr(ctypes_module, "get_last_error")()
    diagnostics = attempt.to_details(backend_name=backend_name, bounds=bounds, window_handle=window_handle)
    if win32_error_code:
        diagnostics["win32_error_message"] = _format_win32_error(ctypes_module, win32_error_code)
    return WindowsCaptureStageError(
        stage=stage,
        message=message,
        win32_error_code=win32_error_code or None,
        diagnostics=diagnostics,
    )
