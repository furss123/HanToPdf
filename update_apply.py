"""HanToPdf 자동 업데이트 적용 (PowerShell 없이 동일 exe로 실행)."""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path

_LOG_PATH = Path(os.environ.get("APPDATA", str(Path.home()))) / "HanToPdf" / "update.log"
_LOCAL_BASE = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "HanToPdf"

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


def _make_extract_dir() -> Path:
    root = _LOCAL_BASE / "staging"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="extract_", dir=root))


def _prepare_detached_updater(install_dir: Path) -> Path:
    """설치 폴더 DLL 잠금을 피하려고 LOCALAPPDATA에 실행 복사본 생성."""
    install_dir = install_dir.resolve()
    runtime_root = _LOCAL_BASE / "updater-runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    runtime = Path(tempfile.mkdtemp(prefix="run_", dir=runtime_root))

    src_exe = install_dir / "HanToPdf.exe"
    src_internal = install_dir / "_internal"
    if not src_exe.is_file():
        raise FileNotFoundError(f"실행 파일 없음: {src_exe}")
    if not src_internal.is_dir():
        raise FileNotFoundError(f"_internal 폴더 없음: {src_internal}")

    shutil.copy2(src_exe, runtime / "HanToPdf.exe")
    shutil.copytree(src_internal, runtime / "_internal")
    _log(f"분리 업데이터 준비: {runtime}")
    return runtime / "HanToPdf.exe"


def _schedule_dir_cleanup(path: Path) -> None:
    import subprocess

    if not path.exists():
        return
    cmd = f'ping 127.0.0.1 -n 3 >nul & rmdir /s /q "{path}"'
    subprocess.Popen(
        ["cmd.exe", "/c", cmd],
        close_fds=True,
        creationflags=_CREATE_NO_WINDOW,
    )


def _is_detached_runtime() -> bool:
    if not getattr(sys, "frozen", False):
        return False
    return "updater-runtime" in Path(sys.executable).resolve().as_posix()


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
    import subprocess

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
    """설치 폴더 exe가 모두 종료될 때까지 대기 (업데이터 프로세스만 남을 때까지)."""
    _wait_for_process(parent_pid)
    for attempt in range(120):
        count = _count_processes("HanToPdf.exe")
        if count <= 1:
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


def launch_apply_update(
    *,
    parent_pid: int,
    install_dir: Path,
    zip_path: Path,
    exe_path: Path,
) -> None:
    """설치 폴더와 분리된 exe 복사본으로 업데이트 적용 프로세스 시작."""
    import subprocess

    cleanup_legacy_update_artifacts()
    updater_exe = _prepare_detached_updater(install_dir)
    subprocess.Popen(
        [
            str(updater_exe),
            "--hantopdf-apply-update",
            str(parent_pid),
            str(install_dir),
            str(zip_path),
            str(exe_path),
        ],
        cwd=str(updater_exe.parent),
        close_fds=True,
        creationflags=_DETACHED_PROCESS | _CREATE_NO_WINDOW,
    )
    _log(f"업데이트 프로세스 시작: {updater_exe}")


def apply_update(
    *,
    parent_pid: int,
    install_dir: Path,
    zip_path: Path,
    exe_path: Path,
) -> None:
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

    import subprocess

    subprocess.Popen(
        [str(exe_path)],
        cwd=str(install_dir),
        close_fds=True,
    )
    _log(f"재시작: {exe_path}")

    if _is_detached_runtime():
        _schedule_dir_cleanup(Path(sys.executable).resolve().parent)


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
