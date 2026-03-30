"""Manual DXcam full-desktop capture diagnostics for interactive Windows sessions."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import struct
import sys
from typing import Mapping, Protocol, Sequence

from universal_visual_os_agent.geometry import (
    ScreenBBox,
    ScreenMetricsQueryResult,
    VirtualDesktopMetrics,
)
from universal_visual_os_agent.integrations.windows.capture_dxcam import (
    WindowsDxcamCaptureBackend,
)
from universal_visual_os_agent.integrations.windows.capture_models import (
    RawWindowsCapture,
    WindowsCaptureBackendCapability,
    WindowsCaptureRequest,
    WindowsCaptureStageError,
    WindowsCaptureTarget,
)
from universal_visual_os_agent.integrations.windows.screen_metrics import (
    WindowsScreenMetricsProvider,
)
from universal_visual_os_agent.perception import FramePixelFormat


class _ScreenMetricsProvider(Protocol):
    """Protocol for diagnostic screen-metrics lookups."""

    def get_virtual_desktop_metrics(self) -> ScreenMetricsQueryResult:
        """Return virtual desktop metrics for the current session."""


class _DxcamDiagnosticBackend(Protocol):
    """Protocol for DXcam capability and capture diagnostics."""

    backend_name: str

    def detect_capability(self, request: WindowsCaptureRequest) -> WindowsCaptureBackendCapability:
        """Return structured DXcam capability details for the request."""

    def capture(self, request: WindowsCaptureRequest) -> RawWindowsCapture:
        """Attempt a read-only DXcam full-desktop capture."""


@dataclass(slots=True, frozen=True, kw_only=True)
class DxcamBackendAttemptDiagnostic:
    """Structured summary for one DXcam backend initialization attempt."""

    dxcam_backend: str
    available: bool
    failing_stage: str | None = None
    reason: str | None = None
    hresult: int | None = None
    exception_type: str | None = None
    exception_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.dxcam_backend:
            raise ValueError("dxcam_backend must not be empty.")

    def to_summary(self) -> dict[str, object]:
        """Return a JSON-serializable attempt summary."""

        return _sanitize_value(
            {
                "dxcam_backend": self.dxcam_backend,
                "available": self.available,
                "failing_stage": self.failing_stage,
                "reason": self.reason,
                "hresult": self.hresult,
                "exception_type": self.exception_type,
                "exception_message": self.exception_message,
                "details": dict(self.details),
            }
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class DxcamCaptureDiagnosticResult:
    """Structured output for manual DXcam full-desktop diagnostics."""

    diagnostic_name: str
    metrics_lookup_succeeded: bool
    backend_available: bool
    requested_target: WindowsCaptureTarget
    availability_reason: str | None = None
    selected_dxcam_backend: str | None = None
    failure_backend: str | None = None
    failure_stage: str | None = None
    failure_hresult: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    process_context: Mapping[str, object] = field(default_factory=dict)
    output_selection: Mapping[str, object] = field(default_factory=dict)
    monitor_metadata: Mapping[str, object] = field(default_factory=dict)
    backend_details: Mapping[str, object] = field(default_factory=dict)
    attempts: tuple[DxcamBackendAttemptDiagnostic, ...] = ()
    capture_attempted: bool = False
    capture_succeeded: bool = False
    capture_error_code: str | None = None
    capture_error_message: str | None = None
    capture_details: Mapping[str, object] = field(default_factory=dict)
    captured_frame_summary: Mapping[str, object] = field(default_factory=dict)
    saved_image_path: str | None = None
    image_save_error_code: str | None = None
    image_save_error_message: str | None = None

    def __post_init__(self) -> None:
        if not self.diagnostic_name:
            raise ValueError("diagnostic_name must not be empty.")
        if self.error_code is None and self.error_message is not None:
            raise ValueError("error_message requires error_code.")
        if self.backend_available and self.selected_dxcam_backend is None:
            raise ValueError("selected_dxcam_backend is required when backend_available is True.")
        if self.capture_succeeded and not self.capture_attempted:
            raise ValueError("capture_attempted must be True when capture_succeeded is True.")
        if self.capture_error_code is None and self.capture_error_message is not None:
            raise ValueError("capture_error_message requires capture_error_code.")
        if self.saved_image_path is not None and not self.capture_succeeded:
            raise ValueError("saved_image_path is only valid after successful capture.")
        if self.image_save_error_code is None and self.image_save_error_message is not None:
            raise ValueError("image_save_error_message requires image_save_error_code.")

    def to_display_dict(self) -> dict[str, object]:
        """Return a JSON-serializable diagnostic summary."""

        return _sanitize_value(
            {
                "diagnostic_name": self.diagnostic_name,
                "metrics_lookup_succeeded": self.metrics_lookup_succeeded,
                "backend_available": self.backend_available,
                "requested_target": self.requested_target,
                "availability_reason": self.availability_reason,
                "selected_dxcam_backend": self.selected_dxcam_backend,
                "failure_backend": self.failure_backend,
                "failure_stage": self.failure_stage,
                "failure_hresult": self.failure_hresult,
                "error_code": self.error_code,
                "error_message": self.error_message,
                "process_context": dict(self.process_context),
                "output_selection": dict(self.output_selection),
                "monitor_metadata": dict(self.monitor_metadata),
                "backend_details": dict(self.backend_details),
                "attempts": [attempt.to_summary() for attempt in self.attempts],
                "capture_attempted": self.capture_attempted,
                "capture_succeeded": self.capture_succeeded,
                "capture_error_code": self.capture_error_code,
                "capture_error_message": self.capture_error_message,
                "capture_details": dict(self.capture_details),
                "captured_frame_summary": dict(self.captured_frame_summary),
                "saved_image_path": self.saved_image_path,
                "image_save_error_code": self.image_save_error_code,
                "image_save_error_message": self.image_save_error_message,
            }
        )


def run_dxcam_capture_diagnostic(
    *,
    output_path: str | Path | None = None,
    screen_metrics_provider: _ScreenMetricsProvider | None = None,
    capture_backend: _DxcamDiagnosticBackend | None = None,
) -> DxcamCaptureDiagnosticResult:
    """Run a local read-only DXcam diagnostic for full-desktop capture."""

    diagnostic_name = "WindowsDxcamCaptureDiagnostic"
    resolved_screen_metrics_provider = (
        WindowsScreenMetricsProvider() if screen_metrics_provider is None else screen_metrics_provider
    )
    resolved_capture_backend = WindowsDxcamCaptureBackend() if capture_backend is None else capture_backend

    try:
        metrics_result = resolved_screen_metrics_provider.get_virtual_desktop_metrics()
    except Exception as exc:  # noqa: BLE001 - diagnostics must remain failure-safe
        return DxcamCaptureDiagnosticResult(
            diagnostic_name=diagnostic_name,
            metrics_lookup_succeeded=False,
            backend_available=False,
            requested_target=WindowsCaptureTarget.virtual_desktop,
            error_code="metrics_probe_exception",
            error_message=str(exc),
            process_context=_basic_process_context(),
            output_selection=_build_output_selection(bounds=None, backend_details={}),
            monitor_metadata={},
            backend_details={},
        )

    if not metrics_result.success or metrics_result.metrics is None:
        return DxcamCaptureDiagnosticResult(
            diagnostic_name=diagnostic_name,
            metrics_lookup_succeeded=False,
            backend_available=False,
            requested_target=WindowsCaptureTarget.virtual_desktop,
            error_code="screen_metrics_unavailable",
            error_message=metrics_result.error_message,
            process_context=_basic_process_context(),
            output_selection=_build_output_selection(bounds=None, backend_details={}),
            monitor_metadata=_build_monitor_metadata(metrics_result),
            backend_details={},
        )

    request = WindowsCaptureRequest(
        target=WindowsCaptureTarget.virtual_desktop,
        bounds=metrics_result.metrics.bounds,
    )
    try:
        capability = resolved_capture_backend.detect_capability(request)
    except Exception as exc:  # noqa: BLE001 - diagnostics must remain failure-safe
        return DxcamCaptureDiagnosticResult(
            diagnostic_name=diagnostic_name,
            metrics_lookup_succeeded=True,
            backend_available=False,
            requested_target=request.target,
            error_code="diagnostic_probe_exception",
            error_message=str(exc),
            process_context=_basic_process_context(),
            output_selection=_build_output_selection(bounds=request.bounds, backend_details={}),
            monitor_metadata=_build_monitor_metadata(metrics_result),
            backend_details={},
        )

    backend_details = dict(capability.details)
    attempts = _build_attempts(backend_details.get("dxcam_attempts"))
    failure_attempt = _first_failure_attempt(attempts)
    base_kwargs = {
        "diagnostic_name": diagnostic_name,
        "metrics_lookup_succeeded": True,
        "backend_available": capability.available,
        "requested_target": request.target,
        "availability_reason": capability.reason,
        "selected_dxcam_backend": _string_or_none(backend_details.get("dxcam_backend_used")),
        "failure_backend": None if failure_attempt is None else failure_attempt.dxcam_backend,
        "failure_stage": None if failure_attempt is None else failure_attempt.failing_stage,
        "failure_hresult": None if failure_attempt is None else failure_attempt.hresult,
        "process_context": _build_process_context(backend_details),
        "output_selection": _build_output_selection(bounds=request.bounds, backend_details=backend_details),
        "monitor_metadata": _build_monitor_metadata(metrics_result),
        "backend_details": _build_backend_details(backend_details),
        "attempts": attempts,
    }

    if not capability.available:
        return DxcamCaptureDiagnosticResult(**base_kwargs)

    try:
        raw_capture = resolved_capture_backend.capture(request)
    except WindowsCaptureStageError as exc:
        return DxcamCaptureDiagnosticResult(
            **base_kwargs,
            capture_attempted=True,
            capture_succeeded=False,
            capture_error_code=_capture_error_code_for_stage(exc.stage),
            capture_error_message=str(exc),
            capture_details={
                "failing_stage": exc.stage,
                "win32_error_code": exc.win32_error_code,
                **exc.diagnostics,
            },
        )
    except ValueError as exc:
        return DxcamCaptureDiagnosticResult(
            **base_kwargs,
            capture_attempted=True,
            capture_succeeded=False,
            capture_error_code="invalid_capture_data",
            capture_error_message=str(exc),
            capture_details={"exception_type": type(exc).__name__},
        )
    except Exception as exc:  # noqa: BLE001 - diagnostics must remain failure-safe
        return DxcamCaptureDiagnosticResult(
            **base_kwargs,
            capture_attempted=True,
            capture_succeeded=False,
            capture_error_code="diagnostic_capture_exception",
            capture_error_message=str(exc),
            capture_details={"exception_type": type(exc).__name__},
        )

    frame_summary = _raw_capture_to_summary(raw_capture)
    saved_image_path: str | None = None
    image_save_error_code: str | None = None
    image_save_error_message: str | None = None
    if output_path is not None:
        try:
            saved_image_path = str(_write_capture_bmp(raw_capture, Path(output_path)))
        except Exception as exc:  # noqa: BLE001 - diagnostics must remain failure-safe
            image_save_error_code = "diagnostic_image_save_failed"
            image_save_error_message = str(exc)

    return DxcamCaptureDiagnosticResult(
        **base_kwargs,
        capture_attempted=True,
        capture_succeeded=True,
        capture_details={
            "backend_name": raw_capture.metadata.get("backend_name"),
            "capture_source_strategy": raw_capture.metadata.get("capture_source_strategy"),
            "pixel_format": raw_capture.pixel_format,
            "image_save_requested": output_path is not None,
        },
        captured_frame_summary=frame_summary,
        saved_image_path=saved_image_path,
        image_save_error_code=image_save_error_code,
        image_save_error_message=image_save_error_message,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the manual DXcam capture diagnostic utility."""

    parser = argparse.ArgumentParser(
        description="Read-only DXcam full-desktop capture diagnostic for interactive Windows sessions."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional BMP output path. The image is written only if capture succeeds.",
    )
    args = parser.parse_args(argv)

    result = run_dxcam_capture_diagnostic(output_path=args.output)
    print(json.dumps(result.to_display_dict(), indent=2, sort_keys=True))
    return 0 if result.capture_succeeded else 1


