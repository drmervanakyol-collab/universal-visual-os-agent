"""DXcam-backed read-only full-desktop capture backend."""

from __future__ import annotations

import os
import sys
from typing import Callable, Protocol

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

_DESKTOP_READOBJECTS = 0x0001
_SM_REMOTESESSION = 0x1000
_E_ACCESSDENIED = -2147024891
_DXCAM_DEVICE_INDEX = 0
_DXCAM_OUTPUT_INDEX: int | None = None
_DXCAM_REGION: tuple[int, int, int, int] | None = None
_DXCAM_OUTPUT_COLOR = "BGRA"
_DXCAM_MAX_BUFFER_LEN = 2
_DXCAM_PROCESSOR_BACKEND = "numpy"


class _DxcamModule(Protocol):
    """Protocol for the subset of DXcam used by the backend."""

    def create(
        self,
        *,
        device_idx: int = 0,
        output_idx: int | None = None,
        region: tuple[int, int, int, int] | None = None,
        output_color: str = "BGRA",
        max_buffer_len: int = 2,
        backend: str = "dxgi",
        processor_backend: str = "numpy",
    ) -> object:
        """Create a DXcam camera."""

    def device_info(self) -> str:
        """Return DXGI adapter information."""

    def output_info(self) -> str:
        """Return DXGI output information."""


