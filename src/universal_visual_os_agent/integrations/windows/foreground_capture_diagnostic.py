"""Manual foreground-window capture diagnostics for interactive Windows sessions."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import struct
import sys
from typing import Mapping, Protocol, Sequence

from universal_visual_os_agent.geometry import ScreenBBox
from universal_visual_os_agent.integrations.windows.capture import WindowsObserveOnlyCaptureProvider
from universal_visual_os_agent.integrations.windows.capture_models import (
    WindowsCaptureRuntimeMode,
    WindowsCaptureStageError,
    WindowsCaptureTarget,
)
from universal_visual_os_agent.integrations.windows.capture_printwindow import (
    WindowsForegroundWindowPrintCaptureBackend,
)
from universal_visual_os_agent.perception import CaptureProvider, CaptureResult, CapturedFrame


@dataclass(slots=True, frozen=True, kw_only=True)
class ForegroundWindowMetadata:
    """Best-effort foreground window metadata for local diagnostics."""

    handle: int
    title: str | None = None
    class_name: str | None = None
    bounds: ScreenBBox | None = None
    is_visible: bool | None = None
    is_minimized: bool | None = None

    def __post_init__(self) -> None:
        if self.handle <= 0:
            raise ValueError("handle must be positive.")

    def to_summary(self) -> dict[str, object]:
        """Return a display-friendly metadata summary."""

        return {
            "handle": self.handle,
            "title": self.title,
            "class_name": self.class_name,
            "bounds": None if self.bounds is None else _bbox_to_summary(self.bounds),
            "is_visible": self.is_visible,
            "is_minimized": self.is_minimized,
        }


@dataclass(slots=True, frozen=True, kw_only=True)
class ForegroundWindowMetadataResult:
    """Structured foreground-window metadata probe result."""

    foreground_window_detected: bool
    foreground_window_handle: int | None = None
    metadata: ForegroundWindowMetadata | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.foreground_window_detected and self.foreground_window_handle is None:
            raise ValueError("foreground_window_handle is required when a window is detected.")
        if not self.foreground_window_detected and self.foreground_window_handle is not None:
            raise ValueError("foreground_window_handle must be omitted when no window is detected.")
        if self.metadata is not None and self.foreground_window_handle != self.metadata.handle:
            raise ValueError("foreground_window_handle must match metadata.handle.")
        if self.error_code is None and self.error_message is not None:
            raise ValueError("error_message requires error_code.")


class ForegroundWindowMetadataReader(Protocol):
    """Read-only diagnostic probe for foreground window metadata."""

    def read_foreground_window_metadata(self) -> ForegroundWindowMetadataResult:
        """Return best-effort metadata for the current foreground window."""


@dataclass(slots=True, frozen=True, kw_only=True)
class ForegroundCaptureDiagnosticResult:
    """Structured output for the manual foreground-window diagnostic utility."""

    provider_name: str
    foreground_window_detected: bool
    foreground_window_handle: int | None
    foreground_window_metadata: ForegroundWindowMetadata | None = None
    metadata_error_code: str | None = None
    metadata_error_message: str | None = None
    metadata_details: Mapping[str, object] = field(default_factory=dict)
    capture_succeeded: bool = False
    capture_error_code: str | None = None
    capture_error_message: str | None = None
    capture_details: Mapping[str, object] = field(default_factory=dict)
    captured_frame_summary: Mapping[str, object] = field(default_factory=dict)
    saved_image_path: str | None = None

    def __post_init__(self) -> None:
        if not self.provider_name:
            raise ValueError("provider_name must not be empty.")
        if self.foreground_window_detected and self.foreground_window_handle is None:
            raise ValueError("foreground_window_handle is required when a window is detected.")
        if not self.foreground_window_detected and self.foreground_window_handle is not None:
            raise ValueError("foreground_window_handle must be omitted when no window is detected.")
        if self.capture_succeeded and self.capture_error_code is not None:
            raise ValueError("capture_error_code must be omitted when capture succeeds.")
        if not self.capture_succeeded and self.saved_image_path is not None:
            raise ValueError("saved_image_path is only valid after a successful capture.")

    def to_display_dict(self) -> dict[str, object]:
        """Return a JSON-serializable diagnostic summary."""

        return _sanitize_value(
            {
                "provider_name": self.provider_name,
                "foreground_window_detected": self.foreground_window_detected,
                "foreground_window_handle": self.foreground_window_handle,
                "foreground_window_metadata": (
                    None if self.foreground_window_metadata is None else self.foreground_window_metadata.to_summary()
                ),
                "metadata_error_code": self.metadata_error_code,
                "metadata_error_message": self.metadata_error_message,
                "metadata_details": dict(self.metadata_details),
                "capture_succeeded": self.capture_succeeded,
                "capture_error_code": self.capture_error_code,
                "capture_error_message": self.capture_error_message,
                "capture_details": dict(self.capture_details),
                "captured_frame_summary": dict(self.captured_frame_summary),
                "saved_image_path": self.saved_image_path,
            }
        )


class WindowsForegroundWindowMetadataReader:
    """Best-effort Win32 metadata reader for the current foreground window."""

    def __init__(self, *, backend: WindowsForegroundWindowPrintCaptureBackend | None = None) -> None:
        self._backend = WindowsForegroundWindowPrintCaptureBackend() if backend is None else backend

    def read_foreground_window_metadata(self) -> ForegroundWindowMetadataResult:
        if not self._backend._is_windows_platform():
            return ForegroundWindowMetadataResult(
                foreground_window_detected=False,
                error_code="platform_unavailable",
                error_message="Foreground-window metadata is only available on Windows.",
                details={"platform": sys.platform},
            )

        foreground_window_handle = self._backend._detect_foreground_window_handle()
        if foreground_window_handle is None:
            return ForegroundWindowMetadataResult(
                foreground_window_detected=False,
                details={"platform": sys.platform, "reason": "No foreground window detected."},
            )

        details: dict[str, object] = {"platform": sys.platform}
        if not self._backend._is_window_handle_valid(foreground_window_handle):
            return ForegroundWindowMetadataResult(
                foreground_window_detected=True,
                foreground_window_handle=foreground_window_handle,
                error_code="invalid_window_handle",
                error_message="Foreground window handle is invalid or inaccessible.",
                details=details,
            )

        bounds, bounds_details = self._try_get_bounds(foreground_window_handle)
        details.update(bounds_details)
        details["title_lookup_succeeded"] = False
        details["class_name_lookup_succeeded"] = False
        title = None
        class_name = None
        try:
            title = self._get_window_title(foreground_window_handle)
            details["title_lookup_succeeded"] = True
        except Exception as exc:  # noqa: BLE001 - diagnostics must stay failure-safe
            details["title_lookup_exception_type"] = type(exc).__name__
            details["title_lookup_exception_message"] = str(exc)
        try:
            class_name = self._get_window_class_name(foreground_window_handle)
            details["class_name_lookup_succeeded"] = True
        except Exception as exc:  # noqa: BLE001 - diagnostics must stay failure-safe
            details["class_name_lookup_exception_type"] = type(exc).__name__
            details["class_name_lookup_exception_message"] = str(exc)

        metadata = ForegroundWindowMetadata(
            handle=foreground_window_handle,
            title=title,
            class_name=class_name,
            bounds=bounds,
            is_visible=self._backend._is_window_visible(foreground_window_handle),
            is_minimized=self._backend._is_window_minimized(foreground_window_handle),
        )
        return ForegroundWindowMetadataResult(
            foreground_window_detected=True,
            foreground_window_handle=foreground_window_handle,
            metadata=metadata,
            details=details,
        )

    def _try_get_bounds(self, foreground_window_handle: int) -> tuple[ScreenBBox | None, dict[str, object]]:
        try:
            bounds = self._backend._get_window_bounds(foreground_window_handle)
        except WindowsCaptureStageError as exc:
            return None, {
                "bounds_lookup_succeeded": False,
                "bounds_error_code": exc.stage,
                "bounds_error_message": str(exc),
            }
        return bounds, {"bounds_lookup_succeeded": True}

    def _get_window_title(self, foreground_window_handle: int) -> str | None:
        import ctypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        get_window_text_length = user32.GetWindowTextLengthW
        get_window_text_length.argtypes = [ctypes.c_void_p]
        get_window_text_length.restype = ctypes.c_int

        get_window_text = user32.GetWindowTextW
        get_window_text.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        get_window_text.restype = ctypes.c_int

        title_length = max(get_window_text_length(foreground_window_handle), 0)
        buffer = ctypes.create_unicode_buffer(title_length + 1)
        get_window_text(foreground_window_handle, buffer, len(buffer))
        return buffer.value or None

    def _get_window_class_name(self, foreground_window_handle: int) -> str | None:
        import ctypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        get_class_name = user32.GetClassNameW
        get_class_name.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        get_class_name.restype = ctypes.c_int

        buffer = ctypes.create_unicode_buffer(256)
        class_name_length = get_class_name(foreground_window_handle, buffer, len(buffer))
        if class_name_length <= 0:
            return None
        return buffer.value or None


def run_foreground_window_capture_diagnostic(
    *,
    output_path: str | Path | None = None,
    metadata_reader: ForegroundWindowMetadataReader | None = None,
    capture_provider: CaptureProvider | None = None,
) -> ForegroundCaptureDiagnosticResult:
    """Run a local read-only foreground-window capture diagnostic."""

    backend = WindowsForegroundWindowPrintCaptureBackend()
    resolved_metadata_reader = WindowsForegroundWindowMetadataReader(backend=backend) if metadata_reader is None else metadata_reader
    resolved_capture_provider = (
        WindowsObserveOnlyCaptureProvider(
            capture_target=WindowsCaptureTarget.foreground_window,
            capture_backends=(backend,),
            runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
        )
        if capture_provider is None
        else capture_provider
    )

    metadata_result = _safe_read_foreground_window_metadata(resolved_metadata_reader)
    capture_result = _safe_capture_frame(resolved_capture_provider)
    saved_image_path = (
        None
        if not capture_result.success or capture_result.frame is None or output_path is None
        else str(_write_frame_bmp(capture_result.frame, Path(output_path)))
    )

    return ForegroundCaptureDiagnosticResult(
        provider_name=capture_result.provider_name,
        foreground_window_detected=metadata_result.foreground_window_detected,
        foreground_window_handle=metadata_result.foreground_window_handle,
        foreground_window_metadata=metadata_result.metadata,
        metadata_error_code=metadata_result.error_code,
        metadata_error_message=metadata_result.error_message,
        metadata_details=dict(metadata_result.details),
        capture_succeeded=capture_result.success,
        capture_error_code=capture_result.error_code,
        capture_error_message=capture_result.error_message,
        capture_details=dict(capture_result.details),
        captured_frame_summary={} if capture_result.frame is None else _frame_to_summary(capture_result.frame),
        saved_image_path=saved_image_path,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the manual foreground-window diagnostic utility."""

    parser = argparse.ArgumentParser(
        description="Read-only foreground-window capture diagnostic for interactive Windows sessions."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional BMP output path. The image is written only if capture succeeds.",
    )
    args = parser.parse_args(argv)

    result = run_foreground_window_capture_diagnostic(output_path=args.output)
    print(json.dumps(result.to_display_dict(), indent=2, sort_keys=True))
    return 0 if result.capture_succeeded else 1


