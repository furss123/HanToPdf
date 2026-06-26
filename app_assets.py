"""앱 리소스(아이콘 등) 경로"""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

_INSTALLED_FONT_KEYS: set[str] = set()


def asset_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "assets"
    else:
        base = ASSETS_DIR
    return base / name


def noto_sans_kr_path() -> Path:
    return asset_path("fonts/NotoSansKR.ttf")


def _install_font_file(path: Path) -> bool:
    key = str(path.resolve())
    if key in _INSTALLED_FONT_KEYS:
        return True
    if not path.is_file():
        return False
    added = ctypes.windll.gdi32.AddFontResourceExW(key, 0x10, 0)
    if added <= 0:
        return False
    _INSTALLED_FONT_KEYS.add(key)
    return True


def install_app_fonts() -> bool:
    """Noto Sans KR 번들 폰트 등록."""
    return _install_font_file(noto_sans_kr_path())


def install_noto_sans_kr() -> bool:
    return install_app_fonts()


def load_photo(window: tk.Misc, name: str) -> tk.PhotoImage | None:
    path = asset_path(name)
    if not path.exists():
        return None
    try:
        img = tk.PhotoImage(file=str(path))
    except tk.TclError:
        return None
    if not hasattr(window, "_photo_refs"):
        window._photo_refs = []  # noqa: SLF001
    window._photo_refs.append(img)
    return img


def apply_window_icon(window: tk.Misc) -> None:
    """메인/설정 창 타이틀바 아이콘."""
    ico = asset_path("icon.ico")
    if ico.exists():
        try:
            window.iconbitmap(default=str(ico))
            return
        except tk.TclError:
            pass
    img = load_photo(window, "icon.png")
    if img is not None:
        window.iconphoto(True, img)
