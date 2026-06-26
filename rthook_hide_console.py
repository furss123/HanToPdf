"""PyInstaller 런타임 훅: GUI exe 시작 직후 콘솔 창 숨김"""

import os
import sys

if sys.platform == "win32":
    import ctypes

    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    SW_HIDE = 0

    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    try:
        kernel32.FreeConsole()
    except OSError:
        pass

    _hwnd = kernel32.GetConsoleWindow()
    if _hwnd:
        try:
            style = user32.GetWindowLongW(_hwnd, GWL_EXSTYLE)
            style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
            user32.SetWindowLongW(_hwnd, GWL_EXSTYLE, style)
        except Exception:
            pass
        user32.ShowWindow(_hwnd, SW_HIDE)

    if getattr(sys, "frozen", False):
        try:
            _devnull = open(os.devnull, "w", encoding="utf-8")
            sys.stdout = _devnull
            sys.stderr = _devnull
        except OSError:
            pass