def _build_attempts(raw_attempts: object) -> tuple[DxcamBackendAttemptDiagnostic, ...]:
    if not isinstance(raw_attempts, tuple):
        return ()

    attempts: list[DxcamBackendAttemptDiagnostic] = []
    for raw_attempt in raw_attempts:
        if not isinstance(raw_attempt, Mapping):
            continue
        dxcam_backend = raw_attempt.get("dxcam_backend")
        if not isinstance(dxcam_backend, str) or not dxcam_backend:
            continue
        attempts.append(
            DxcamBackendAttemptDiagnostic(
                dxcam_backend=dxcam_backend,
                available=bool(raw_attempt.get("available")),
                failing_stage=_string_or_none(raw_attempt.get("failing_stage")),
                reason=_string_or_none(raw_attempt.get("reason")),
                hresult=_int_or_none(raw_attempt.get("hresult")),
                exception_type=_string_or_none(raw_attempt.get("exception_type")),
                exception_message=_string_or_none(raw_attempt.get("exception_message")),
                details={
                    str(key): value
                    for key, value in raw_attempt.items()
                    if key
                    not in {
                        "dxcam_backend",
                        "available",
                        "failing_stage",
                        "reason",
                        "hresult",
                        "exception_type",
                        "exception_message",
                    }
                },
            )
        )
    return tuple(attempts)


