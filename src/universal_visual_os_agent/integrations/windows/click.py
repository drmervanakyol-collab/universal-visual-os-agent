"""Minimal Windows real-click transport for the safe click prototype."""

from __future__ import annotations

import ctypes
import sys

from universal_visual_os_agent.geometry.models import ScreenPoint

_MOUSEEVENTF_LEFTDOWN = 0x0002
_MOUSEEVENTF_LEFTUP = 0x0004


class WindowsUser32ClickTransport:
    """Perform one constrained left click through the Win32 user32 API."""

    def click(self, point: ScreenPoint) -> None:
        if sys.platform != "win32":
            raise OSError("WindowsUser32ClickTransport is only available on Windows.")

        user32 = ctypes.windll.user32
        if not user32.SetCursorPos(point.x_px, point.y_px):
            raise OSError("SetCursorPos failed for the safe click prototype.")
        user32.mouse_event(_MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        user32.mouse_event(_MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
