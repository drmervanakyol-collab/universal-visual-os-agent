from __future__ import annotations

from universal_visual_os_agent.geometry import ScreenBBox
from universal_visual_os_agent.integrations.windows import (
    DefaultWindowsCaptureRuntimePolicy,
    WindowsCaptureBackendCapability,
    WindowsCaptureBackendIntendedTarget,
    WindowsCaptureBackendRole,
    WindowsCaptureRequest,
    WindowsCaptureRuntimeMode,
    WindowsCaptureTarget,
    select_capture_backends,
)


class _FakeBackend:
    def __init__(self, *, backend_name: str, capability: WindowsCaptureBackendCapability) -> None:
        self.backend_name = backend_name
        self._capability = capability

    def detect_capability(self, request: WindowsCaptureRequest) -> WindowsCaptureBackendCapability:
        del request
        return self._capability

    def capture(self, request):
        del request
        raise AssertionError("capture should not be called in runtime architecture tests")


def _desktop_request() -> WindowsCaptureRequest:
    return WindowsCaptureRequest(
        target=WindowsCaptureTarget.virtual_desktop,
        bounds=ScreenBBox(left_px=0, top_px=0, width_px=1920, height_px=1080),
    )


def test_builtin_backend_roles_and_priorities_are_explicit_and_stable() -> None:
    policy = DefaultWindowsCaptureRuntimePolicy()

    dxcam = policy.policy_for_backend("dxcam_desktop")
    gdi = policy.policy_for_backend("gdi_bitblt")
    printwindow = policy.policy_for_backend("printwindow_foreground")

    assert dxcam.role is WindowsCaptureBackendRole.primary
    assert dxcam.priority < gdi.priority
    assert dxcam.intended_target is WindowsCaptureBackendIntendedTarget.virtual_desktop
    assert dxcam.diagnostic_only is False

    assert gdi.role is WindowsCaptureBackendRole.fallback
    assert gdi.intended_target is WindowsCaptureBackendIntendedTarget.virtual_desktop
    assert gdi.diagnostic_only is True

    assert printwindow.role is WindowsCaptureBackendRole.diagnostic_only
    assert printwindow.intended_target is WindowsCaptureBackendIntendedTarget.foreground_window
    assert printwindow.diagnostic_only is True


def test_runtime_selection_order_is_priority_driven_not_tuple_order() -> None:
    request = _desktop_request()
    selection = select_capture_backends(
        (
            _FakeBackend(
                backend_name="gdi_bitblt",
                capability=WindowsCaptureBackendCapability.available_backend(
                    backend_name="gdi_bitblt"
                ),
            ),
            _FakeBackend(
                backend_name="dxcam_desktop",
                capability=WindowsCaptureBackendCapability.available_backend(
                    backend_name="dxcam_desktop"
                ),
            ),
        ),
        request,
        runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
    )

    assert selection.available_backend_names == ("dxcam_desktop", "gdi_bitblt")
    assert selection.selected_backend_name == "dxcam_desktop"
    assert selection.candidates[0].backend_name == "dxcam_desktop"
    assert (
        selection.candidates[0].selection_reason
        == "Selected as the highest-priority runtime-eligible backend."
    )
    assert selection.candidates[1].skip_reason == "A higher-priority runtime-eligible backend was selected first."


def test_printwindow_is_diagnostic_only_for_foreground_window_routing() -> None:
    request = WindowsCaptureRequest(target=WindowsCaptureTarget.foreground_window)
    selection = select_capture_backends(
        (
            _FakeBackend(
                backend_name="printwindow_foreground",
                capability=WindowsCaptureBackendCapability.available_backend(
                    backend_name="printwindow_foreground"
                ),
            ),
        ),
        request,
        runtime_mode=WindowsCaptureRuntimeMode.production,
    )

    assert selection.selected_backend_name is None
    assert selection.candidates[0].runtime_eligible is False
    assert (
        selection.candidates[0].skip_reason
        == "Diagnostic-only backend is disabled in the production capture runtime."
    )

    diagnostic_selection = select_capture_backends(
        (
            _FakeBackend(
                backend_name="printwindow_foreground",
                capability=WindowsCaptureBackendCapability.available_backend(
                    backend_name="printwindow_foreground"
                ),
            ),
        ),
        request,
        runtime_mode=WindowsCaptureRuntimeMode.diagnostic,
    )

    assert diagnostic_selection.selected_backend_name == "printwindow_foreground"
    assert diagnostic_selection.candidates[0].runtime_eligible is True
    assert (
        diagnostic_selection.candidates[0].selection_reason
        == "Selected as the diagnostic foreground-window backend."
    )


def test_production_full_desktop_runtime_fails_cleanly_when_primary_is_unavailable() -> None:
    selection = select_capture_backends(
        (
            _FakeBackend(
                backend_name="dxcam_desktop",
                capability=WindowsCaptureBackendCapability.unavailable_backend(
                    backend_name="dxcam_desktop",
                    reason="DXcam runtime probe failed.",
                ),
            ),
            _FakeBackend(
                backend_name="gdi_bitblt",
                capability=WindowsCaptureBackendCapability.available_backend(
                    backend_name="gdi_bitblt"
                ),
            ),
        ),
        _desktop_request(),
        runtime_mode=WindowsCaptureRuntimeMode.production,
    )

    assert selection.selected_backend_name is None
    assert selection.available_backend_names == ()
    assert selection.capability_available_backend_names == ("gdi_bitblt",)
    assert selection.candidates[0].backend_name == "dxcam_desktop"
    assert selection.candidates[0].available is False
    assert selection.candidates[1].backend_name == "gdi_bitblt"
    assert selection.candidates[1].runtime_eligible is False
    assert (
        selection.candidates[1].skip_reason
        == "Diagnostic-only backend is disabled in the production capture runtime."
    )
