"""바탕화면 HanToPdf.lnk 생성·갱신."""

from __future__ import annotations

import ctypes
import subprocess
from pathlib import Path

SHORTCUT_NAME = "HanToPdf.lnk"
SHORTCUT_DESCRIPTION = "HanToPdf - 한글 파일 PDF 변환기"

_SHCNE_ASSOCCHANGED = 0x08000000
_SHCNF_IDLIST = 0x0000
_CREATE_NO_WINDOW = 0x08000000


def _desktop_dir() -> Path:
    import win32com.client

    shell = win32com.client.Dispatch("WScript.Shell")
    return Path(shell.SpecialFolders("Desktop"))


def _resolve_icon(install_dir: Path, exe_path: Path) -> str:
    """exe 내장 아이콘 우선 — 업데이트 시 Windows 아이콘 캐시 문제를 줄임."""
    return f"{exe_path.resolve()},0"


def _notify_shell_icon_change() -> None:
    try:
        ctypes.windll.shell32.SHChangeNotify(
            _SHCNE_ASSOCCHANGED,
            _SHCNF_IDLIST,
            None,
            None,
        )
    except OSError:
        pass

    system_root = Path(__import__("os").environ.get("SystemRoot", r"C:\Windows"))
    ie4uinit = system_root / "System32" / "ie4uinit.exe"
    if ie4uinit.is_file():
        try:
            subprocess.Popen(
                [str(ie4uinit), "-show"],
                close_fds=True,
                creationflags=_CREATE_NO_WINDOW,
            )
        except OSError:
            pass


def refresh_desktop_shortcut(install_dir: Path, exe_path: Path) -> Path:
    """바탕화면 바로가기를 최신 exe·아이콘으로 갱신."""
    import win32com.client

    install_dir = install_dir.resolve()
    exe_path = exe_path.resolve()
    shortcut_path = _desktop_dir() / SHORTCUT_NAME

    if shortcut_path.is_file():
        shortcut_path.unlink()

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(shortcut_path))
    shortcut.TargetPath = str(exe_path)
    shortcut.WorkingDirectory = str(install_dir)
    shortcut.Description = SHORTCUT_DESCRIPTION
    shortcut.IconLocation = _resolve_icon(install_dir, exe_path)
    shortcut.Save()

    _notify_shell_icon_change()
    return shortcut_path
