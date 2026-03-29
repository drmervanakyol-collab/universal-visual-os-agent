"""PrintWindow-backed foreground-window capture backend."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import sys
from typing import Mapping

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
_SM_REMOTESESSION = 0x1000
_DESKTOP_READOBJECTS = 0x0001
_PW_DEFAULT = 0
_PW_RENDERFULLCONTENT = 0x00000002


@dataclass(slots=True)
class _PrintWindowAttemptState:
    """Mutable state for one PrintWindow capture attempt."""

    stage: str = "not_started"
    target_window_resolved: bool = False
    window_handle_validated: bool = False
    window_visible: bool | None = None
    window_minimized: bool | None = None
    foreground_window_stable: bool | None = None
    source_dc_acquired: bool = False
    memory_dc_created: bool = False
    bitmap_created: bool = False
    bitmap_selected: bool = False
    print_window_attempts: list[dict[str, object]] = field(default_factory=list)

    def to_details(
        self,
        *,
        backend_name: str,
        bounds: ScreenBBox | None,
        window_handle: int | None,
        requested_window_handle: int | None,
        detected_foreground_window_handle: int | None,
        environment_details: Mapping[str, object],
    ) -> dict[str, object]:
        details: dict[str, object] = {
            "backend_name": backend_name,
            "failing_stage": self.stage,
            "target_window_resolved": self.target_window_resolved,
            "window_handle_validated": self.window_handle_validated,
            "window_visible": self.window_visible,
            "window_minimized": self.window_minimized,
            "foreground_window_stable": self.foreground_window_stable,
            "source_dc_acquired": self.source_dc_acquired,
            "memory_dc_created": self.memory_dc_created,
            "bitmap_created": self.bitmap_created,
            "bitmap_selected": self.bitmap_selected,
            **dict(environment_details),
        }
        if requested_window_handle is not None:
            details["requested_window_handle"] = requested_window_handle
        if detected_foreground_window_handle is not None:
            details["detected_foreground_window_handle"] = detected_foreground_window_handle
        if window_handle is not None:
            details["target_window_handle"] = window_handle
        if bounds is not None:
            details["bounds_left_px"] = bounds.left_px
            details["bounds_top_px"] = bounds.top_px
            details["bounds_width_px"] = bounds.width_px
            details["bounds_height_px"] = bounds.height_px
        if self.print_window_attempts:
            details["print_window_attempts"] = tuple(dict(item) for item in self.print_window_attempts)
        return details


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

        detected_foreground_window_handle = (
            None if request.window_handle is not None else self._detect_foreground_window_handle()
        )
        window_handle = request.window_handle or detected_foreground_window_handle
        details: dict[str, object] = {
            "target": request.target,
        }
        if request.window_handle is not None:
            details["requested_window_handle"] = request.window_handle
        if detected_foreground_window_handle is not None:
            details["detected_foreground_window_handle"] = detected_foreground_window_handle
        if window_handle is None:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="No foreground window is available for PrintWindow capture.",
                details=details,
            )

        details["target_window_handle"] = window_handle
        if not self._is_window_handle_valid(window_handle):
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Foreground window handle is invalid or inaccessible.",
                details=details,
            )

        window_visible = self._is_window_visible(window_handle)
        details["window_visible"] = window_visible
        if not window_visible:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Foreground window is not visible for PrintWindow capture.",
                details=details,
            )

        window_minimized = self._is_window_minimized(window_handle)
        details["window_minimized"] = window_minimized
        if window_minimized:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Foreground window is minimized and will not be captured.",
                details=details,
            )

        details["print_window_flag_order"] = self._print_window_flag_order()
        return WindowsCaptureBackendCapability.available_backend(
            backend_name=self.backend_name,
            details=details,
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

        attempt = _PrintWindowAttemptState()
        environment_details = self._capture_environment_details()
        requested_window_handle = request.window_handle
        detected_foreground_window_handle = (
            None if request.window_handle is not None else self._detect_foreground_window_handle()
        )
        window_handle = request.window_handle or detected_foreground_window_handle
        bounds = None

        attempt.stage = "detect_target_window"
        if window_handle is None:
            raise self._build_stage_error(
                stage=attempt.stage,
                message="No foreground window is available for PrintWindow capture.",
                attempt=attempt,
                bounds=bounds,
                window_handle=window_handle,
                requested_window_handle=requested_window_handle,
                detected_foreground_window_handle=detected_foreground_window_handle,
                environment_details=environment_details,
                extra_diagnostics={"failure_classification": "no_foreground_window"},
            )
        attempt.target_window_resolved = True

        attempt.stage = "validate_window_handle"
        if not self._is_window_handle_valid(window_handle):
            raise self._build_stage_error(
                stage=attempt.stage,
                message="Foreground window handle is invalid or inaccessible.",
                attempt=attempt,
                bounds=bounds,
                window_handle=window_handle,
                requested_window_handle=requested_window_handle,
                detected_foreground_window_handle=detected_foreground_window_handle,
                environment_details=environment_details,
                extra_diagnostics={"failure_classification": "inaccessible_window_handle"},
            )
        attempt.window_handle_validated = True

        attempt.stage = "validate_window_visibility"
        attempt.window_visible = self._is_window_visible(window_handle)
        if not attempt.window_visible:
            raise self._build_stage_error(
                stage=attempt.stage,
                message="Foreground window is not visible for PrintWindow capture.",
                attempt=attempt,
                bounds=bounds,
                window_handle=window_handle,
                requested_window_handle=requested_window_handle,
                detected_foreground_window_handle=detected_foreground_window_handle,
                environment_details=environment_details,
                extra_diagnostics={"failure_classification": "window_not_visible"},
            )

        attempt.stage = "validate_window_state"
        attempt.window_minimized = self._is_window_minimized(window_handle)
        if attempt.window_minimized:
            raise self._build_stage_error(
                stage=attempt.stage,
                message="Foreground window is minimized and will not be captured.",
                attempt=attempt,
                bounds=bounds,
                window_handle=window_handle,
                requested_window_handle=requested_window_handle,
                detected_foreground_window_handle=detected_foreground_window_handle,
                environment_details=environment_details,
                extra_diagnostics={"failure_classification": "window_minimized"},
            )

        attempt.stage = "get_window_rect"
        try:
            bounds = self._get_window_bounds(window_handle)
        except WindowsCaptureStageError as exc:
            raise self._enrich_stage_error(
                exc,
                attempt=attempt,
                bounds=bounds,
                window_handle=window_handle,
                requested_window_handle=requested_window_handle,
                detected_foreground_window_handle=detected_foreground_window_handle,
                environment_details=environment_details,
            ) from None

        if bounds.width_px <= 0 or bounds.height_px <= 0:
            attempt.stage = "validate_bounds"
            raise self._build_stage_error(
                stage=attempt.stage,
                message="Foreground window bounds must be positive.",
                attempt=attempt,
                bounds=bounds,
                window_handle=window_handle,
                requested_window_handle=requested_window_handle,
                detected_foreground_window_handle=detected_foreground_window_handle,
                environment_details=environment_details,
                extra_diagnostics={"failure_classification": "invalid_window_bounds"},
            )

        if request.window_handle is None:
            self._ensure_foreground_window_stable(
                expected_window_handle=window_handle,
                phase="before_capture",
                attempt=attempt,
                bounds=bounds,
                requested_window_handle=requested_window_handle,
                detected_foreground_window_handle=detected_foreground_window_handle,
                environment_details=environment_details,
            )

        try:
            raw_capture = self._capture_window_image(
                window_handle=window_handle,
                bounds=bounds,
                attempt=attempt,
                requested_window_handle=requested_window_handle,
                detected_foreground_window_handle=detected_foreground_window_handle,
                environment_details=environment_details,
            )
        except WindowsCaptureStageError as exc:
            raise self._enrich_stage_error(
                exc,
                attempt=attempt,
                bounds=bounds,
                window_handle=window_handle,
                requested_window_handle=requested_window_handle,
                detected_foreground_window_handle=detected_foreground_window_handle,
                environment_details=environment_details,
            ) from None

        if request.window_handle is None:
            self._ensure_foreground_window_stable(
                expected_window_handle=window_handle,
                phase="after_capture",
                attempt=attempt,
                bounds=bounds,
                requested_window_handle=requested_window_handle,
                detected_foreground_window_handle=detected_foreground_window_handle,
                environment_details=environment_details,
            )

        metadata = {
            **raw_capture.metadata,
            "backend_name": self.backend_name,
            "capture_source_strategy": "print_window",
            "target_window_handle": window_handle,
            "target_window_visible": attempt.window_visible,
            "target_window_minimized": attempt.window_minimized,
            "foreground_window_stable": attempt.foreground_window_stable,
        }
        if attempt.print_window_attempts:
            metadata["print_window_attempts"] = tuple(dict(item) for item in attempt.print_window_attempts)
        return RawWindowsCapture(
            width=raw_capture.width,
            height=raw_capture.height,
            origin_x_px=raw_capture.origin_x_px,
            origin_y_px=raw_capture.origin_y_px,
            row_stride_bytes=raw_capture.row_stride_bytes,
            image_bytes=raw_capture.image_bytes,
            pixel_format=raw_capture.pixel_format,
            captured_at=raw_capture.captured_at,
            metadata=metadata,
        )

    def _capture_window_image(
        self,
        *,
        window_handle: int,
        bounds: ScreenBBox,
        attempt: _PrintWindowAttemptState,
        requested_window_handle: int | None,
        detected_foreground_window_handle: int | None,
        environment_details: Mapping[str, object],
    ) -> RawWindowsCapture:
        try:
            import ctypes
            from ctypes import wintypes
        except ImportError as exc:  # pragma: no cover - unavailable on supported Windows runtimes
            raise WindowsCaptureUnavailableError(str(exc)) from exc

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

        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        except (AttributeError, OSError) as exc:
            raise WindowsCaptureUnavailableError(str(exc)) from exc

        handle_type = wintypes.HANDLE
        hdc_type = getattr(wintypes, "HDC", handle_type)
        hwnd_type = getattr(wintypes, "HWND", handle_type)
        hgdi_error = ctypes.c_void_p(-1).value

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

        source_dc = None
        memory_dc = None
        bitmap = None
        previous_object = None

        try:
            attempt.stage = "acquire_source_dc"
            _reset_last_error(ctypes)
            source_dc = get_window_dc(window_handle)
            if not source_dc:
                raise self._build_stage_error(
                    stage=attempt.stage,
                    message="GetWindowDC failed.",
                    attempt=attempt,
                    bounds=bounds,
                    window_handle=window_handle,
                    requested_window_handle=requested_window_handle,
                    detected_foreground_window_handle=detected_foreground_window_handle,
                    environment_details=environment_details,
                    ctypes_module=ctypes,
                    extra_diagnostics={"failure_classification": "inaccessible_window_handle"},
                )
            attempt.source_dc_acquired = True

            attempt.stage = "create_memory_dc"
            _reset_last_error(ctypes)
            memory_dc = create_compatible_dc(source_dc)
            if not memory_dc:
                raise self._build_stage_error(
                    stage=attempt.stage,
                    message="CreateCompatibleDC failed.",
                    attempt=attempt,
                    bounds=bounds,
                    window_handle=window_handle,
                    requested_window_handle=requested_window_handle,
                    detected_foreground_window_handle=detected_foreground_window_handle,
                    environment_details=environment_details,
                    ctypes_module=ctypes,
                )
            attempt.memory_dc_created = True

            attempt.stage = "create_bitmap"
            _reset_last_error(ctypes)
            bitmap = create_compatible_bitmap(source_dc, bounds.width_px, bounds.height_px)
            if not bitmap:
                raise self._build_stage_error(
                    stage=attempt.stage,
                    message="CreateCompatibleBitmap failed.",
                    attempt=attempt,
                    bounds=bounds,
                    window_handle=window_handle,
                    requested_window_handle=requested_window_handle,
                    detected_foreground_window_handle=detected_foreground_window_handle,
                    environment_details=environment_details,
                    ctypes_module=ctypes,
                )
            attempt.bitmap_created = True

            attempt.stage = "select_bitmap"
            _reset_last_error(ctypes)
            previous_object = select_object(memory_dc, bitmap)
            if previous_object in (None, 0, hgdi_error):
                raise self._build_stage_error(
                    stage=attempt.stage,
                    message="SelectObject failed.",
                    attempt=attempt,
                    bounds=bounds,
                    window_handle=window_handle,
                    requested_window_handle=requested_window_handle,
                    detected_foreground_window_handle=detected_foreground_window_handle,
                    environment_details=environment_details,
                    ctypes_module=ctypes,
                )
            attempt.bitmap_selected = True

            selected_flag: int | None = None
            for print_window_flag in self._print_window_flag_order():
                attempt.stage = "print_window"
                _reset_last_error(ctypes)
                printed = print_window(window_handle, memory_dc, print_window_flag)
                if printed:
                    selected_flag = print_window_flag
                    attempt.print_window_attempts.append(
                        {
                            "print_window_flag": print_window_flag,
                            "print_window_flag_name": _print_window_flag_name(print_window_flag),
                            "printed": True,
                        }
                    )
                    break

                error_code = ctypes.get_last_error()
                attempt.print_window_attempts.append(
                    {
                        "print_window_flag": print_window_flag,
                        "print_window_flag_name": _print_window_flag_name(print_window_flag),
                        "printed": False,
                        "win32_error_code": error_code or None,
                        "win32_error_message": _format_win32_error(ctypes, error_code) if error_code else "",
                    }
                )

            if selected_flag is None:
                last_error_code = _last_print_window_error_code(attempt.print_window_attempts)
                raise self._build_stage_error(
                    stage=attempt.stage,
                    message="PrintWindow failed for all supported flags.",
                    attempt=attempt,
                    bounds=bounds,
                    window_handle=window_handle,
                    requested_window_handle=requested_window_handle,
                    detected_foreground_window_handle=detected_foreground_window_handle,
                    environment_details=environment_details,
                    ctypes_module=ctypes,
                    explicit_win32_error_code=last_error_code,
                    extra_diagnostics={
                        "failure_classification": "printwindow_failed",
                        **_environment_limitation_details(
                            stage="print_window",
                            win32_error_code=last_error_code,
                            environment_details=environment_details,
                        ),
                    },
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
                raise self._build_stage_error(
                    stage=attempt.stage,
                    message="GetDIBits failed.",
                    attempt=attempt,
                    bounds=bounds,
                    window_handle=window_handle,
                    requested_window_handle=requested_window_handle,
                    detected_foreground_window_handle=detected_foreground_window_handle,
                    environment_details=environment_details,
                    ctypes_module=ctypes,
                    extra_diagnostics={"failure_classification": "bitmap_readback_failed"},
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
                    "print_window_flag_used": selected_flag,
                    "print_window_flag_name": _print_window_flag_name(selected_flag),
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

    def _ensure_foreground_window_stable(
        self,
        *,
        expected_window_handle: int,
        phase: str,
        attempt: _PrintWindowAttemptState,
        bounds: ScreenBBox,
        requested_window_handle: int | None,
        detected_foreground_window_handle: int | None,
        environment_details: Mapping[str, object],
    ) -> None:
        current_foreground_window_handle = self._detect_foreground_window_handle()
        attempt.foreground_window_stable = current_foreground_window_handle == expected_window_handle
        if attempt.foreground_window_stable:
            return

        attempt.stage = "foreground_window_changed"
        raise self._build_stage_error(
            stage=attempt.stage,
            message="Foreground window changed during PrintWindow capture.",
            attempt=attempt,
            bounds=bounds,
            window_handle=expected_window_handle,
            requested_window_handle=requested_window_handle,
            detected_foreground_window_handle=detected_foreground_window_handle,
            environment_details=environment_details,
            extra_diagnostics={
                "failure_classification": "foreground_window_changed",
                "foreground_window_change_phase": phase,
                "current_foreground_window_handle": current_foreground_window_handle,
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

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
        except (AttributeError, OSError, ImportError) as exc:
            details["environment_probe_failed"] = True
            details["environment_probe_exception_type"] = type(exc).__name__
            details["environment_probe_exception_message"] = str(exc)
            return details

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
            details["input_desktop_error_code"] = error_code or None
            if error_code:
                details["input_desktop_error_message"] = _format_win32_error(ctypes, error_code)
        return details

    def _is_windows_platform(self) -> bool:
        return sys.platform == "win32"

    def _detect_foreground_window_handle(self) -> int | None:
        if not self._is_windows_platform():
            return None

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
        except (AttributeError, OSError, ImportError):
            return None

        get_foreground_window = user32.GetForegroundWindow
        get_foreground_window.argtypes = []
        get_foreground_window.restype = getattr(wintypes, "HWND", wintypes.HANDLE)
        return _normalize_handle(get_foreground_window())

    def _is_window_handle_valid(self, window_handle: int) -> bool:
        if not self._is_windows_platform():
            return False

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
        except (AttributeError, OSError, ImportError):
            return False

        is_window = user32.IsWindow
        is_window.argtypes = [getattr(wintypes, "HWND", wintypes.HANDLE)]
        is_window.restype = wintypes.BOOL
        _reset_last_error(ctypes)
        return bool(is_window(window_handle))

    def _is_window_visible(self, window_handle: int) -> bool:
        if not self._is_windows_platform():
            return False

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
        except (AttributeError, OSError, ImportError):
            return False

        is_window_visible = user32.IsWindowVisible
        is_window_visible.argtypes = [getattr(wintypes, "HWND", wintypes.HANDLE)]
        is_window_visible.restype = wintypes.BOOL
        _reset_last_error(ctypes)
        return bool(is_window_visible(window_handle))

    def _is_window_minimized(self, window_handle: int) -> bool:
        if not self._is_windows_platform():
            return False

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
        except (AttributeError, OSError, ImportError):
            return False

        is_iconic = user32.IsIconic
        is_iconic.argtypes = [getattr(wintypes, "HWND", wintypes.HANDLE)]
        is_iconic.restype = wintypes.BOOL
        _reset_last_error(ctypes)
        return bool(is_iconic(window_handle))

    def _get_window_bounds(self, window_handle: int) -> ScreenBBox:
        if not self._is_windows_platform():
            raise WindowsCaptureUnavailableError("Windows capture APIs are not available on this platform.")

        try:
            import ctypes
            from ctypes import wintypes
        except ImportError as exc:  # pragma: no cover - unavailable on supported Windows runtimes
            raise WindowsCaptureUnavailableError(str(exc)) from exc

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
        except (AttributeError, OSError) as exc:
            raise WindowsCaptureUnavailableError(str(exc)) from exc

        get_window_rect = user32.GetWindowRect
        get_window_rect.argtypes = [getattr(wintypes, "HWND", wintypes.HANDLE), ctypes.POINTER(RECT)]
        get_window_rect.restype = wintypes.BOOL

        rect = RECT()
        _reset_last_error(ctypes)
        if not get_window_rect(window_handle, ctypes.byref(rect)):
            error_code = ctypes.get_last_error()
            raise WindowsCaptureStageError(
                stage="get_window_rect",
                message="GetWindowRect failed.",
                win32_error_code=error_code or None,
                diagnostics={
                    "backend_name": self.backend_name,
                    "target_window_handle": window_handle,
                    "win32_error_message": _format_win32_error(ctypes, error_code) if error_code else "",
                },
            )

        return ScreenBBox(
            left_px=int(rect.left),
            top_px=int(rect.top),
            width_px=int(rect.right) - int(rect.left),
            height_px=int(rect.bottom) - int(rect.top),
        )

    def _print_window_flag_order(self) -> tuple[int, ...]:
        return (_PW_DEFAULT, _PW_RENDERFULLCONTENT)

    def _build_stage_error(
        self,
        *,
        stage: str,
        message: str,
        attempt: _PrintWindowAttemptState,
        bounds: ScreenBBox | None,
        window_handle: int | None,
        requested_window_handle: int | None,
        detected_foreground_window_handle: int | None,
        environment_details: Mapping[str, object],
        ctypes_module: object | None = None,
        explicit_win32_error_code: int | None = None,
        extra_diagnostics: Mapping[str, object] | None = None,
    ) -> WindowsCaptureStageError:
        diagnostics = attempt.to_details(
            backend_name=self.backend_name,
            bounds=bounds,
            window_handle=window_handle,
            requested_window_handle=requested_window_handle,
            detected_foreground_window_handle=detected_foreground_window_handle,
            environment_details=environment_details,
        )
        if extra_diagnostics is not None:
            diagnostics.update(dict(extra_diagnostics))

        win32_error_code = explicit_win32_error_code
        if win32_error_code is None and ctypes_module is not None:
            get_last_error = getattr(ctypes_module, "get_last_error", None)
            if callable(get_last_error):
                error_code = get_last_error()
                win32_error_code = error_code or None

        if win32_error_code:
            diagnostics["win32_error_message"] = _format_win32_error(ctypes_module, win32_error_code)

        return WindowsCaptureStageError(
            stage=stage,
            message=message,
            win32_error_code=win32_error_code,
            diagnostics=diagnostics,
        )

    def _enrich_stage_error(
        self,
        error: WindowsCaptureStageError,
        *,
        attempt: _PrintWindowAttemptState,
        bounds: ScreenBBox | None,
        window_handle: int | None,
        requested_window_handle: int | None,
        detected_foreground_window_handle: int | None,
        environment_details: Mapping[str, object],
    ) -> WindowsCaptureStageError:
        diagnostics = attempt.to_details(
            backend_name=self.backend_name,
            bounds=bounds,
            window_handle=window_handle,
            requested_window_handle=requested_window_handle,
            detected_foreground_window_handle=detected_foreground_window_handle,
            environment_details=environment_details,
        )
        diagnostics.update(error.diagnostics)
        diagnostics["failing_stage"] = error.stage
        return WindowsCaptureStageError(
            stage=error.stage,
            message=str(error),
            win32_error_code=error.win32_error_code,
            diagnostics=diagnostics,
        )


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


def _format_win32_error(ctypes_module: object | None, error_code: int) -> str:
    if ctypes_module is None:
        return ""
    try:
        return str(ctypes_module.FormatError(error_code)).strip()
    except (AttributeError, OSError):
        return ""


def _print_window_flag_name(print_window_flag: int) -> str:
    return {
        _PW_DEFAULT: "PW_DEFAULT",
        _PW_RENDERFULLCONTENT: "PW_RENDERFULLCONTENT",
    }.get(print_window_flag, f"UNKNOWN_{print_window_flag}")


def _last_print_window_error_code(print_window_attempts: list[dict[str, object]]) -> int | None:
    for attempt in reversed(print_window_attempts):
        win32_error_code = attempt.get("win32_error_code")
        if isinstance(win32_error_code, int) and win32_error_code > 0:
            return win32_error_code
    return None


def _environment_limitation_details(
    *,
    stage: str,
    win32_error_code: int | None,
    environment_details: Mapping[str, object],
) -> dict[str, object]:
    reasons: list[str] = []
    if environment_details.get("is_remote_session") is True:
        reasons.append("remote_session")
    if environment_details.get("input_desktop_accessible") is False:
        reasons.append("input_desktop_inaccessible")
    if stage == "print_window" and win32_error_code in (None, 0):
        reasons.append("printwindow_returned_failure_without_last_error")
    return {
        "environment_limitation_suspected": bool(reasons),
        "environment_limitation_reasons": tuple(reasons),
    }