def _safe_read_foreground_window_metadata(
    metadata_reader: ForegroundWindowMetadataReader,
) -> ForegroundWindowMetadataResult:
    try:
        return metadata_reader.read_foreground_window_metadata()
    except Exception as exc:  # noqa: BLE001 - diagnostics must stay failure-safe
        return ForegroundWindowMetadataResult(
            foreground_window_detected=False,
            error_code="metadata_probe_exception",
            error_message=str(exc),
            details={"exception_type": type(exc).__name__},
        )


def _safe_capture_frame(capture_provider: CaptureProvider) -> CaptureResult:
    try:
        return capture_provider.capture_frame()
    except Exception as exc:  # noqa: BLE001 - diagnostics must stay failure-safe
        return CaptureResult.failure(
            provider_name=type(capture_provider).__name__,
            error_code="diagnostic_capture_exception",
            error_message=str(exc),
            details={"exception_type": type(exc).__name__},
        )


def _write_frame_bmp(frame: CapturedFrame, output_path: Path) -> Path:
    if frame.payload is None:
        raise ValueError("A capture payload is required to write a diagnostic image.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image_size = frame.payload.row_stride_bytes * frame.payload.height
    file_header = struct.pack("<2sIHHI", b"BM", 14 + 40 + image_size, 0, 0, 14 + 40)
    info_header = struct.pack(
        "<IiiHHIIiiII",
        40,
        frame.payload.width,
        -frame.payload.height,
        1,
        32,
        0,
        image_size,
        2835,
        2835,
        0,
        0,
    )
    output_path.write_bytes(file_header + info_header + frame.payload.image_bytes)
    return output_path


def _frame_to_summary(frame: CapturedFrame) -> dict[str, object]:
    return {
        "frame_id": frame.frame_id,
        "width": frame.width,
        "height": frame.height,
        "captured_at": frame.captured_at.isoformat(),
        "source": frame.source,
        "metadata": dict(frame.metadata),
    }


def _bbox_to_summary(bounds: ScreenBBox) -> dict[str, int]:
    return {
        "left_px": bounds.left_px,
        "top_px": bounds.top_px,
        "width_px": bounds.width_px,
        "height_px": bounds.height_px,
    }


def _sanitize_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _sanitize_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, ScreenBBox):
        return _bbox_to_summary(value)
    if isinstance(value, datetime):
        return value.isoformat()
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return value


if __name__ == "__main__":
    raise SystemExit(main())
