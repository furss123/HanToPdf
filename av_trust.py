"""백신 검사 예외 자동 등록 (Windows Defender + AhnLab V3)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

_CREATE_NO_WINDOW = 0x08000000
_TRUST_STATE = ".hantopdf_trust_state.json"
_AHNLAB_PS1 = Path(__file__).resolve().parent / "scripts" / "ahnlab_trust.ps1"

# 안랩 Safe Transaction MDP 오탐 진단명
_AHNLAB_MDP_NAMES = (
    "DefenseEvasion/MDP.Event.M1423",
    "DefenseEvasion/MDP",
)


def _appdata_dir() -> Path:
    return Path(os.environ.get("APPDATA", str(Path.home()))) / "HanToPdf"


def _local_hantopdf_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "HanToPdf"


def _trust_state_path() -> Path:
    return _appdata_dir() / _TRUST_STATE


def _trust_log_path() -> Path:
    return _appdata_dir() / "trust.log"


def _paths_to_trust(install_dir: Path) -> list[str]:
    install_dir = install_dir.resolve()
    local_base = _local_hantopdf_dir().resolve()
    paths = [str(install_dir), str(local_base)]
    exe = install_dir / "HanToPdf.exe"
    if exe.is_file():
        paths.append(str(exe.resolve()))
    return paths


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_trust_state() -> dict:
    path = _trust_state_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _save_trust_state(state: dict) -> None:
    path = _trust_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_hidden(cmd: list[str], *, timeout: float = 60) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=_CREATE_NO_WINDOW,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _add_defender_exclusions(paths: list[str], *, exe_path: Path | None) -> bool:
    if not paths and not exe_path:
        return False

    parts: list[str] = []
    if paths:
        quoted = ",".join("'" + p.replace("'", "''") + "'" for p in paths)
        parts.append(f"Add-MpPreference -ExclusionPath @({quoted})")
    if exe_path and exe_path.is_file():
        exe = str(exe_path.resolve()).replace("'", "''")
        parts.append(f"Add-MpPreference -ExclusionProcess @('{exe}')")
        parts.append("Add-MpPreference -ExclusionProcess @('HanToPdf.exe')")

    script = "$ErrorActionPreference = 'SilentlyContinue'; " + "; ".join(parts)
    result = _run_hidden(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        timeout=30,
    )
    return result is not None and result.returncode == 0


def _ahnlab_ps1_path() -> Path:
    if _AHNLAB_PS1.is_file():
        return _AHNLAB_PS1
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        bundled = meipass / "scripts" / "ahnlab_trust.ps1"
        if bundled.is_file():
            return bundled
    return _AHNLAB_PS1


def _add_ahnlab_exclusions(paths: list[str], *, exe_path: Path | None) -> bool:
    ps1 = _ahnlab_ps1_path()
    if not ps1.is_file():
        _log_trust("ahnlab_trust.ps1 없음 — 안랩 자동 등록 스킵")
        return False

    args = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-File",
        str(ps1),
        "-Paths",
    ] + paths
    args.extend(["-LogPath", str(_trust_log_path())])
    if exe_path and exe_path.is_file():
        args.extend(["-ExePath", str(exe_path.resolve())])

    result = _run_hidden(args, timeout=90)
    return result is not None


def _log_trust(message: str) -> None:
    line = f"[trust] {message}"
    try:
        path = _trust_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            from datetime import datetime

            fh.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {line}\n")
    except OSError:
        pass


def _needs_refresh(install_dir: Path, *, force: bool) -> bool:
    if force:
        return True
    install_dir = install_dir.resolve()
    exe = install_dir / "HanToPdf.exe"
    exe_hash = _sha256_file(exe) if exe.is_file() else ""
    state = _load_trust_state()
    if state.get("install_dir") != str(install_dir):
        return True
    if exe_hash and state.get("exe_sha256") != exe_hash:
        return True
    return not state.get("registered")


def ensure_update_paths_trusted(install_dir: Path, *, force: bool = False) -> None:
    """설치·스테이징 경로를 Defender·AhnLab 검사 예외에 자동 등록."""
    install_dir = install_dir.resolve()
    if not _needs_refresh(install_dir, force=force):
        return

    paths = _paths_to_trust(install_dir)
    exe_path = install_dir / "HanToPdf.exe"

    defender_ok = _add_defender_exclusions(paths, exe_path=exe_path)
    if defender_ok:
        _log_trust("Windows Defender 예외 등록")

    _add_ahnlab_exclusions(paths, exe_path=exe_path)

    state = {
        "registered": True,
        "install_dir": str(install_dir),
        "paths": paths,
        "exe_sha256": _sha256_file(exe_path) if exe_path.is_file() else "",
        "ahnlab_mdp": list(_AHNLAB_MDP_NAMES),
        "defender": defender_ok,
    }
    _save_trust_state(state)
    _log_trust(f"신뢰 경로 등록 완료: {install_dir}")
