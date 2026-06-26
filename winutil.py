"""Windows 유틸리티"""

from __future__ import annotations

import sys


def hide_console_window() -> None:
    if sys.platform != "win32":
        return
    import ctypes

    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)
