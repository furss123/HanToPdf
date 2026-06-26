"""한글 보안/파일 접근 허용 대화상자 자동 처리."""

from __future__ import annotations

import ctypes
import os
import threading
import time
import winreg
from pathlib import Path

import win32api
import win32con
import win32gui
import win32process

_HWP_TITLE_PARTS = ("한글", "훈글", "Hwp", "HWP", "Hangul")
_ALLOW_ACCESS_KEYWORDS = ("접근 허용", "접근허용", "Allow Access")
_ALLOW_ALL_KEYWORDS = ("모두 허용", "모두허용", "Allow All")
_SECURITY_KEYWORDS = (
    "접근하려는 시도",
    "접근을 허용",
    "FilePathCheck",
    "손상 또는 유출",
    "정상적인 작업",
)
_FILE_MARKERS = (".hwp", ".hwpx", "한컴")
_REGISTRY_MODULE_PATHS = (
    r"SOFTWARE\HNC\HwpAutomation\Modules",
    r"SOFTWARE\Hnc\HwpAutomation\Modules",
)
_KNOWN_MODULE_NAMES = (
    "SecurityModule",
    "FilePathCheckerModule",
    "FilePathCheckerModuleExample",
    "AutomationModule",
    "HanToPdfSecurityModule",
)
_AUTO_MODULE_NAME = "HanToPdfSecurityModule"

_registry_module_cache: list[str] | None = None
_security_registry_ensured = False


def _window_text(hwnd: int) -> str:
    try:
        return win32gui.GetWindowText(hwnd)
    except win32gui.error:
        return ""


def _control_text(hwnd: int) -> str:
    try:
        length = win32gui.SendMessage(hwnd, win32con.WM_GETTEXTLENGTH, 0, 0)
        if length <= 0:
            return _window_text(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        win32gui.SendMessage(hwnd, win32con.WM_GETTEXT, length + 1, buf)
        return buf.value or _window_text(hwnd)
    except Exception:
        return _window_text(hwnd)


def _collect_texts(hwnd: int) -> str:
    parts = [_window_text(hwnd)]

    def child(child_hwnd, _):
        try:
            cls = win32gui.GetClassName(child_hwnd)
        except win32gui.error:
            return True
        if cls in ("Static", "Button", "Edit"):
            parts.append(_control_text(child_hwnd))
        else:
            parts.append(_window_text(child_hwnd))
        return True

    try:
        win32gui.EnumChildWindows(hwnd, child, None)
    except win32gui.error:
        pass
    return "\n".join(parts)


def _find_buttons(hwnd: int) -> list[tuple[int, str]]:
    buttons: list[tuple[int, str]] = []

    def child(child_hwnd, _):
        try:
            if win32gui.GetClassName(child_hwnd) == "Button":
                buttons.append((child_hwnd, _control_text(child_hwnd)))
        except win32gui.error:
            pass
        return True

    try:
        win32gui.EnumChildWindows(hwnd, child, None)
    except win32gui.error:
        pass
    return buttons


def _has_allow_buttons(hwnd: int) -> bool:
    texts = " ".join(text for _, text in _find_buttons(hwnd))
    return any(k in texts for k in _ALLOW_ACCESS_KEYWORDS + _ALLOW_ALL_KEYWORDS)


def _is_hwp_security_dialog(hwnd: int) -> bool:
    if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
        return False
    try:
        if win32gui.GetClassName(hwnd) != "#32770":
            return False
    except win32gui.error:
        return False

    title = _window_text(hwnd)
    body = _collect_texts(hwnd)
    title_match = any(part in title for part in _HWP_TITLE_PARTS)
    security_match = any(k in body for k in _SECURITY_KEYWORDS)
    file_match = any(m in body.lower() for m in _FILE_MARKERS)
    button_match = _has_allow_buttons(hwnd)

    if button_match and (title_match or file_match or security_match):
        return True
    return security_match and (title_match or file_match)


def _discover_registry_module_names(*, refresh: bool = False) -> list[str]:
    global _registry_module_cache
    if not refresh and _registry_module_cache is not None:
        return _registry_module_cache

    names: list[str] = []
    seen: set[str] = set()
    for path in _REGISTRY_MODULE_PATHS:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
                index = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, index)
                        index += 1
                        if not name or name in seen:
                            continue
                        dll_path = str(value or "").strip().strip('"')
                        if dll_path.lower().endswith(".dll"):
                            seen.add(name)
                            names.append(name)
                    except OSError:
                        break
        except OSError:
            continue
    _registry_module_cache = names
    return names


