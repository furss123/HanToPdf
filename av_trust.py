"""업데이트 경로를 Windows Defender 예외에 등록 (안랩 MDP 오탐 완화 보조)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

_CREATE_NO_WINDOW = 0x08000000
_TRUST_MARKER = ".hantopdf_trusted"


def _local_hantopdf_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "HanToPdf"


def _trust_marker_path(install_dir: Path) -> Path:
    return _local_hantopdf_dir() / _TRUST_MARKER


def _paths_to_trust(install_dir: Path) -> list[str]:
    install_dir = install_dir.resolve()
    local_base = _local_hantopdf_dir().resolve()
    return [str(install_dir), str(local_base)]


def _add_defender_exclusions(paths: list[str]) -> bool:
    if not paths:
        return False
    quoted = ",".join("'" + p.replace("'", "''") + "'" for p in paths)
    script = (
        "$ErrorActionPreference = 'SilentlyContinue'; "
        f"Add-MpPreference -ExclusionPath @({quoted})"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            creationflags=_CREATE_NO_WINDOW,
            timeout=30,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def ensure_update_paths_trusted(install_dir: Path, *, force: bool = False) -> None:
    """설치·스테이징 폴더를 Defender 검사 예외에 등록 (이미 등록 시 스킵)."""
    install_dir = install_dir.resolve()
    marker = _trust_marker_path(install_dir)
    if not force and marker.is_file():
        try:
            if marker.read_text(encoding="utf-8").strip() == str(install_dir):
                return
        except OSError:
            pass

    paths = _paths_to_trust(install_dir)
    if _add_defender_exclusions(paths):
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(install_dir), encoding="utf-8")
