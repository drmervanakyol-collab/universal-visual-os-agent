"""GDI-backed virtual-desktop capture backend."""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
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
_SRCCOPY = 0x00CC0020
_DESKTOP_READOBJECTS = 0x0001
_SM_REMOTESESSION = 0x1000
_SOURCE_SCREEN_DC = "screen_dc"
_SOURCE_DESKTOP_WINDOW_DC = "desktop_window_dc"
_SOURCE_DISPLAY_DC = "display_dc"
_SOURCE_ORDER = (_SOURCE_SCREEN_DC, _SOURCE_DESKTOP_WINDOW_DC, _SOURCE_DISPLAY_DC)


@dataclass(slots=True)
class _CaptureAttemptState:
    """Mutable state for one GDI capture source attempt."""

    source_strategy: str
    stage: str = "not_started"
    source_dc_acquired: bool = False
    memory_dc_created: bool = False
    bitmap_created: bool = False
    bitmap_selected: bool = False

    def to_details(self, bounds: ScreenBBox, *, backend_name: str) -> dict[str, object]:
        return {
            "backend_name": backend_name,
            "capture_source_strategy": self.source_strategy,
            "failing_stage": self.stage,
            "source_dc_acquired": self.source_dc_acquired,
            "memory_dc_created": self.memory_dc_created,
            "bitmap_created": self.bitmap_created,
            "bitmap_selected": self.bitmap_selected,
            "bounds_left_px": bounds.left_px,
            "bounds_top_px": bounds.top_px,
            "bounds_width_px": bounds.width_px,
            "bounds_height_px": bounds.height_px,
        }