def _search_security_dll() -> Path | None:
    names = (
        "FilePathCheckerModuleExample.dll",
        "FilePathCheckerModule.dll",
        "FilePathCeckerModuleExample.dll",
    )
    roots: list[Path] = []
    for env in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        value = os.environ.get(env)
        if value:
            roots.append(Path(value))
    app_dir = Path(__file__).resolve().parent
    roots.extend((app_dir, app_dir / "assets", app_dir / "security"))

    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for name in names:
            direct = root / name
            if direct.is_file():
                return direct.resolve()
        try:
            for pattern in ("FilePathChecker*.dll", "FilePathCecker*.dll"):
                for match in root.rglob(pattern):
                    resolved = match.resolve()
                    if resolved not in seen:
                        seen.add(resolved)
                        return resolved
        except OSError:
            continue
    return None


def _write_registry_module(name: str, dll_path: Path) -> None:
    for rel in _REGISTRY_MODULE_PATHS:
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rel) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(dll_path))
            return
        except OSError:
            continue


def ensure_hwp_security_module_registered() -> bool:
    """PC에 보안 DLL이 있으면 레지스트리에 자동 등록."""
    global _security_registry_ensured
    if _security_registry_ensured:
        return True
    if _discover_registry_module_names():
        _security_registry_ensured = True
        return True
    dll = _search_security_dll()
    if dll is None:
        return False
    _write_registry_module(_AUTO_MODULE_NAME, dll)
    _discover_registry_module_names(refresh=True)
    _security_registry_ensured = True
    return True


def register_hwp_security_modules(hwp) -> None:
    """레지스트리·기본 이름으로 보안 모듈 등록 — 팝업 자체를 막음."""
    ensure_hwp_security_module_registered()
    module_names = list(_discover_registry_module_names())
    for name in _KNOWN_MODULE_NAMES:
        if name not in module_names:
            module_names.append(name)

    for name in module_names:
        try:
            hwp.RegisterModule("FilePathCheckDLL", name)
        except Exception:
            pass

    for mode in (0x00214411, 0x00020000, 0x00001000, 0x1104412):
        try:
            hwp.SetMessageBoxMode(mode)
        except Exception:
            pass


def _allow_foreground() -> None:
    try:
        ctypes.windll.user32.AllowSetForegroundWindow(0xFFFFFFFF)
    except Exception:
        pass


def _force_foreground(hwnd: int) -> bool:
    _allow_foreground()
    try:
        if win32gui.GetForegroundWindow() == hwnd:
            return True
        fg = win32gui.GetForegroundWindow()
        fg_thread, _ = win32process.GetWindowThreadProcessId(fg)
        target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
        attached = False
        if fg_thread != target_thread:
            win32api.AttachThreadInput(fg_thread, target_thread, True)
            attached = True
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
        finally:
            if attached:
                win32api.AttachThreadInput(fg_thread, target_thread, False)
        return True
    except Exception:
        return False


def _matches_keywords(text: str, keywords: tuple[str, ...]) -> bool:
    return any(k in text for k in keywords)


def _click_button(btn_hwnd: int, dialog_hwnd: int) -> None:
    btn_id = win32gui.GetDlgCtrlID(btn_hwnd)
    actions = (
        lambda: win32gui.SendMessage(btn_hwnd, win32con.BM_CLICK, 0, 0),
        lambda: win32api.PostMessage(btn_hwnd, win32con.BM_CLICK, 0, 0),
        lambda: win32gui.SendMessage(dialog_hwnd, win32con.WM_COMMAND, btn_id, btn_hwnd),
        lambda: win32api.PostMessage(dialog_hwnd, win32con.WM_COMMAND, btn_id, btn_hwnd),
    )
    rect = win32gui.GetWindowRect(btn_hwnd)
    cx = (rect[2] - rect[0]) // 2
    cy = (rect[3] - rect[1]) // 2
    lparam = win32api.MAKELONG(cx, cy)
    actions += (
        lambda: win32gui.SendMessage(btn_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam),
        lambda: win32gui.SendMessage(btn_hwnd, win32con.WM_LBUTTONUP, 0, lparam),
    )
    for action in actions:
        try:
            action()
        except Exception:
            continue


def _click_default_button(dialog_hwnd: int) -> bool:
    try:
        default = win32gui.SendMessage(dialog_hwnd, win32con.DM_GETDEFID, 0, 0)
        if default:
            btn_id = default & 0xFFFF
            btn_hwnd = win32gui.GetDlgItem(dialog_hwnd, btn_id)
            if btn_hwnd:
                _click_button(btn_hwnd, dialog_hwnd)
                return True
    except Exception:
        pass
    return False


