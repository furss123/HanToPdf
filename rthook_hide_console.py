"""PyInstaller 런타임 훅: GUI exe 뒤에 붙는 콘솔 창 숨김"""

import sys

if sys.platform == "win32":
    import ctypes

    _hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if _hwnd:
        ctypes.windll.user32.ShowWindow(_hwnd, 0)
