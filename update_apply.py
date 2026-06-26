"""HanToPdf 자동 업데이트 적용 (PowerShell 없이 동일 exe로 실행)."""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path

_LOG_PATH = Path(os.environ.get("APPDATA", str(Path.home()))) / "HanToPdf" / "update.log"
_LOCAL_BASE = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "HanToPdf"
_APPLY_PS1 = _LOCAL_BASE / "apply_update.ps1"

_SYNCHRONIZE = 0x00100000
_WAIT_TIMEOUT_MS = 120_000
_COPY_RETRIES = 8
_COPY_RETRY_DELAY = 0.75
_CREATE_NO_WINDOW = 0x08000000
_DETACHED_PROCESS = 0x00000008


def _log(message: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def _log_exception(context: str) -> None:
    _log(f"{context}\n{traceback.format_exc()}")


def _desktop_dir() -> Path | None:
    try:
        import win32com.client

        shell = win32com.client.Dispatch("WScript.Shell")
        return Path(shell.SpecialFolders("Desktop"))
    except Exception:
        profile = os.environ.get("USERPROFILE", "")
        if profile:
            return Path(profile) / "Desktop"
        return None


def cleanup_legacy_update_artifacts() -> None:
    """예전 버전이 바탕화면·TEMP에 남긴 스테이징 폴더 정리."""
    desktop = _desktop_dir()
    if desktop and desktop.is_dir():
        for item in desktop.glob("_HanToPdf_update_*"):
            shutil.rmtree(item, ignore_errors=True)

    staging_root = _LOCAL_BASE / "staging"
    if staging_root.is_dir():
        for item in staging_root.glob("extract_*"):
            shutil.rmtree(item, ignore_errors=True)

    runtime_root = _LOCAL_BASE / "updater-runtime"
    if runtime_root.is_dir():
        shutil.rmtree(runtime_root, ignore_errors=True)


def _make_extract_dir() -> Path:
    root = _LOCAL_BASE / "staging"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="extract_", dir=root))


def _wait_for_process(pid: int) -> None:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(_SYNCHRONIZE, False, pid)
    if not handle:
        _log(f"OpenProcess 실패(pid={pid}), 3초 대기")
        time.sleep(3)
        return
    try:
        result = kernel32.WaitForSingleObject(handle, _WAIT_TIMEOUT_MS)
        if result != 0:
            _log(f"WaitForSingleObject 타임아웃(pid={pid}, code={result})")
    finally:
        kernel32.CloseHandle(handle)


def _count_processes(image_name: str) -> int:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/NH"],
            capture_output=True,
            text=True,
            creationflags=_CREATE_NO_WINDOW,
        )
    except OSError:
        return 0
    return sum(1 for line in result.stdout.splitlines() if image_name.lower() in line.lower())


def _wait_for_install_idle(parent_pid: int) -> None:
    """설치 폴더 exe가 모두 종료될 때까지 대기."""
    _wait_for_process(parent_pid)
    for attempt in range(120):
        count = _count_processes("HanToPdf.exe")
        if count == 0:
            break
        if attempt % 10 == 0:
            _log(f"HanToPdf.exe 프로세스 대기 중... (count={count})")
        time.sleep(0.5)
    else:
        _log("HanToPdf.exe 프로세스 대기 타임아웃")
    time.sleep(2)


def _resolve_zip_root(staging: Path) -> Path:
    nested = staging / "HanToPdf"
    if nested.is_dir() and (nested / "HanToPdf.exe").is_file():
        return nested
    if (staging / "HanToPdf.exe").is_file():
        return staging
    children = [p for p in staging.iterdir() if p.is_dir()]
    if len(children) == 1 and (children[0] / "HanToPdf.exe").is_file():
        return children[0]
    return staging