def _first_failure_attempt(
    attempts: tuple[DxcamBackendAttemptDiagnostic, ...],
) -> DxcamBackendAttemptDiagnostic | None:
    for attempt in attempts:
        if not attempt.available:
            return attempt
    return None


def _build_process_context(backend_details: Mapping[str, object]) -> dict[str, object]:
    process_context = _basic_process_context()
    session_name = _string_or_none(backend_details.get("session_name"))
    input_desktop_accessible = _bool_or_none(backend_details.get("input_desktop_accessible"))
    is_remote_session = _bool_or_none(backend_details.get("is_remote_session"))

    process_context.update(
        {
            "platform": _string_or_default(backend_details.get("platform"), sys.platform),
            "session_name": session_name,
            "is_remote_session": is_remote_session,
            "input_desktop_accessible": input_desktop_accessible,
            "input_desktop_error_code": _int_or_none(backend_details.get("input_desktop_error_code")),
            "input_desktop_error_message": _string_or_none(backend_details.get("input_desktop_error_message")),
            "environment_limitation_suspected": _bool_or_none(
                backend_details.get("environment_limitation_suspected")
            ),
            "environment_limitation_reasons": _string_tuple(
                backend_details.get("environment_limitation_reasons")
            ),
        }
    )

    interactive_indicators: list[str] = []
    if session_name is not None and session_name.upper() not in {"SERVICE", "SERVICES"}:
        interactive_indicators.append("session_name")
    if input_desktop_accessible is True:
        interactive_indicators.append("input_desktop_accessible")
    if process_context["stdin_isatty"] is True:
        interactive_indicators.append("stdin_isatty")
    if process_context["stdout_isatty"] is True:
        interactive_indicators.append("stdout_isatty")

    process_context["interactive_indicators"] = tuple(interactive_indicators)
    process_context["process_appears_interactive"] = bool(interactive_indicators)
    return process_context


