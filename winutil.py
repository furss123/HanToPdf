"""Windows 유틸리티 — 콘솔/백그라운드 창 숨김"""

from __future__ import annotations

import os
import sys
import threading

SW_HIDE = 0
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000

_MAIN_HWND: int | None = None


def _win32():
    import ctypes
    from ctypes import wintypes

    return ctypes, wintypes


def set_main_window_hwnd(hwnd: int) -> None:
    """숨김 대상에서 제외할 Tk 메인 창 HWND."""
    global _MAIN_HWND
    _MAIN_HWND = hwnd


def _is_protected_window(hwnd: int, user32) -> bool:
    if _MAIN_HWND and hwnd == _MAIN_HWND:
        return True
    if _MAIN_HWND and user32.IsChild(_MAIN_HWND, hwnd):
        return True
    return False


def _hide_from_taskbar_and_screen(hwnd: int, user32) -> None:
    try:
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        user32.ShowWindow(hwnd, SW_HIDE)
    except Exception:
        try:
            user32.ShowWindow(hwnd, SW_HIDE)
        except Exception:
            pass


def hide_console_window() -> None:
    if sys.platform != "win32":
        return

    ctypes, _ = _win32()
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    try:
        kernel32.FreeConsole()
    except OSError:
        pass

    hwnd = kernel32.GetConsoleWindow()
    if hwnd and not _is_protected_window(hwnd, user32):
        _hide_from_taskbar_and_screen(hwnd, user32)


def suppress_background_windows() -> None:
    """콘솔(CMD) 창만 숨김. 한글 창은 COM(Visible=False)으로만 제어."""
    if sys.platform != "win32":
        return

    hide_console_window()

    ctypes, wintypes = _win32()
    user32 = ctypes.windll.user32
    current_pid = os.getpid()

    def _callback(hwnd: int, _lparam: int) -> bool:
        if _is_protected_window(hwnd, user32):
            return True

        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        cls = class_name.value

        if cls != "ConsoleWindowClass":
            return True

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value != current_pid:
            return True

        if user32.IsWindowVisible(hwnd):
            _hide_from_taskbar_and_screen(hwnd, user32)
        return True

    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(_callback)
    user32.EnumWindows(enum_proc, 0)


def hide_hwp_windows_com(hwp) -> None:
    """한글 창은 COM API로만 숨김 (ShowWindow 사용 시 검은 화면 발생)."""
    try:
        count = int(hwp.XHwpWindows.Count)
    except Exception:
        count = 1
    for i in range(count):
        try:
            win = hwp.XHwpWindows.Item(i)
            win.Visible = False
            try:
                win.Left = -4000
                win.Top = -4000
            except Exception:
                pass
            try:
                win.WindowState = 2
            except Exception:
                pass
        except Exception:
            continue


def silence_stdio() -> None:
    """GUI 전용 실행 시 stdout/stderr로 콘솔이 붙는 것 방지."""
    if sys.platform != "win32":
        return
    try:
        devnull = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
        sys.stdout = devnull
        sys.stderr = devnull
    except OSError:
        pass


class ConsoleSuppressor:
    """실행 내내 콘솔 창이 보이지 않도록 백그라운드에서 숨김."""

    def __init__(self, interval: float = 0.5):
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.stop()
        hide_console_window()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="ConsoleSuppressor", daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            suppress_background_windows()
            self._stop.wait(self._interval)
