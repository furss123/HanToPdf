"""앱 버전 — 배포 시 build.ps1 / package_release.ps1 과 VERSION.txt 를 함께 갱신하세요."""

from __future__ import annotations

import sys
from pathlib import Path

_DEFAULT = "1.0.8"


def _read_installed_version() -> str:
    if getattr(sys, "frozen", False):
        version_file = Path(sys.executable).resolve().parent / "VERSION.txt"
        if version_file.is_file():
            text = version_file.read_text(encoding="utf-8-sig").strip()
            if text:
                return text
    return _DEFAULT


__version__ = _read_installed_version()
