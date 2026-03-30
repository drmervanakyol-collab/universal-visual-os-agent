"""Observe-only Windows capture provider with backend selection."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC

from universal_visual_os_agent.geometry import ScreenBBox, ScreenMetricsProvider
from universal_visual_os_agent.integrations.windows.capture_backends import (
    BoundsCaptureApiBackendAdapter,
    DefaultWindowsCaptureRuntimePolicy,
    WindowsCaptureBackend,
    WindowsCaptureRuntimePolicy,
    WindowsScreenCaptureApi,
    select_capture_backends,
)
from universal_visual_os_agent.integrations.windows.capture_dxcam import WindowsDxcamCaptureBackend
from universal_visual_os_agent.integrations.windows.capture_gdi import WindowsGdiCaptureBackend
from universal_visual_os_agent.integrations.windows.capture_models import (
    RawWindowsCapture,
    WindowsCaptureRequest,
    WindowsCaptureRuntimeMode,
    WindowsCaptureStageError,
    WindowsCaptureTarget,
    WindowsCaptureUnavailableError,
)
from universal_visual_os_agent.integrations.windows.capture_printwindow import (
    WindowsForegroundWindowPrintCaptureBackend,
)
from universal_visual_os_agent.integrations.windows.screen_metrics import WindowsScreenMetricsProvider
from universal_visual_os_agent.perception import (
    CaptureProvider,
    CaptureResult,
    CapturedFrame,
    FrameImagePayload,
)


class WindowsObserveOnlyCaptureProvider(CaptureProvider):
    """Read-only Windows capture provider with explicit backend reporting."""

    def __init__(
        self,
        *,
        screen_metrics_provider: ScreenMetricsProvider | None = None,
        capture_target: WindowsCaptureTarget = WindowsCaptureTarget.virtual_desktop,
        capture_backends: tuple[WindowsCaptureBackend, ...] | None = None,
        capture_api: WindowsScreenCaptureApi | None = None,
        runtime_mode: WindowsCaptureRuntimeMode = WindowsCaptureRuntimeMode.production,
        runtime_policy: WindowsCaptureRuntimePolicy | None = None,
    ) -> None:
        if capture_backends is not None and capture_api is not None:
            raise ValueError("Provide either capture_backends or capture_api, not both.")

        self._screen_metrics_provider = (
            WindowsScreenMetricsProvider() if screen_metrics_provider is None else screen_metrics_provider
        )
        self._capture_target = capture_target
        self._runtime_mode = runtime_mode
        self._runtime_policy = (
            DefaultWindowsCaptureRuntimePolicy()
            if runtime_policy is None
            else runtime_policy
        )
        self._capture_backends = self._build_capture_backends(capture_backends=capture_backends, capture_api=capture_api)
        _validate_backend_names(self._capture_backends)

    def capture_frame(self) -> CaptureResult:
        """Capture the current target or return a safe structured failure."""

        provider_name = self.__class__.__name__
        prepared = self._prepare_request()
        if prepared["failure"] is not None:
            return prepared["failure"]

        request = prepared["request"]
        base_details = prepared["base_details"]
        selection = select_capture_backends(
            self._capture_backends,
            request,
            runtime_mode=self._runtime_mode,
            runtime_policy=self._runtime_policy,
        )
        selection_details = selection.to_details()

        if selection.selected_backend_name is None:
            return CaptureResult.failure(
                provider_name=provider_name,
                error_code="capture_backend_unavailable",
                error_message="No safe capture backend is available for the current request.",
                details={
                    **base_details,
                    **selection_details,
                    "failing_stage": "backend_selection",
                },
            )

        backends_by_name = {
            backend.backend_name: backend for backend in self._capture_backends
        }
        backend_attempts: list[dict[str, object]] = []
        for backend_name in selection.available_backend_names:
            backend = backends_by_name[backend_name]
            try:
                raw_capture = backend.capture(request)
                raw_capture = _ensure_backend_metadata(raw_capture, backend_name=backend.backend_name)
                frame = _build_captured_frame(
                    raw_capture,
                    provider_name=provider_name,
                    display_count=prepared["display_count"],
                )
            except WindowsCaptureUnavailableError as exc:
                backend_attempts.append(
                    {
                        "backend_name": backend.backend_name,
                        "failing_stage": "platform_availability",
                        "error_code": "capture_unavailable",
                        "error_message": str(exc),
                    }
                )
                continue
            except WindowsCaptureStageError as exc:
                backend_attempts.append(
                    {
                        "backend_name": backend.backend_name,
                        "failing_stage": exc.stage,
                        "error_code": _error_code_for_stage(exc.stage),
                        "error_message": str(exc),
                        "win32_error_code": exc.win32_error_code,
                        **exc.diagnostics,
                    }
                )
                continue
            except ValueError as exc:
                backend_attempts.append(
                    {
                        "backend_name": backend.backend_name,
                        "failing_stage": "invalid_capture_data",
                        "error_code": "invalid_capture_data",
                        "error_message": str(exc),
                    }
                )
                continue
            except Exception as exc:  # noqa: BLE001 - provider must remain failure-safe
                backend_attempts.append(
                    {
                        "backend_name": backend.backend_name,
                        "failing_stage": "unexpected_exception",
                        "error_code": "capture_internal_error",
                        "error_message": str(exc),
                        "exception_type": type(exc).__name__,
                    }
                )
                continue

            return CaptureResult.ok(
                provider_name=provider_name,
                frame=frame,
                details={
                    **base_details,
                    **selection_details,
                    "used_backend_name": backend.backend_name,
                    "backend_fallback_used": backend.backend_name != selection.selected_backend_name,
                    "backend_attempt_count": len(backend_attempts) + 1,
                    "backend_attempts": tuple(backend_attempts),
                    "selected_backend_name_runtime_stable": True,
                    "capture_origin_x_px": raw_capture.origin_x_px,
                    "capture_origin_y_px": raw_capture.origin_y_px,
                },
            )

        error_code = (
            "capture_backend_fallback_exhausted"
            if len(backend_attempts) > 1
            else _single_backend_error_code(backend_attempts)
        )
        error_message = (
            "All safe capture backends failed."
            if len(backend_attempts) > 1
            else _single_backend_error_message(backend_attempts)
        )
        failing_stage = (
            "backend_fallback_exhausted"
            if len(backend_attempts) > 1
            else _single_backend_failing_stage(backend_attempts)
        )
        return CaptureResult.failure(
            provider_name=provider_name,
            error_code=error_code,
            error_message=error_message,
            details={
                **base_details,
                **selection_details,
                "failing_stage": failing_stage,
                "backend_attempt_count": len(backend_attempts),
                "backend_attempts": tuple(backend_attempts),
            },
        )

    def _prepare_request(self) -> dict[str, object]:
        if self._capture_target is WindowsCaptureTarget.virtual_desktop:
            metrics_result = self._screen_metrics_provider.get_virtual_desktop_metrics()
            if not metrics_result.success or metrics_result.metrics is None:
                failure = CaptureResult.failure(
                    provider_name=self.__class__.__name__,
                    error_code="screen_metrics_unavailable",
                    error_message=metrics_result.error_message or "Screen metrics are unavailable.",
                    details={
                "capture_target": self._capture_target,
                "runtime_mode": self._runtime_mode,
                "metrics_lookup_succeeded": False,
                "metrics_required": True,
                "bounds_valid": False,
                "failing_stage": "screen_metrics_lookup",
                "metrics_error_code": metrics_result.error_code or "unknown",
                    },
                )
                return {
                    "failure": failure,
                    "request": None,
                    "base_details": {},
                    "display_count": 0,
                }

            bounds = metrics_result.metrics.bounds
            request = WindowsCaptureRequest(target=self._capture_target, bounds=bounds)
            return {
                "failure": None,
                "request": request,
                "display_count": len(metrics_result.metrics.displays),
                "base_details": {
                    "capture_target": self._capture_target,
                    "runtime_mode": self._runtime_mode,
                    "metrics_lookup_succeeded": True,
                    "metrics_required": True,
                    "bounds_valid": _bounds_are_valid(bounds),
                    "bounds_left_px": bounds.left_px,
                    "bounds_top_px": bounds.top_px,
                    "bounds_width_px": bounds.width_px,
                    "bounds_height_px": bounds.height_px,
                    "display_count": len(metrics_result.metrics.displays),
                },
            }

        request = WindowsCaptureRequest(target=self._capture_target)
        return {
            "failure": None,
            "request": request,
            "display_count": 0,
            "base_details": {
                "capture_target": self._capture_target,
                "runtime_mode": self._runtime_mode,
                "metrics_lookup_succeeded": False,
                "metrics_required": False,
                "bounds_valid": False,
                "display_count": 0,
            },
        }

    def _build_capture_backends(
        self,
        *,
        capture_backends: tuple[WindowsCaptureBackend, ...] | None,
        capture_api: WindowsScreenCaptureApi | None,
    ) -> tuple[WindowsCaptureBackend, ...]:
        if capture_backends is not None:
            return capture_backends
        if capture_api is not None:
            return (BoundsCaptureApiBackendAdapter(capture_api=capture_api),)
        return (
            WindowsDxcamCaptureBackend(),
            WindowsGdiCaptureBackend(),
            WindowsForegroundWindowPrintCaptureBackend(),
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
            **raw_capture.metadata,
        },
    )


def _ensure_backend_metadata(raw_capture: RawWindowsCapture, *, backend_name: str) -> RawWindowsCapture:
    if raw_capture.metadata.get("backend_name") == backend_name:
        return raw_capture
    return replace(raw_capture, metadata={**raw_capture.metadata, "backend_name": backend_name})


def _bounds_are_valid(bounds: ScreenBBox) -> bool:
    return bounds.width_px > 0 and bounds.height_px > 0


def _validate_backend_names(backends: tuple[WindowsCaptureBackend, ...]) -> None:
    backend_names = tuple(backend.backend_name for backend in backends)
    if len(set(backend_names)) != len(backend_names):
        raise ValueError("Capture backend names must be unique.")


def _error_code_for_stage(stage: str) -> str:
    return {
        "validate_bounds": "invalid_capture_bounds",
        "unsupported_request_target": "unsupported_capture_target",
        "validate_window_handle": "target_window_inaccessible",
        "validate_window_visibility": "target_window_not_visible",
        "validate_window_state": "target_window_unsupported_state",
        "foreground_window_changed": "foreground_window_changed",
        "desktop_duplication_runtime_unavailable": "desktop_duplication_unavailable",
        "desktop_duplication_incomplete": "desktop_duplication_incomplete",
        "dxcam_backend_exhausted": "dxcam_backend_unavailable",
        "dxcam_create": "dxcam_create_failed",
        "dxcam_layout_unsupported": "dxcam_layout_unsupported",
        "dxcam_grab": "dxcam_grab_failed",
        "dxcam_frame_unavailable": "dxcam_frame_unavailable",
        "dxcam_frame_shape_invalid": "dxcam_frame_invalid",
        "acquire_source_dc": "source_dc_failed",
        "create_memory_dc": "memory_dc_failed",
        "create_bitmap": "bitmap_creation_failed",
        "select_bitmap": "bitmap_selection_failed",
        "bit_blt": "screen_copy_failed",
        "get_dibits": "bitmap_read_failed",
        "capture_fallback_exhausted": "capture_fallback_exhausted",
        "detect_target_window": "target_window_unavailable",
        "get_window_rect": "window_rect_failed",
        "print_window": "window_print_failed",
    }.get(stage, "windows_api_error")


def _single_backend_error_code(backend_attempts: list[dict[str, object]]) -> str:
    if not backend_attempts:
        return "capture_backend_unavailable"
    error_code = backend_attempts[-1].get("error_code")
    return error_code if isinstance(error_code, str) else "windows_api_error"


def _single_backend_error_message(backend_attempts: list[dict[str, object]]) -> str:
    if not backend_attempts:
        return "No capture backend attempted a capture."
    error_message = backend_attempts[-1].get("error_message")
    return error_message if isinstance(error_message, str) else "Capture backend failed."


def _single_backend_failing_stage(backend_attempts: list[dict[str, object]]) -> str:
    if not backend_attempts:
        return "backend_selection"
    failing_stage = backend_attempts[-1].get("failing_stage")
    return failing_stage if isinstance(failing_stage, str) else "backend_failure"
