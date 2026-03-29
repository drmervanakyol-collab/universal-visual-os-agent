"""Read-only Windows screen capture adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from universal_visual_os_agent.geometry import ScreenBBox, ScreenMetricsProvider
from universal_visual_os_agent.integrations.windows.screen_metrics import WindowsScreenMetricsProvider
from universal_visual_os_agent.perception import (
    CaptureProvider,
    CaptureResult,
    CapturedFrame,
    FrameImagePayload,
    FramePixelFormat,
)

_BI_RGB = 0
_DIB_RGB_COLORS = 0
_SRCCOPY = 0x00CC0020


class WindowsCaptureUnavailableError(RuntimeError):
    """Raised when Windows screen capture APIs are unavailable."""


@dataclass(slots=True, frozen=True, kw_only=True)
class RawWindowsCapture:
    """Raw image data captured from the Windows desktop."""

    width: int
    height: int
    origin_x_px: int
    origin_y_px: int
    row_stride_bytes: int
    image_bytes: bytes
    pixel_format: FramePixelFormat = FramePixelFormat.bgra_8888
    captured_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("width must be positive.")
        if self.height <= 0:
            raise ValueError("height must be positive.")
        if self.row_stride_bytes <= 0:
            raise ValueError("row_stride_bytes must be positive.")
        expected_length = self.row_stride_bytes * self.height
        if len(self.image_bytes) != expected_length:
            raise ValueError("image_bytes length must match row_stride_bytes * height.")
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware.")


class WindowsScreenCaptureApi(Protocol):
    """Low-level Windows desktop capture contract."""

    def capture_bounds(self, bounds: ScreenBBox) -> RawWindowsCapture:
        """Capture the provided bounds from the current virtual desktop."""


class CtypesWindowsScreenCaptureApi:
    """Win32-backed capture implementation using only the standard library."""

    def capture_bounds(self, bounds: ScreenBBox) -> RawWindowsCapture:
        """Capture the provided virtual-desktop bounds or raise a safe error."""

        import sys

        if sys.platform != "win32":
            raise WindowsCaptureUnavailableError("Windows capture APIs are not available on this platform.")

        if bounds.width_px <= 0 or bounds.height_px <= 0:
            raise ValueError("Capture bounds must be positive.")

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

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

        get_dc = user32.GetDC
        get_dc.argtypes = [hwnd_type]
        get_dc.restype = hdc_type

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

        screen_dc = get_dc(None)
        if not screen_dc:
            error_code = ctypes.get_last_error()
            raise OSError(error_code, "GetDC failed.")

        memory_dc = create_compatible_dc(screen_dc)
        if not memory_dc:
            release_dc(None, screen_dc)
            error_code = ctypes.get_last_error()
            raise OSError(error_code, "CreateCompatibleDC failed.")

        bitmap = create_compatible_bitmap(screen_dc, bounds.width_px, bounds.height_px)
        if not bitmap:
            delete_dc(memory_dc)
            release_dc(None, screen_dc)
            error_code = ctypes.get_last_error()
            raise OSError(error_code, "CreateCompatibleBitmap failed.")

        previous_object = select_object(memory_dc, bitmap)
        if not previous_object:
            delete_object(bitmap)
            delete_dc(memory_dc)
            release_dc(None, screen_dc)
            error_code = ctypes.get_last_error()
            raise OSError(error_code, "SelectObject failed.")

        try:
            if not bit_blt(
                memory_dc,
                0,
                0,
                bounds.width_px,
                bounds.height_px,
                screen_dc,
                bounds.left_px,
                bounds.top_px,
                _SRCCOPY,
            ):
                error_code = ctypes.get_last_error()
                raise OSError(error_code, "BitBlt failed.")

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
                error_code = ctypes.get_last_error()
                raise OSError(error_code, "GetDIBits failed.")

            return RawWindowsCapture(
                width=bounds.width_px,
                height=bounds.height_px,
                origin_x_px=bounds.left_px,
                origin_y_px=bounds.top_px,
                row_stride_bytes=row_stride_bytes,
                image_bytes=image_buffer.raw,
            )
        finally:
            select_object(memory_dc, previous_object)
            delete_object(bitmap)
            delete_dc(memory_dc)
            release_dc(None, screen_dc)


class WindowsObserveOnlyCaptureProvider(CaptureProvider):
    """Read-only Windows desktop capture provider for observe-only use."""

    def __init__(
        self,
        *,
        screen_metrics_provider: ScreenMetricsProvider | None = None,
        capture_api: WindowsScreenCaptureApi | None = None,
    ) -> None:
        self._screen_metrics_provider = (
            WindowsScreenMetricsProvider() if screen_metrics_provider is None else screen_metrics_provider
        )
        self._capture_api = CtypesWindowsScreenCaptureApi() if capture_api is None else capture_api

    def capture_frame(self) -> CaptureResult:
        """Capture the current virtual desktop or return a safe failure result."""

        metrics_result = self._screen_metrics_provider.get_virtual_desktop_metrics()
        if not metrics_result.success or metrics_result.metrics is None:
            return CaptureResult.failure(
                provider_name=self.__class__.__name__,
                error_code="screen_metrics_unavailable",
                error_message=metrics_result.error_message or "Screen metrics are unavailable.",
                details={
                    "metrics_error_code": metrics_result.error_code or "unknown",
                },
            )

        try:
            raw_capture = self._capture_api.capture_bounds(metrics_result.metrics.bounds)
            frame = _build_captured_frame(
                raw_capture,
                provider_name=self.__class__.__name__,
                display_count=len(metrics_result.metrics.displays),
            )
        except WindowsCaptureUnavailableError as exc:
            return CaptureResult.failure(
                provider_name=self.__class__.__name__,
                error_code="capture_unavailable",
                error_message=str(exc),
            )
        except ValueError as exc:
            return CaptureResult.failure(
                provider_name=self.__class__.__name__,
                error_code="invalid_capture_data",
                error_message=str(exc),
            )
        except OSError as exc:
            return CaptureResult.failure(
                provider_name=self.__class__.__name__,
                error_code="windows_api_error",
                error_message=str(exc),
            )

        return CaptureResult.ok(
            provider_name=self.__class__.__name__,
            frame=frame,
            details={
                "display_count": len(metrics_result.metrics.displays),
                "capture_origin_x_px": raw_capture.origin_x_px,
                "capture_origin_y_px": raw_capture.origin_y_px,
            },
        )


def _build_captured_frame(
    raw_capture: RawWindowsCapture,
    *,
    provider_name: str,
    display_count: int,
) -> CapturedFrame:
    payload = FrameImagePayload(
        width=raw_capture.width,
        height=raw_capture.height,
        row_stride_bytes=raw_capture.row_stride_bytes,
        image_bytes=raw_capture.image_bytes,
        pixel_format=raw_capture.pixel_format,
    )
    captured_at_utc = raw_capture.captured_at.astimezone(UTC)
    frame_id = f"capture-{captured_at_utc.strftime('%Y%m%dT%H%M%S%fZ')}"
    return CapturedFrame(
        frame_id=frame_id,
        width=raw_capture.width,
        height=raw_capture.height,
        captured_at=raw_capture.captured_at,
        payload=payload,
        source=provider_name,
        metadata={
            "origin_x_px": raw_capture.origin_x_px,
            "origin_y_px": raw_capture.origin_y_px,
            "display_count": display_count,
        },
    )