class WindowsGdiCaptureBackend:
    """Read-only GDI/BitBlt backend for virtual desktop capture."""

    backend_name = "gdi_bitblt"

    def detect_capability(self, request: WindowsCaptureRequest) -> WindowsCaptureBackendCapability:
        if not self._is_windows_platform():
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Windows GDI capture is unavailable on this platform.",
                details={"platform": sys.platform},
            )
        if request.target is not WindowsCaptureTarget.virtual_desktop:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="GDI capture only supports virtual_desktop requests.",
                details={"target": request.target},
            )
        if request.bounds is None:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Virtual desktop bounds are required for GDI capture.",
            )
        if not _bounds_are_valid(request.bounds):
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Virtual desktop bounds must be positive.",
                details={
                    "bounds_left_px": request.bounds.left_px,
                    "bounds_top_px": request.bounds.top_px,
                    "bounds_width_px": request.bounds.width_px,
                    "bounds_height_px": request.bounds.height_px,
                },
            )
        return WindowsCaptureBackendCapability.available_backend(
            backend_name=self.backend_name,
            details={
                "target": request.target,
                "source_order": _SOURCE_ORDER,
            },
        )

    def capture(self, request: WindowsCaptureRequest) -> RawWindowsCapture:
        if not self._is_windows_platform():
            raise WindowsCaptureUnavailableError("Windows capture APIs are not available on this platform.")
        if request.target is not WindowsCaptureTarget.virtual_desktop:
            raise WindowsCaptureStageError(
                stage="unsupported_request_target",
                message="GDI capture only supports virtual_desktop requests.",
                diagnostics={"backend_name": self.backend_name, "target": request.target},
            )
        if request.bounds is None:
            raise WindowsCaptureStageError(
                stage="validate_bounds",
                message="Virtual desktop bounds are required.",
                diagnostics={"backend_name": self.backend_name},
            )
        self._validate_bounds(request.bounds)
        attempts: list[dict[str, object]] = []

        for source_strategy in self._capture_source_order():
            try:
                raw_capture = self._capture_from_source(request.bounds, source_strategy)
            except WindowsCaptureStageError as exc:
                attempts.append(
                    {
                        "backend_name": self.backend_name,
                        "capture_source_strategy": source_strategy,
                        "failing_stage": exc.stage,
                        "win32_error_code": exc.win32_error_code,
                        **exc.diagnostics,
                    }
                )
                continue

            metadata = {
                **raw_capture.metadata,
                "backend_name": self.backend_name,
                "capture_source_strategy": source_strategy,
                "backend_fallback_used": bool(attempts),
                "backend_attempt_count": len(attempts) + 1,
            }
            if attempts:
                metadata["backend_prior_attempts"] = tuple(attempts)
            return replace(raw_capture, metadata=metadata)

        raise WindowsCaptureStageError(
            stage="capture_fallback_exhausted",
            message="All GDI capture sources failed.",
            win32_error_code=_last_attempt_error_code(attempts),
            diagnostics={
                "backend_name": self.backend_name,
                "attempts": tuple(attempts),
                **self._capture_environment_details(),
            },
        )

    def capture_bounds(self, bounds: ScreenBBox) -> RawWindowsCapture:
        """Legacy compatibility wrapper for bounds-based callers."""

        return self.capture(WindowsCaptureRequest(target=WindowsCaptureTarget.virtual_desktop, bounds=bounds))

    def _is_windows_platform(self) -> bool:
        return sys.platform == "win32"

    def _capture_source_order(self) -> tuple[str, ...]:
        return _SOURCE_ORDER

    def _validate_bounds(self, bounds: ScreenBBox) -> None:
        if not _bounds_are_valid(bounds):
            raise WindowsCaptureStageError(
                stage="validate_bounds",
                message="Capture bounds must be positive.",
                diagnostics={
                    "backend_name": self.backend_name,
                    "bounds_left_px": bounds.left_px,
                    "bounds_top_px": bounds.top_px,
                    "bounds_width_px": bounds.width_px,
                    "bounds_height_px": bounds.height_px,
                },
            )

    def _capture_environment_details(self) -> dict[str, object]:
        details: dict[str, object] = {
            "backend_name": self.backend_name,
            "platform": sys.platform,
            "session_name": os.environ.get("SESSIONNAME"),
        }
        if not self._is_windows_platform():
            return details

        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        get_system_metrics = user32.GetSystemMetrics
        get_system_metrics.argtypes = [ctypes.c_int]
        get_system_metrics.restype = ctypes.c_int

        open_input_desktop = user32.OpenInputDesktop
        open_input_desktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        open_input_desktop.restype = getattr(wintypes, "HDESK", wintypes.HANDLE)

        close_desktop = user32.CloseDesktop
        close_desktop.argtypes = [getattr(wintypes, "HDESK", wintypes.HANDLE)]
        close_desktop.restype = wintypes.BOOL

        details["is_remote_session"] = bool(get_system_metrics(_SM_REMOTESESSION))

        _reset_last_error(ctypes)
        desktop_handle = open_input_desktop(0, False, _DESKTOP_READOBJECTS)
        if desktop_handle:
            details["input_desktop_accessible"] = True
            close_desktop(desktop_handle)
        else:
            details["input_desktop_accessible"] = False
            error_code = ctypes.get_last_error()
            details["input_desktop_error_code"] = error_code
            if error_code:
                details["input_desktop_error_message"] = _format_win32_error(ctypes, error_code)

        return details

    def _capture_from_source(self, bounds: ScreenBBox, source_strategy: str) -> RawWindowsCapture:
        import ctypes
        from ctypes import wintypes

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

        get_dc = user32.GetDC
        get_dc.argtypes = [hwnd_type]
        get_dc.restype = hdc_type

        get_desktop_window = user32.GetDesktopWindow
        get_desktop_window.argtypes = []
        get_desktop_window.restype = hwnd_type

        get_window_dc = user32.GetWindowDC
        get_window_dc.argtypes = [hwnd_type]
        get_window_dc.restype = hdc_type

        release_dc = user32.ReleaseDC
        release_dc.argtypes = [hwnd_type, hdc_type]
        release_dc.restype = ctypes.c_int

        create_compatible_dc = gdi32.CreateCompatibleDC
        create_compatible_dc.argtypes = [hdc_type]
        create_compatible_dc.restype = hdc_type

        delete_dc = gdi32.DeleteDC
        delete_dc.argtypes = [hdc_type]
        delete_dc.restype = wintypes.BOOL

        create_compatible_bitmap = gdi32.CreateCompatibleBitmap
        create_compatible_bitmap.argtypes = [hdc_type, ctypes.c_int, ctypes.c_int]
        create_compatible_bitmap.restype = handle_type

        create_display_dc = gdi32.CreateDCW
        create_display_dc.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p]
        create_display_dc.restype = hdc_type

        select_object = gdi32.SelectObject
        select_object.argtypes = [hdc_type, handle_type]
        select_object.restype = handle_type

        bit_blt = gdi32.BitBlt
        bit_blt.argtypes = [
            hdc_type,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            hdc_type,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.DWORD,
        ]
        bit_blt.restype = wintypes.BOOL

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

        attempt = _CaptureAttemptState(source_strategy=source_strategy)
        source_dc = None
        source_release_target = None
        source_release_kind = None
        memory_dc = None
        bitmap = None
        previous_object = None

        try:
            attempt.stage = "acquire_source_dc"
            _reset_last_error(ctypes)
            if source_strategy == _SOURCE_SCREEN_DC:
                source_dc = get_dc(None)
                source_release_kind = "release_dc"
            elif source_strategy == _SOURCE_DESKTOP_WINDOW_DC:
                source_release_target = get_desktop_window()
                source_dc = get_window_dc(source_release_target)
                source_release_kind = "release_dc"
            elif source_strategy == _SOURCE_DISPLAY_DC:
                source_dc = create_display_dc("DISPLAY", None, None, None)
                source_release_kind = "delete_dc"
            else:
                raise ValueError(f"Unsupported capture source strategy: {source_strategy}")

            if not source_dc:
                raise _stage_error(
                    ctypes_module=ctypes,
                    stage=attempt.stage,
                    message=f"Failed to acquire source DC via {source_strategy}.",
                    attempt=attempt,
                    bounds=bounds,
                    backend_name=self.backend_name,
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
                    bounds=bounds,
                    backend_name=self.backend_name,
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
                    bounds=bounds,
                    backend_name=self.backend_name,
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
                    bounds=bounds,
                    backend_name=self.backend_name,
                )
            attempt.bitmap_selected = True

            attempt.stage = "bit_blt"
            _reset_last_error(ctypes)
            copied = bit_blt(
                memory_dc,
                0,
                0,
                bounds.width_px,
                bounds.height_px,
                source_dc,
                bounds.left_px,
                bounds.top_px,
                _SRCCOPY,
            )
            if not copied:
                raise _stage_error(
                    ctypes_module=ctypes,
                    stage=attempt.stage,
                    message="BitBlt failed.",
                    attempt=attempt,
                    bounds=bounds,
                    backend_name=self.backend_name,
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
                    bounds=bounds,
                    backend_name=self.backend_name,
                )

            return RawWindowsCapture(
                width=bounds.width_px,
                height=bounds.height_px,
                origin_x_px=bounds.left_px,
                origin_y_px=bounds.top_px,
                row_stride_bytes=row_stride_bytes,
                image_bytes=image_buffer.raw,
            )
        finally:
            if attempt.bitmap_selected and previous_object not in (None, 0, hgdi_error) and memory_dc:
                select_object(memory_dc, previous_object)
            if bitmap:
                delete_object(bitmap)
            if memory_dc:
                delete_dc(memory_dc)
            if source_dc:
                if source_release_kind == "release_dc":
                    release_dc(source_release_target, source_dc)
                elif source_release_kind == "delete_dc":
                    delete_dc(source_dc)


def _bounds_are_valid(bounds: ScreenBBox) -> bool:
    return bounds.width_px > 0 and bounds.height_px > 0


def _last_attempt_error_code(attempts: list[dict[str, object]]) -> int | None:
    if not attempts:
        return None
    last_code = attempts[-1].get("win32_error_code")
    return last_code if isinstance(last_code, int) else None


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
    attempt: _CaptureAttemptState,
    bounds: ScreenBBox,
    backend_name: str,
) -> WindowsCaptureStageError:
    win32_error_code = getattr(ctypes_module, "get_last_error")()
    diagnostics = attempt.to_details(bounds, backend_name=backend_name)
    if win32_error_code:
        diagnostics["win32_error_message"] = _format_win32_error(ctypes_module, win32_error_code)
    return WindowsCaptureStageError(
        stage=stage,
        message=message,
        win32_error_code=win32_error_code or None,
        diagnostics=diagnostics,
    )


CtypesWindowsScreenCaptureApi = WindowsGdiCaptureBackend