def _click_by_keywords(dialog_hwnd: int, keywords: tuple[str, ...]) -> bool:
    for btn_hwnd, text in _find_buttons(dialog_hwnd):
        if _matches_keywords(text, keywords):
            _click_button(btn_hwnd, dialog_hwnd)
            return True
    return False


def _send_vk(vk: int, extended: bool = False) -> None:
    flags = 0
    if extended:
        flags |= win32con.KEYEVENTF_EXTENDEDKEY
    win32api.keybd_event(vk, 0, flags, 0)
    win32api.keybd_event(vk, 0, flags | win32con.KEYEVENTF_KEYUP, 0)


def _press_char(ch: str) -> None:
    vk_scan = win32api.VkKeyScan(ch)
    if vk_scan == -1:
        return
    vk = vk_scan & 0xFF
    shift = (vk_scan >> 8) & 1
    if shift:
        _send_vk(win32con.VK_SHIFT)
    _send_vk(vk)
    if shift:
        _send_vk(win32con.VK_SHIFT)


def _post_key_to_dialog(dialog_hwnd: int, vk: int) -> None:
    try:
        win32api.PostMessage(dialog_hwnd, win32con.WM_KEYDOWN, vk, 0)
        win32api.PostMessage(dialog_hwnd, win32con.WM_KEYUP, vk, 0)
    except Exception:
        pass


def _force_keyboard_allow(dialog_hwnd: int) -> None:
    _force_foreground(dialog_hwnd)
    time.sleep(0.06)
    try:
        win32gui.SetActiveWindow(dialog_hwnd)
        win32gui.SetFocus(dialog_hwnd)
    except Exception:
        pass

    for action in (
        lambda: _press_char("Y"),
        lambda: _send_vk(win32con.VK_RETURN),
        lambda: _post_key_to_dialog(dialog_hwnd, ord("Y")),
        lambda: _post_key_to_dialog(dialog_hwnd, win32con.VK_RETURN),
        lambda: _press_char("N"),
        lambda: _post_key_to_dialog(dialog_hwnd, ord("N")),
        lambda: _send_vk(win32con.VK_RETURN),
    ):
        try:
            action()
            time.sleep(0.05)
        except Exception:
            continue


def _dialog_still_open(hwnd: int) -> bool:
    return win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd) and _is_hwp_security_dialog(hwnd)


def _dismiss_dialog(hwnd: int) -> bool:
    """접근 허용 → 모두 허용 → 기본 버튼 → 키보드 강제."""
    steps = (
        lambda: _click_by_keywords(hwnd, _ALLOW_ACCESS_KEYWORDS),
        lambda: _click_by_keywords(hwnd, _ALLOW_ALL_KEYWORDS),
        lambda: _click_default_button(hwnd),
        lambda: _force_keyboard_allow(hwnd) or True,
    )
    for step in steps:
        step()
        time.sleep(0.08)
        if not _dialog_still_open(hwnd):
            return True

    buttons = _find_buttons(hwnd)
    if buttons:
        _click_button(buttons[0][0], hwnd)
        time.sleep(0.08)
        if not _dialog_still_open(hwnd):
            return True

    _force_keyboard_allow(hwnd)
    return not _dialog_still_open(hwnd)


def find_hwp_security_dialogs() -> list[int]:
    dialogs: list[int] = []

    def enum_cb(hwnd, _):
        if _is_hwp_security_dialog(hwnd):
            dialogs.append(hwnd)
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
    except win32gui.error:
        pass
    return dialogs


def dismiss_hwp_security_dialog() -> bool:
    """보이는 한글 보안 대화상자가 있으면 접근 허용 처리."""
    dismissed = False
    for hwnd in find_hwp_security_dialogs():
        if _dismiss_dialog(hwnd):
            dismissed = True
    return dismissed


def wait_for_security_dialogs(timeout: float = 3.0, interval: float = 0.08) -> None:
    """파일 열기 직후 뜨는 보안 창을 닫힐 때까지 반복 처리."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        dialogs = find_hwp_security_dialogs()
        if not dialogs:
            return
        for hwnd in dialogs:
            _dismiss_dialog(hwnd)
        time.sleep(interval)


class HwpSecurityDialogWatcher:
    """변환 중 보안 대화상자를 주기적으로 자동 허용."""

    def __init__(self, interval: float = 0.12):
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.stop()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="HwpSecurityWatcher", daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            dismiss_hwp_security_dialog()
            self._stop.wait(self._interval)
