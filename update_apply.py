"""HanToPdf 자동 업데이트 적용 (PowerShell 없이 동일 exe로 실행)."""

from __future__ import annotations

import ctypes
import shutil
import sys
import time
import zipfile
from pathlib import Path

_LOG_PATH = Path(__import__("os").environ.get("APPDATA", "")) / "HanToPdf" / "update.log"

_SYNCHRONIZE = 0x00100000
_WAIT_TIMEOUT_MS = 120_000
_COPY_RETRIES = 8
_COPY_RETRY_DELAY = 0.75


def _log(message: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


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
    time.sleep(1.5)


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

    _wait_for_process(parent_pid)

    if not zip_path.is_file():
        raise FileNotFoundError(f"ZIP 없음: {zip_path}")

    staging = install_dir.parent / f"_HanToPdf_update_{int(time.time())}"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(staging)
        src = _resolve_zip_root(staging)
        if not (src / "HanToPdf.exe").is_file():
            raise FileNotFoundError(f"ZIP 안에 HanToPdf.exe 없음: {src}")

        count = _copy_tree(src, install_dir)
        _log(f"파일 복사 완료: {count}개 -> {install_dir}")

        if not exe_path.is_file():
            raise FileNotFoundError(f"업데이트 후 exe 없음: {exe_path}")
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        try:
            zip_path.unlink()
        except OSError:
            _log(f"ZIP 삭제 실패: {zip_path}")

    import subprocess

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
    except Exception as exc:
        _log(f"업데이트 실패: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(run_apply_update_cli())
