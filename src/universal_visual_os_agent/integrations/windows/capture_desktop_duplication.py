"""Desktop Duplication capability probe for read-only full-desktop capture."""

from __future__ import annotations

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

_DESKTOP_READOBJECTS = 0x0001
_MIN_WINDOWS_MAJOR = 6
_MIN_WINDOWS_MINOR = 2
_SM_REMOTESESSION = 0x1000


class WindowsDesktopDuplicationCaptureBackend:
    """Capability-probe backend for DXGI Desktop Duplication capture."""

    backend_name = "desktop_duplication_dxgi"

    def detect_capability(self, request: WindowsCaptureRequest) -> WindowsCaptureBackendCapability:
        if not self._is_windows_platform():
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Desktop Duplication is unavailable on this platform.",
                details={"platform": sys.platform, "capture_api": "dxgi_desktop_duplication"},
            )
        if request.target is not WindowsCaptureTarget.virtual_desktop:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Desktop Duplication only supports virtual_desktop requests.",
                details={"target": request.target, "capture_api": "dxgi_desktop_duplication"},
            )
        if request.bounds is None:
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Virtual desktop bounds are required for Desktop Duplication.",
                details={"capture_api": "dxgi_desktop_duplication"},
            )
        if not _bounds_are_valid(request.bounds):
            return WindowsCaptureBackendCapability.unavailable_backend(
                backend_name=self.backend_name,
                reason="Virtual desktop bounds must be positive.",
                details={
                    "capture_api": "dxgi_desktop_duplication",
                    "bounds_left_px": request.bounds.left_px,
                    "bounds_top_px": request.bounds.top_px,
                    "bounds_width_px": request.bounds.width_px,
                    "bounds_height_px": request.bounds.height_px,
                },
            )

        diagnostics = self._probe_desktop_duplication_details(request.bounds)
        return WindowsCaptureBackendCapability.unavailable_backend(
            backend_name=self.backend_name,
            reason=_reason_from_probe(diagnostics),
            details=diagnostics,
        )

    def capture(self, request: WindowsCaptureRequest) -> RawWindowsCapture:
        if not self._is_windows_platform():
            raise WindowsCaptureUnavailableError("Desktop Duplication is unavailable on this platform.")
        if request.target is not WindowsCaptureTarget.virtual_desktop:
            raise WindowsCaptureStageError(
                stage="unsupported_request_target",
                message="Desktop Duplication only supports virtual_desktop requests.",
                diagnostics={"backend_name": self.backend_name, "target": request.target},
            )
        if request.bounds is None:
            raise WindowsCaptureStageError(
                stage="validate_bounds",
                message="Virtual desktop bounds are required for Desktop Duplication.",
                diagnostics={"backend_name": self.backend_name},
            )
        if not _bounds_are_valid(request.bounds):
            raise WindowsCaptureStageError(
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

        diagnostics = self._probe_desktop_duplication_details(request.bounds)
        stage = (
            "desktop_duplication_runtime_unavailable"
            if diagnostics["runtime_supported_os"] is not True
            or diagnostics["dxgi_library_loadable"] is not True
            or diagnostics["d3d11_library_loadable"] is not True
            else "desktop_duplication_incomplete"
        )
        raise WindowsCaptureStageError(
            stage=stage,
            message=_reason_from_probe(diagnostics),
            diagnostics=diagnostics,
        )

    def _is_windows_platform(self) -> bool:
        return sys.platform == "win32"

    def _probe_desktop_duplication_details(self, bounds: ScreenBBox) -> dict[str, object]:
        details: dict[str, object] = {
            "backend_name": self.backend_name,
            "capture_api": "dxgi_desktop_duplication",
            "capture_target": WindowsCaptureTarget.virtual_desktop,
            "bounds_left_px": bounds.left_px,
            "bounds_top_px": bounds.top_px,
            "bounds_width_px": bounds.width_px,
            "bounds_height_px": bounds.height_px,
            "preferred_for_virtual_desktop": True,
            "implementation_status": "capability_probe_only",
            "implementation_complete": False,
            "com_binding_implemented": False,
            "platform": sys.platform,
            "session_name": os.environ.get("SESSIONNAME"),
            "runtime_supported_os": False,
            "dxgi_library_loadable": False,
            "d3d11_library_loadable": False,
            "environment_limitation_suspected": False,
            "environment_limitation_reasons": (),
        }
        if not self._is_windows_platform():
            return details

        windows_version = sys.getwindowsversion()
        details["windows_major"] = windows_version.major
        details["windows_minor"] = windows_version.minor
        details["windows_build"] = windows_version.build
        details["runtime_supported_os"] = (
            windows_version.major > _MIN_WINDOWS_MAJOR
            or (windows_version.major == _MIN_WINDOWS_MAJOR and windows_version.minor >= _MIN_WINDOWS_MINOR)
        )

        import ctypes
        from ctypes import wintypes

        details.update(self._probe_runtime_libraries(ctypes))

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
        details["environment_limitation_reasons"] = tuple(limitation_reasons)
        details["environment_limitation_suspected"] = bool(limitation_reasons)
        return details

    def _probe_runtime_libraries(self, ctypes_module: object) -> dict[str, object]:
        diagnostics: dict[str, object] = {
            "dxgi_library_loadable": False,
            "d3d11_library_loadable": False,
        }
        for library_name, key in (("dxgi", "dxgi_library_loadable"), ("d3d11", "d3d11_library_loadable")):
            try:
                ctypes_module.WinDLL(library_name, use_last_error=True)
            except OSError as exc:
                diagnostics[f"{key}_error_message"] = str(exc)
            else:
                diagnostics[key] = True
        return diagnostics


def _bounds_are_valid(bounds: ScreenBBox) -> bool:
    return bounds.width_px > 0 and bounds.height_px > 0


def _reason_from_probe(diagnostics: dict[str, object]) -> str:
    if diagnostics["runtime_supported_os"] is not True:
        return "Desktop Duplication requires Windows 8 or newer."
    if diagnostics["dxgi_library_loadable"] is not True or diagnostics["d3d11_library_loadable"] is not True:
        return "Desktop Duplication runtime libraries are unavailable in this environment."
    return (
        "Desktop Duplication support is detectable, but a safe Direct3D/DXGI capture implementation is not "
        "completed in this repository yet."
    )


def _reset_last_error(ctypes_module: object) -> None:
    set_last_error = getattr(ctypes_module, "set_last_error", None)
    if callable(set_last_error):
        set_last_error(0)


def _format_win32_error(ctypes_module: object, error_code: int) -> str:
    try:
        return str(ctypes_module.FormatError(error_code)).strip()
    except (AttributeError, OSError):
        return ""
