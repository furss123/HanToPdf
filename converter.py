"""HWP/HWPX → PDF 변환 (한컴오피스 COM)"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable

import pythoncom
import win32com.client
from pypdf import PdfWriter

from hwp_automation import (
    HwpSecurityDialogWatcher,
    dismiss_hwp_security_dialog,
    ensure_hwp_security_module_registered,
    register_hwp_security_modules,
    wait_for_security_dialogs,
)
from winutil import hide_console_window, hide_hwp_windows_com, suppress_background_windows

HWP_EXTENSIONS = {".hwp", ".hwpx"}

_hwp_installed_cache: bool | None = None

PDF_SAVE_ATTRIBUTES = 16384

# 한글 PDF 저장 그림 품질 (PictureQuality)
# 0=자동, 1=매우낮음, 2=낮음, 3=보통, 4=높음, 5=매우높음(원본)
PDF_QUALITY_PRESETS = {
    "original": {
        "label": "원본화질",
        "picture_quality": 5,
        "desc": "원본과 동일, 용량이 가장 큽니다",
    },
    "high": {
        "label": "고화질",
        "picture_quality": 4,
        "desc": "보관용 문서에 적합합니다",
    },
    "medium": {
        "label": "중간",
        "picture_quality": 3,
        "desc": "화질과 용량의 균형",
    },
    "low": {
        "label": "저화질",
        "picture_quality": 2,
        "desc": "용량 절약, 화질이 낮습니다",
    },
}

PDF_QUALITY_ORDER = ("original", "high", "medium", "low")


class ConversionCancelled(Exception):
    """사용자가 변환을 중단함."""


def _check_cancelled(should_cancel: Callable[[], bool] | None) -> None:
    if should_cancel and should_cancel():
        raise ConversionCancelled()


def get_picture_quality(quality_key: str) -> int:
    preset = PDF_QUALITY_PRESETS.get(quality_key, PDF_QUALITY_PRESETS["high"])
    return preset["picture_quality"]


def build_pdf_save_argument(picture_quality: int) -> str:
    return (
        "PDFSaveOption:EmbedAllFonts=true,"
        f"PictureQuality={picture_quality},UsePassword=false"
    )


def is_hwp_available_fast() -> bool:
    """레지스트리 ProgID 확인 — 한글을 실행하지 않고 즉시 판별."""
    import winreg

    try:
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"HWPFrame.HwpObject")
        return True
    except OSError:
        return False


def _register_hwp_security_bypass(hwp) -> None:
    """보안 모듈 등록으로 접근 허용 창 자체가 뜨지 않도록 시도."""
    register_hwp_security_modules(hwp)


def _create_hwp():
    suppress_background_windows()
    try:
        hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
    except Exception as exc:
        raise RuntimeError(
            "한컴오피스(한글)가 설치되어 있지 않거나 실행할 수 없습니다."
        ) from exc
    _register_hwp_security_bypass(hwp)
    _reset_print_method(hwp)
    hide_hwp_windows_com(hwp)
    return hwp


def _reset_print_method(hwp) -> None:
    """문서에 저장된 모아찍기 등 인쇄 옵션으로 PDF 저장이 멈추는 문제 방지."""
    try:
        pset = hwp.HParameterSet.HPrint
        hwp.HAction.GetDefault("PrintToPDFEx", pset.HSet)
        pset.PrintMethod = 0
        pset.PrinterName = "Hancom PDF"
        pset.Collate = 1
        pset.PrintImage = 1
        pset.PrintDrawObj = 1
        pset.PrintFormObj = 1
        pset.PrintRevision = 1
    except Exception:
        pass


def _apply_pdf_quality(fos, picture_quality: int) -> str:
    fos.Format = "PDF"
    fos.Attributes = PDF_SAVE_ATTRIBUTES
    argument = build_pdf_save_argument(picture_quality)
    fos.Argument = argument
    applied = str(getattr(fos, "Argument", ""))
    if applied != argument:
        raise RuntimeError(f"PDF 화질 설정 적용 실패 (PictureQuality={picture_quality})")
    return argument


def _save_pdf(hwp, dst: Path, picture_quality: int) -> None:
    dst = dst.resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst_str = str(dst)
    pdf_option = build_pdf_save_argument(picture_quality)

    fos = hwp.HParameterSet.HFileOpenSave
    hwp.HAction.GetDefault("FileSaveAsPdf", fos.HSet)
    fos.filename = dst_str
    _apply_pdf_quality(fos, picture_quality)
    if hwp.HAction.Execute("FileSaveAsPdf", fos.HSet):
        if dst.exists() and dst.stat().st_size > 0:
            return

    if hwp.SaveAs(dst_str, "PDF", pdf_option):
        if dst.exists() and dst.stat().st_size > 0:
            return

    raise RuntimeError(f"PDF 저장 실패: {dst.name}")


def _open_document(hwp, src: Path) -> None:
    try:
        hwp.Clear(1)
    except Exception:
        pass

    path = str(src.resolve())
    try:
        ok = hwp.Open(path, "", "lock:false;forceopen:true;versionwarning:false;")
    except Exception as exc:
        raise RuntimeError(f"파일을 열 수 없습니다: {src.name}") from exc

    wait_for_security_dialogs(timeout=3.0)
    dismiss_hwp_security_dialog()
    hide_hwp_windows_com(hwp)

    if ok is False:
        raise RuntimeError(f"파일을 열 수 없습니다: {src.name}")


def convert_hwp_to_pdf(
    hwp,
    hwp_path: str | Path,
    pdf_path: str | Path,
    picture_quality: int | None = None,
    step_cb=None,
) -> Path:
    """이미 열린 HWP 세션으로 단일 파일 변환."""
    if picture_quality is None:
        picture_quality = get_picture_quality("high")
    src = Path(hwp_path).resolve()
    dst = Path(pdf_path).resolve()

    if not src.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {src}")
    if src.suffix.lower() not in HWP_EXTENSIONS:
        raise ValueError(f"지원하지 않는 형식입니다: {src.suffix}")

    if step_cb:
        step_cb(0.08, "문서 열기")
    _open_document(hwp, src)
    if step_cb:
        step_cb(0.45, "PDF 저장 중")
    _save_pdf(hwp, dst, picture_quality)
    hide_hwp_windows_com(hwp)
    if step_cb:
        step_cb(1.0, "완료")
    return dst


def _normalize_pdf_filename(name: str) -> str:
    name = name.strip()
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


def _separate_output_name(src: Path, output_filename: str | None, total: int) -> str:
    custom = (output_filename or "").strip()
    if not custom:
        return f"{src.stem}.pdf"
    if total == 1:
        return _normalize_pdf_filename(custom)
    base = Path(custom).stem
    return f"{base}_{src.stem}.pdf"


def merge_pdfs(pdf_paths: list[Path], output_path: Path) -> Path:
    writer = PdfWriter()
    for pdf in pdf_paths:
        writer.append(str(pdf), import_outline=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
    writer.close()
    return output_path


def convert_files(
    hwp_files: list[str | Path],
    output_dir: str | Path,
    mode: str = "separate",
    merged_name: str = "merged.pdf",
    output_filename: str | None = None,
    picture_quality: int | None = None,
    progress_cb=None,
    should_cancel: Callable[[], bool] | None = None,
) -> list[Path]:
    if picture_quality is None:
        picture_quality = get_picture_quality("high")
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    files = [Path(f).resolve() for f in hwp_files]
    total = len(files)
    results: list[Path] = []

    def report(percent: float, filename: str, action: str) -> None:
        if progress_cb:
            progress_cb(min(100.0, max(0.0, percent)), filename, action)

    pythoncom.CoInitialize()
    suppress_background_windows()
    ensure_hwp_security_module_registered()
    watcher = HwpSecurityDialogWatcher()
    watcher.start()
    hwp = None
    try:
        report(0, "", "한글 프로그램 준비 중")
        hwp = _create_hwp()
        report(3, "", "한글 준비 완료")

        if mode == "separate":
            for i, src in enumerate(files):
                _check_cancelled(should_cancel)
                chunk = 97.0 / total
                base = 3.0 + i * chunk

                def step_cb(step: float, action: str, _base=base, _chunk=chunk, _name=src.name):
                    report(_base + _chunk * step, _name, action)

                dst = output_dir / _separate_output_name(src, output_filename, total)
                results.append(convert_hwp_to_pdf(
                    hwp, src, dst, picture_quality, step_cb=step_cb,
                ))
            report(100, "", "변환 완료")
            return results

        temp_dir = Path(tempfile.mkdtemp(prefix="hantopdf_"))
        temp_pdfs: list[Path] = []
        try:
            for i, src in enumerate(files):
                _check_cancelled(should_cancel)
                chunk = 90.0 / total
                base = 3.0 + i * chunk

                def step_cb(step: float, action: str, _base=base, _chunk=chunk, _name=src.name):
                    report(_base + _chunk * step, _name, action)

                tmp = temp_dir / f"{i + 1:03d}.pdf"
                temp_pdfs.append(convert_hwp_to_pdf(
                    hwp, src, tmp, picture_quality, step_cb=step_cb,
                ))

            _check_cancelled(should_cancel)
            report(95, "", "PDF 병합 중")
            custom = (output_filename or "").strip()
            merged = _normalize_pdf_filename(custom) if custom else merged_name
            merged = output_dir / merged
            results.append(merge_pdfs(temp_pdfs, merged))
            report(100, "", "변환 완료")
            return results
        finally:
            for p in temp_pdfs:
                try:
                    p.unlink(missing_ok=True)
                except OSError:
                    pass
            try:
                temp_dir.rmdir()
            except OSError:
                pass
    finally:
        watcher.stop()
        if hwp is not None:
            try:
                hwp.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def check_hwp_installed(*, force: bool = False) -> bool:
    """한글 COM 연결 가능 여부 (결과 캐시)."""
    global _hwp_installed_cache
    if not force and _hwp_installed_cache is not None:
        return _hwp_installed_cache
    if not is_hwp_available_fast():
        _hwp_installed_cache = False
        return False

    pythoncom.CoInitialize()
    suppress_background_windows()
    try:
        hwp = _create_hwp()
        try:
            hwp.Quit()
        except Exception:
            pass
        _hwp_installed_cache = True
        return True
    except Exception:
        _hwp_installed_cache = False
        return False
    finally:
        pythoncom.CoUninitialize()