def _copy_file_with_retry(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    last_exc: OSError | None = None
    for attempt in range(_COPY_RETRIES):
        try:
            if dst.exists() and dst.is_file():
                dst.unlink()
            shutil.copy2(src, dst)
            return
        except OSError as exc:
            last_exc = exc
            time.sleep(_COPY_RETRY_DELAY * (attempt + 1))
    if last_exc is not None:
        raise last_exc
    raise OSError(f"copy failed: {src} -> {dst}")


def _copy_tree(src: Path, dst: Path) -> int:
    copied = 0
    for item in sorted(src.rglob("*")):
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        _copy_file_with_retry(item, target)
        copied += 1
    return copied


def _write_apply_ps1() -> Path:
    """exe 자기복사 없이 PowerShell로 적용 — 안랩 DefenseEvasion 오탐 완화."""
    _LOCAL_BASE.mkdir(parents=True, exist_ok=True)
    script = r'''param(
    [int]$ParentPid,
    [string]$InstallDir,
    [string]$ZipPath,
    [string]$ExePath,
    [string]$LogPath
)

$ErrorActionPreference = 'Stop'

function Write-UpdateLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    try {
        $dir = Split-Path -Parent $LogPath
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Add-Content -Path $LogPath -Value $line -Encoding UTF8
    } catch {}
}

function Wait-InstallIdle {
    if ($ParentPid -gt 0) {
        try {
            Wait-Process -Id $ParentPid -Timeout 120 -ErrorAction SilentlyContinue
        } catch {}
    }
    for ($i = 0; $i -lt 120; $i++) {
        $procs = @(Get-Process -Name 'HanToPdf' -ErrorAction SilentlyContinue)
        if ($procs.Count -eq 0) { break }
        if (($i % 10) -eq 0) {
            Write-UpdateLog "HanToPdf.exe 프로세스 대기 중... (count=$($procs.Count))"
        }
        Start-Sleep -Milliseconds 500
    }
    Start-Sleep -Seconds 2
}

function Resolve-ZipRoot {
    param([string]$Staging)
    $nested = Join-Path $Staging 'HanToPdf'
    if ((Test-Path (Join-Path $nested 'HanToPdf.exe'))) { return $nested }
    if (Test-Path (Join-Path $Staging 'HanToPdf.exe')) { return $Staging }
    $dirs = @(Get-ChildItem -Path $Staging -Directory -ErrorAction SilentlyContinue)
    if ($dirs.Count -eq 1 -and (Test-Path (Join-Path $dirs[0].FullName 'HanToPdf.exe'))) {
        return $dirs[0].FullName
    }
    return $Staging
}

function Update-DesktopShortcut {
    param([string]$Install, [string]$Exe)
    $desktop = [Environment]::GetFolderPath('Desktop')
    $lnk = Join-Path $desktop 'HanToPdf.lnk'
    if (Test-Path $lnk) { Remove-Item -LiteralPath $lnk -Force }
    $shell = New-Object -ComObject WScript.Shell
    $sc = $shell.CreateShortcut($lnk)
    $sc.TargetPath = $Exe
    $sc.WorkingDirectory = $Install
    $sc.Description = 'HanToPdf - 한글 파일 PDF 변환기'
    $sc.IconLocation = "$Exe,0"
    $sc.Save()
    try {
        Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class HanToPdfShellNotify {
    [DllImport("shell32.dll")]
    public static extern void SHChangeNotify(int eventId, uint flags, IntPtr item1, IntPtr item2);
}
"@ -ErrorAction SilentlyContinue | Out-Null
        [HanToPdfShellNotify]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
    } catch {}
    $ie4uinit = Join-Path $env:SystemRoot 'System32\ie4uinit.exe'
    if (Test-Path $ie4uinit) {
        Start-Process -FilePath $ie4uinit -ArgumentList '-show' -WindowStyle Hidden -ErrorAction SilentlyContinue
    }
    Write-UpdateLog "바탕화면 바로가기 갱신: $lnk"
}

try {
    Write-UpdateLog "PowerShell 업데이트 시작 pid=$ParentPid install=$InstallDir zip=$ZipPath"
    Wait-InstallIdle

    if (-not (Test-Path -LiteralPath $ZipPath)) {
        throw "ZIP 없음: $ZipPath"
    }

    $stagingRoot = Join-Path $env:LOCALAPPDATA 'HanToPdf\staging'
    if (-not (Test-Path $stagingRoot)) { New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null }
    $staging = Join-Path $stagingRoot ("extract_" + [guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Path $staging -Force | Out-Null

    try {
        Expand-Archive -LiteralPath $ZipPath -DestinationPath $staging -Force
        $src = Resolve-ZipRoot -Staging $staging
        if (-not (Test-Path (Join-Path $src 'HanToPdf.exe'))) {
            throw "ZIP 안에 HanToPdf.exe 없음: $src"
        }

        $robocopyArgs = @(
            $src, $InstallDir,
            '/E', '/IS', '/IT', '/R:3', '/W:1',
            '/NFL', '/NDL', '/NJH', '/NJS', '/nc', '/ns', '/np'
        )
        & robocopy.exe @robocopyArgs | Out-Null
        $rc = $LASTEXITCODE
        if ($rc -ge 8) {
            throw "robocopy 실패 (exit=$rc)"
        }
        Write-UpdateLog "파일 복사 완료 (robocopy exit=$rc) -> $InstallDir"

        $versionFile = Join-Path $InstallDir 'VERSION.txt'
        if (Test-Path $versionFile) {
            $ver = (Get-Content -LiteralPath $versionFile -Raw -Encoding UTF8).Trim()
            Write-UpdateLog "설치 버전: $ver"
        }

        if (-not (Test-Path -LiteralPath $ExePath)) {
            throw "업데이트 후 exe 없음: $ExePath"
        }

        Update-DesktopShortcut -Install $InstallDir -Exe $ExePath
        Start-Process -FilePath $ExePath -WorkingDirectory $InstallDir
        Write-UpdateLog "재시작: $ExePath"
    } finally {
        if (Test-Path $staging) { Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue }
        if (Test-Path -LiteralPath $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force -ErrorAction SilentlyContinue }
    }
} catch {
    Write-UpdateLog ("업데이트 실패: " + $_.Exception.Message)
    exit 1
}
'''
    _APPLY_PS1.write_text(script, encoding="utf-8-sig")
    return _APPLY_PS1


def launch_apply_update(
    *,
    parent_pid: int,
    install_dir: Path,
    zip_path: Path,
    exe_path: Path,
) -> None:
    """PowerShell로 업데이트 적용 (HanToPdf exe 자기복사 없음)."""
    from av_trust import ensure_update_paths_trusted

    cleanup_legacy_update_artifacts()
    ensure_update_paths_trusted(install_dir, force=True)

    ps1 = _write_apply_ps1()
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-File",
            str(ps1),
            "-ParentPid",
            str(parent_pid),
            "-InstallDir",
            str(install_dir.resolve()),
            "-ZipPath",
            str(zip_path.resolve()),
            "-ExePath",
            str(exe_path.resolve()),
            "-LogPath",
            str(_LOG_PATH),
        ],
        close_fds=True,
        creationflags=_DETACHED_PROCESS | _CREATE_NO_WINDOW,
    )
    _log(f"PowerShell 업데이트 프로세스 시작: {ps1}")