def _basic_process_context() -> dict[str, object]:
    return {
        "process_id": os.getpid(),
        "python_executable": sys.executable,
        "stdin_isatty": _safe_isatty(getattr(sys, "stdin", None)),
        "stdout_isatty": _safe_isatty(getattr(sys, "stdout", None)),
    }


def _build_output_selection(*, bounds: ScreenBBox | None, backend_details: Mapping[str, object]) -> dict[str, object]:
    return {
        "target": WindowsCaptureTarget.virtual_desktop,
        "requested_bounds": None if bounds is None else _bbox_to_summary(bounds),
        "requested_device_idx": _int_or_none(backend_details.get("requested_device_idx")),
        "requested_output_idx": _int_or_none(backend_details.get("requested_output_idx")),
        "requested_region": _sanitize_value(backend_details.get("requested_region")),
        "requested_output_color": _string_or_none(backend_details.get("requested_output_color")),
        "requested_processor_backend": _string_or_none(backend_details.get("requested_processor_backend")),
        "requested_max_buffer_len": _int_or_none(backend_details.get("requested_max_buffer_len")),
        "primary_output_layout_required": _bool_or_none(backend_details.get("primary_output_layout_required")),
    }


def _build_monitor_metadata(metrics_result: ScreenMetricsQueryResult) -> dict[str, object]:
    metadata: dict[str, object] = {
        "metrics_provider_name": metrics_result.provider_name,
        "metrics_details": dict(metrics_result.details),
    }
    if not metrics_result.success or metrics_result.metrics is None:
        metadata["metrics_error_code"] = metrics_result.error_code
        metadata["metrics_error_message"] = metrics_result.error_message
        return metadata

    metadata["display_count"] = len(metrics_result.metrics.displays)
    metadata["virtual_desktop_bounds"] = _bbox_to_summary(metrics_result.metrics.bounds)
    metadata["displays"] = [
        _display_to_summary(metrics_result.metrics, index=index) for index in range(len(metrics_result.metrics.displays))
    ]
    return metadata