class WindowsDxcamCaptureBackend:
    """Read-only DXcam backend for full-desktop capture."""

    backend_name = "dxcam_desktop"

    def __init__(
        self,
        *,
        dxcam_module_loader: Callable[[], _DxcamModule] | None = None,
    ) -> None:
        self._dxcam_module_loader = self._default_dxcam_module_loader if dxcam_module_loader is None else dxcam_module_loader

    def detect_capability(self, request: WindowsCaptureRequest) -> WindowsCaptureBackendCapability:
        validation = self._validate_request(request)
        if validation is not None:
            return validation

        try:
            dxcam_module = self._load_dxcam_module()
        except ModuleNotFoundError as exc:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="DXcam is not installed.",
                details={
                    "backend_name": self.backend_name,
                    "capture_api": "dxcam",
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )

        probe = self._probe_dxcam_runtime(dxcam_module=dxcam_module, bounds=request.bounds)
        if probe["available"] is True:
            return WindowsCaptureBackendCapability.available_backend(
                backend_name=self.backend_name,
                details=probe,
            )
        return WindowsCaptureBackendCapability.unavailable_backend(
            backend_name=self.backend_name,
            reason=probe["reason"],
            details=probe,
        )

    def capture(self, request: WindowsCaptureRequest) -> RawWindowsCapture:
        validation_error = self._validate_request_for_capture(request)
        if validation_error is not None:
            raise validation_error

        try:
            dxcam_module = self._load_dxcam_module()
        except ModuleNotFoundError as exc:
            raise WindowsCaptureUnavailableError(str(exc)) from exc

        probe = self._probe_dxcam_runtime(dxcam_module=dxcam_module, bounds=request.bounds)
        if probe["available"] is not True:
            raise WindowsCaptureStageError(
                stage="dxcam_backend_exhausted",
                message=str(probe["reason"]),
                diagnostics=probe,
            )

        dxcam_backend = probe["dxcam_backend_used"]
        camera = None
        try:
            camera = self._create_camera(dxcam_module=dxcam_module, dxcam_backend=dxcam_backend)
            frame = self._grab_frame(camera)
            return self._frame_to_raw_capture(
                frame=frame,
                bounds=request.bounds,
                dxcam_backend=dxcam_backend,
                probe=probe,
            )
        except WindowsCaptureStageError:
            raise
        except Exception as exc:  # noqa: BLE001 - backend must remain structured and failure-safe
            raise WindowsCaptureStageError(
                stage="dxcam_grab",
                message="DXcam failed to grab a frame.",
                diagnostics={
                    **probe,
                    "backend_name": self.backend_name,
                    "capture_api": "dxcam",
                    "dxcam_backend_used": dxcam_backend,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    **_exception_details(exc),
                },
            ) from None
        finally:
            self._release_camera(camera)

    def _validate_request(self, request: WindowsCaptureRequest) -> WindowsCaptureBackendCapability | None:
        if not self._is_windows_platform():
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="DXcam capture is unavailable on this platform.",
                details={"platform": sys.platform, "capture_api": "dxcam"},
            )
        if request.target is not WindowsCaptureTarget.virtual_desktop:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="DXcam capture only supports virtual_desktop requests.",
                details={"target": request.target, "capture_api": "dxcam"},
            )
        if request.bounds is None:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Virtual desktop bounds are required for DXcam capture.",
                details={"capture_api": "dxcam"},
            )
        if not _bounds_are_valid(request.bounds):
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Virtual desktop bounds must be positive.",
                details={
                    "capture_api": "dxcam",
                    "bounds_left_px": request.bounds.left_px,
                    "bounds_top_px": request.bounds.top_px,
                    "bounds_width_px": request.bounds.width_px,
                    "bounds_height_px": request.bounds.height_px,
                },
            )
        return None

    def _validate_request_for_capture(self, request: WindowsCaptureRequest) -> WindowsCaptureStageError | None:
        if not self._is_windows_platform():
            raise WindowsCaptureUnavailableError("DXcam capture is unavailable on this platform.")
        if request.target is not WindowsCaptureTarget.virtual_desktop:
            return WindowsCaptureStageError(
                stage="unsupported_request_target",
                message="DXcam capture only supports virtual_desktop requests.",
                diagnostics={"backend_name": self.backend_name, "target": request.target},
            )
        if request.bounds is None:
            return WindowsCaptureStageError(
                stage="validate_bounds",
                message="Virtual desktop bounds are required for DXcam capture.",
                diagnostics={"backend_name": self.backend_name},
            )
        if not _bounds_are_valid(request.bounds):
            return WindowsCaptureStageError(
                stage="validate_bounds",
                message="Virtual desktop bounds must be positive.",
                diagnostics={
                    "backend_name": self.backend_name,
                    "bounds_left_px": request.bounds.left_px,
                    "bounds_top_px": request.bounds.top_px,
                    "bounds_width_px": request.bounds.width_px,
                    "bounds_height_px": request.bounds.height_px,
                },
            )
        return None

    def _probe_dxcam_runtime(self, *, dxcam_module: _DxcamModule, bounds: ScreenBBox) -> dict[str, object]:
        environment_details = self._capture_environment_details()
        dxcam_details = self._dxcam_metadata(dxcam_module)
        attempts: list[dict[str, object]] = []

        for dxcam_backend in self._dxcam_backend_order():
            camera = None
            try:
                camera = self._create_camera(dxcam_module=dxcam_module, dxcam_backend=dxcam_backend)
                width = int(getattr(camera, "width"))
                height = int(getattr(camera, "height"))
                if not self._requested_bounds_match_primary_output(bounds=bounds, width=width, height=height):
                    attempts.append(
                        {
                            "dxcam_backend": dxcam_backend,
                            "available": False,
                            "failing_stage": "dxcam_layout_unsupported",
                            "reason": "DXcam currently supports only a single primary-output layout matching the request.",
                            "camera_width_px": width,
                            "camera_height_px": height,
                        }
                    )
                    continue

                attempts.append(
                    {
                        "dxcam_backend": dxcam_backend,
                        "available": True,
                        "camera_width_px": width,
                        "camera_height_px": height,
                    }
                )
                return {
                    "backend_name": self.backend_name,
                    "capture_api": "dxcam",
                    "preferred_for_virtual_desktop": True,
                    "implementation_complete": True,
                    "dxcam_backend_order": self._dxcam_backend_order(),
                    "dxcam_backend_used": dxcam_backend,
                    "dxcam_attempts": tuple(attempts),
                    "bounds_left_px": bounds.left_px,
                    "bounds_top_px": bounds.top_px,
                    "bounds_width_px": bounds.width_px,
                    "bounds_height_px": bounds.height_px,
                    "camera_width_px": width,
                    "camera_height_px": height,
                    "available": True,
                    "reason": "DXcam is available for the current request.",
                    **self._capture_request_details(bounds),
                    **environment_details,
                    **dxcam_details,
                }
            except Exception as exc:  # noqa: BLE001 - capability probing must stay structured
                attempts.append(
                    {
                        "dxcam_backend": dxcam_backend,
                        "available": False,
                        "failing_stage": "dxcam_create",
                        "reason": _reason_from_dxcam_exception(exc, dxcam_backend=dxcam_backend),
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                        **_exception_details(exc),
                    }
                )
            finally:
                self._release_camera(camera)

        return {
            "backend_name": self.backend_name,
            "capture_api": "dxcam",
            "preferred_for_virtual_desktop": True,
            "implementation_complete": True,
            "dxcam_backend_order": self._dxcam_backend_order(),
            "dxcam_backend_used": None,
            "dxcam_attempts": tuple(attempts),
            "bounds_left_px": bounds.left_px,
            "bounds_top_px": bounds.top_px,
            "bounds_width_px": bounds.width_px,
            "bounds_height_px": bounds.height_px,
            "available": False,
            "reason": _reason_from_attempts(attempts),
            **self._capture_request_details(bounds),
            **environment_details,
            **dxcam_details,
        }

    def _grab_frame(self, camera: object) -> object:
        frame = getattr(camera, "grab")(region=None, copy=True, new_frame_only=False)
        if frame is None:
            raise WindowsCaptureStageError(
                stage="dxcam_frame_unavailable",
                message="DXcam did not return a frame.",
                diagnostics={"backend_name": self.backend_name, "capture_api": "dxcam"},
            )
        return frame

    def _frame_to_raw_capture(
        self,
        *,
        frame: object,
        bounds: ScreenBBox,
        dxcam_backend: str,
        probe: dict[str, object],
    ) -> RawWindowsCapture:
        import numpy

        if not isinstance(frame, numpy.ndarray):
            raise WindowsCaptureStageError(
                stage="dxcam_frame_shape_invalid",
                message="DXcam returned an unexpected frame type.",
                diagnostics={
                    "backend_name": self.backend_name,
                    "capture_api": "dxcam",
                    "dxcam_backend_used": dxcam_backend,
                    "frame_type": type(frame).__name__,
                },
            )

        frame_array = numpy.ascontiguousarray(frame)
        if frame_array.ndim != 3 or frame_array.shape[2] != 4:
            raise WindowsCaptureStageError(
                stage="dxcam_frame_shape_invalid",
                message="DXcam must return a BGRA frame.",
                diagnostics={
                    "backend_name": self.backend_name,
                    "capture_api": "dxcam",
                    "dxcam_backend_used": dxcam_backend,
                    "frame_shape": tuple(int(item) for item in frame_array.shape),
                },
            )

        height = int(frame_array.shape[0])
        width = int(frame_array.shape[1])
        if width != bounds.width_px or height != bounds.height_px:
            raise WindowsCaptureStageError(
                stage="dxcam_layout_unsupported",
                message="DXcam frame dimensions do not match the requested virtual desktop bounds.",
                diagnostics={
                    **probe,
                    "backend_name": self.backend_name,
                    "capture_api": "dxcam",
                    "dxcam_backend_used": dxcam_backend,
                    "frame_width_px": width,
                    "frame_height_px": height,
                },
            )

        row_stride_bytes = width * FramePixelFormat.bgra_8888.bytes_per_pixel
        image_bytes = frame_array.tobytes(order="C")
        return RawWindowsCapture(
            width=width,
            height=height,
            origin_x_px=bounds.left_px,
            origin_y_px=bounds.top_px,
            row_stride_bytes=row_stride_bytes,
            image_bytes=image_bytes,
            metadata={
                "backend_name": self.backend_name,
                "capture_source_strategy": "dxcam",
                "dxcam_backend_used": dxcam_backend,
                "dxcam_attempts": probe["dxcam_attempts"],
            },
        )

    def _requested_bounds_match_primary_output(self, *, bounds: ScreenBBox, width: int, height: int) -> bool:
        return bounds.left_px == 0 and bounds.top_px == 0 and bounds.width_px == width and bounds.height_px == height

    def _capture_request_details(self, bounds: ScreenBBox) -> dict[str, object]:
        return {
            "requested_device_idx": _DXCAM_DEVICE_INDEX,
            "requested_output_idx": _DXCAM_OUTPUT_INDEX,
            "requested_region": _DXCAM_REGION,
            "requested_output_color": _DXCAM_OUTPUT_COLOR,
            "requested_processor_backend": _DXCAM_PROCESSOR_BACKEND,
            "requested_max_buffer_len": _DXCAM_MAX_BUFFER_LEN,
            "primary_output_layout_required": True,
            "requested_layout_origin_x_px": bounds.left_px,
            "requested_layout_origin_y_px": bounds.top_px,
            "requested_layout_width_px": bounds.width_px,
            "requested_layout_height_px": bounds.height_px,
        }

    def _create_camera(self, *, dxcam_module: _DxcamModule, dxcam_backend: str) -> object:
        return dxcam_module.create(
            device_idx=_DXCAM_DEVICE_INDEX,
            output_idx=_DXCAM_OUTPUT_INDEX,
            region=_DXCAM_REGION,
            output_color=_DXCAM_OUTPUT_COLOR,
            max_buffer_len=_DXCAM_MAX_BUFFER_LEN,
            backend=dxcam_backend,
            processor_backend=_DXCAM_PROCESSOR_BACKEND,
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
            details["input_desktop_error_code"] = error_code or None
            if error_code:
                details["input_desktop_error_message"] = _format_win32_error(ctypes, error_code)

        limitation_reasons: list[str] = []
        if details["is_remote_session"] is True:
            limitation_reasons.append("remote_session")
        if details.get("input_desktop_accessible") is False:
            limitation_reasons.append("input_desktop_inaccessible")
        details["environment_limitation_suspected"] = bool(limitation_reasons)
        details["environment_limitation_reasons"] = tuple(limitation_reasons)
        return details

    def _dxcam_metadata(self, dxcam_module: _DxcamModule) -> dict[str, object]:
        details: dict[str, object] = {}
        try:
            details["dxcam_device_info"] = dxcam_module.device_info()
        except Exception as exc:  # noqa: BLE001 - diagnostics only
            details["dxcam_device_info_error_type"] = type(exc).__name__
            details["dxcam_device_info_error_message"] = str(exc)
        try:
            details["dxcam_output_info"] = dxcam_module.output_info()
        except Exception as exc:  # noqa: BLE001 - diagnostics only
            details["dxcam_output_info_error_type"] = type(exc).__name__
            details["dxcam_output_info_error_message"] = str(exc)
        return details

    def _release_camera(self, camera: object | None) -> None:
        if camera is None:
            return
        release = getattr(camera, "release", None)
        if callable(release):
            try:
                release()
            except Exception:
                return

    def _dxcam_backend_order(self) -> tuple[str, ...]:
        return ("dxgi", "winrt")

    def _load_dxcam_module(self) -> _DxcamModule:
        return self._dxcam_module_loader()

    def _default_dxcam_module_loader(self) -> _DxcamModule:
        import dxcam

        return dxcam

    def _is_windows_platform(self) -> bool:
        return sys.platform == "win32"


def _bounds_are_valid(bounds: ScreenBBox) -> bool:
    return bounds.width_px > 0 and bounds.height_px > 0


def _reason_from_attempts(attempts: list[dict[str, object]]) -> str:
    if not attempts:
        return "DXcam availability could not be determined."
    for attempt in attempts:
        reason = attempt.get("reason")
        if isinstance(reason, str) and reason:
            return reason
    return "DXcam failed for an unspecified reason."


def _reason_from_dxcam_exception(exc: Exception, *, dxcam_backend: str) -> str:
    details = _exception_details(exc)
    if details.get("hresult") == _E_ACCESSDENIED:
        return f"DXcam {dxcam_backend} backend access was denied in this environment."
    if isinstance(exc, ModuleNotFoundError):
        return f"DXcam {dxcam_backend} backend requires optional dependencies that are not installed."
    return f"DXcam {dxcam_backend} backend could not be initialized."


def _exception_details(exc: Exception) -> dict[str, object]:
    details: dict[str, object] = {}
    if exc.args:
        first_arg = exc.args[0]
        if isinstance(first_arg, int):
            details["hresult"] = first_arg
    return details


def _reset_last_error(ctypes_module: object) -> None:
    set_last_error = getattr(ctypes_module, "set_last_error", None)
    if callable(set_last_error):
        set_last_error(0)


def _format_win32_error(ctypes_module: object, error_code: int) -> str:
    try:
        return str(ctypes_module.FormatError(error_code)).strip()
    except (AttributeError, OSError):
        return ""