def apply_update(
    *,
    parent_pid: int,
    install_dir: Path,
    zip_path: Path,
    exe_path: Path,
) -> None:
    """Python 직접 적용 (개발·폴백용)."""
    install_dir = install_dir.resolve()
    zip_path = zip_path.resolve()
    exe_path = exe_path.resolve()
    _log(f"업데이트 시작 pid={parent_pid} install={install_dir} zip={zip_path}")

    cleanup_legacy_update_artifacts()
    _wait_for_install_idle(parent_pid)

    if not zip_path.is_file():
        raise FileNotFoundError(f"ZIP 없음: {zip_path}")

    staging = _make_extract_dir()
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(staging)
        src = _resolve_zip_root(staging)
        if not (src / "HanToPdf.exe").is_file():
            raise FileNotFoundError(f"ZIP 안에 HanToPdf.exe 없음: {src}")

        count = _copy_tree(src, install_dir)
        _log(f"파일 복사 완료: {count}개 -> {install_dir}")

        version_file = install_dir / "VERSION.txt"
        if version_file.is_file():
            _log(f"설치 버전: {version_file.read_text(encoding='utf-8-sig').strip()}")
        else:
            _log("VERSION.txt 없음 — 구버전 패키지일 수 있음")

        if not exe_path.is_file():
            raise FileNotFoundError(f"업데이트 후 exe 없음: {exe_path}")
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        try:
            zip_path.unlink()
        except OSError:
            _log(f"ZIP 삭제 실패: {zip_path}")

    from desktop_shortcut import refresh_desktop_shortcut

    try:
        shortcut_path = refresh_desktop_shortcut(install_dir, exe_path)
        _log(f"바탕화면 바로가기 갱신: {shortcut_path}")
    except Exception:
        _log_exception("바로가기 갱신 실패(계속 재시작)")

    subprocess.Popen(
        [str(exe_path)],
        cwd=str(install_dir),
        close_fds=True,
    )
    _log(f"재시작: {exe_path}")


def run_apply_update_cli(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 4:
        _log(f"인자 부족: {args}")
        return 2
    try:
        parent_pid = int(args[0])
        install_dir = Path(args[1])
        zip_path = Path(args[2])
        exe_path = Path(args[3])
        apply_update(
            parent_pid=parent_pid,
            install_dir=install_dir,
            zip_path=zip_path,
            exe_path=exe_path,
        )
        return 0
    except Exception:
        _log_exception("업데이트 실패")
        return 1


if __name__ == "__main__":
    raise SystemExit(run_apply_update_cli())