def _build_backend_details(backend_details: Mapping[str, object]) -> dict[str, object]:
    return {
        "backend_name": _string_or_none(backend_details.get("backend_name")),
        "capture_api": _string_or_none(backend_details.get("capture_api")),
        "preferred_for_virtual_desktop": _bool_or_none(
            backend_details.get("preferred_for_virtual_desktop")
        ),
        "implementation_complete": _bool_or_none(backend_details.get("implementation_complete")),
        "dxcam_backend_order": _string_tuple(backend_details.get("dxcam_backend_order")),
        "dxcam_device_info": _string_or_none(backend_details.get("dxcam_device_info")),
        "dxcam_output_info": _string_or_none(backend_details.get("dxcam_output_info")),
        "camera_width_px": _int_or_none(backend_details.get("camera_width_px")),
        "camera_height_px": _int_or_none(backend_details.get("camera_height_px")),
    }


def _display_to_summary(metrics: VirtualDesktopMetrics, *, index: int) -> dict[str, object]:
    display = metrics.displays[index]
    return {
        "display_id": display.display_id,
        "is_primary": display.is_primary,
        "origin_x_px": display.origin_x_px,
        "origin_y_px": display.origin_y_px,
        "width_px": display.width_px,
        "height_px": display.height_px,
        "dpi_scale": display.dpi_scale,
    }


def _raw_capture_to_summary(raw_capture: RawWindowsCapture) -> dict[str, object]:
    return {
        "width": raw_capture.width,
        "height": raw_capture.height,
        "origin_x_px": raw_capture.origin_x_px,
        "origin_y_px": raw_capture.origin_y_px,
        "row_stride_bytes": raw_capture.row_stride_bytes,
        "pixel_format": raw_capture.pixel_format,
        "captured_at": raw_capture.captured_at.isoformat(),
        "metadata": dict(raw_capture.metadata),
    }


def _write_capture_bmp(raw_capture: RawWindowsCapture, output_path: Path) -> Path:
    if raw_capture.pixel_format is not FramePixelFormat.bgra_8888:
        raise ValueError("Only bgra_8888 captures can be written as BMP.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image_size = raw_capture.row_stride_bytes * raw_capture.height
    file_header = struct.pack("<2sIHHI", b"BM", 14 + 40 + image_size, 0, 0, 14 + 40)
    info_header = struct.pack(
        "<IiiHHIIiiII",
        40,
        raw_capture.width,
        -raw_capture.height,
        1,
        32,
        0,
        image_size,
        2835,
        2835,
        0,
        0,
    )
    output_path.write_bytes(file_header + info_header + raw_capture.image_bytes)
    return output_path


def _bbox_to_summary(bounds: ScreenBBox) -> dict[str, int]:
    return {
        "left_px": bounds.left_px,
        "top_px": bounds.top_px,
        "width_px": bounds.width_px,
        "height_px": bounds.height_px,
    }


def _capture_error_code_for_stage(stage: str) -> str:
    return {
        "validate_bounds": "invalid_capture_bounds",
        "unsupported_request_target": "unsupported_capture_target",
        "dxcam_backend_exhausted": "dxcam_backend_unavailable",
        "dxcam_create": "dxcam_create_failed",
        "dxcam_layout_unsupported": "dxcam_layout_unsupported",
        "dxcam_grab": "dxcam_grab_failed",
        "dxcam_frame_unavailable": "dxcam_frame_unavailable",
        "dxcam_frame_shape_invalid": "dxcam_frame_invalid",
    }.get(stage, "windows_api_error")


def _safe_isatty(stream: object) -> bool | None:
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return None
    try:
        return bool(isatty())
    except Exception:
        return None


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _string_or_default(value: object, default: str) -> str:
    return value if isinstance(value, str) and value else default


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _bool_or_none(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        return ()
    return tuple(item for item in value if isinstance(item, str))


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
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return value


if __name__ == "__main__":
    raise SystemExit(main())
