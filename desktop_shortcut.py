"""바탕화면 HanToPdf.lnk 생성·갱신."""

from __future__ import annotations

from pathlib import Path

SHORTCUT_NAME = "HanToPdf.lnk"
SHORTCUT_DESCRIPTION = "HanToPdf - 한글 파일 PDF 변환기"


def _desktop_dir() -> Path:
    import win32com.client

    shell = win32com.client.Dispatch("WScript.Shell")
    return Path(shell.SpecialFolders("Desktop"))


def _resolve_icon(install_dir: Path, exe_path: Path) -> str:
    for parts in (("assets", "icon.ico"), ("_internal", "assets", "icon.ico")):
        icon = install_dir.joinpath(*parts)
        if icon.is_file():
            return f"{icon},0"
    return f"{exe_path},0"


def refresh_desktop_shortcut(install_dir: Path, exe_path: Path) -> Path:
    """바탕화면 바로가기를 최신 exe·아이콘으로 갱신."""
    import win32com.client

    install_dir = install_dir.resolve()
    exe_path = exe_path.resolve()
    shortcut_path = _desktop_dir() / SHORTCUT_NAME

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(shortcut_path))
    shortcut.TargetPath = str(exe_path)
    shortcut.WorkingDirectory = str(install_dir)
    shortcut.Description = SHORTCUT_DESCRIPTION
    shortcut.IconLocation = _resolve_icon(install_dir, exe_path)
    shortcut.Save()
    return shortcut_path
