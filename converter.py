"""HWP/HWPX → PDF 변환 (한컴오피스 COM)"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pythoncom
import win32com.client
from pypdf import PdfWriter

from winutil import hide_console_window

HWP_EXTENSIONS = {".hwp", ".hwpx"}

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


def get_picture_quality(quality_key: str) -> int:
    preset = PDF_QUALITY_PRESETS.get(quality_key, PDF_QUALITY_PRESETS["high"])
    return preset["picture_quality"]


def build_pdf_save_argument(picture_quality: int) -> str:
    return (
        "PDFSaveOption:EmbedAllFonts=true,"
        f"PictureQuality={picture_quality},UsePassword=false"
    )


def _create_hwp():
    hide_console_window()
    hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
    try:
        hwp.RegisterModule("FilePathCheckDLL", "SecurityModule")
    except Exception:
        pass
    try:
        hwp.SetMessageBoxMode(0x00214411)
    except Exception:
        pass
    try:
        hwp.XHwpWindows.Item(0).Visible = False
    except Exception:
        pass
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

    if ok is False:
        raise RuntimeError(f"파일을 열 수 없습니다: {src.name}")


def convert_hwp_to_pdf(
    hwp,
    hwp_path: str | Path,
    pdf_path: str | Path,
    picture_quality: int | None = None,
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

    _open_document(hwp, src)
    _reset_print_method(hwp)
    _save_pdf(hwp, dst, picture_quality)
    return dst


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
    picture_quality: int | None = None,
    progress_cb=None,
) -> list[Path]:
    if picture_quality is None:
        picture_quality = get_picture_quality("high")
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    files = [Path(f).resolve() for f in hwp_files]
    total = len(files)
    results: list[Path] = []

    pythoncom.CoInitialize()
    hide_console_window()
    hwp = None
    try:
        hwp = _create_hwp()

        if mode == "separate":
            for i, src in enumerate(files, 1):
                if progress_cb:
                    progress_cb(i - 1, total, f"변환 중 ({i}/{total}): {src.name}")
                dst = output_dir / f"{src.stem}.pdf"
                results.append(convert_hwp_to_pdf(hwp, src, dst, picture_quality))
                if progress_cb:
                    progress_cb(i, total, f"완료 ({i}/{total}): {src.name}")
            return results

        temp_dir = Path(tempfile.mkdtemp(prefix="hantopdf_"))
        temp_pdfs: list[Path] = []
        try:
            for i, src in enumerate(files, 1):
                if progress_cb:
                    progress_cb(i - 1, total, f"변환 중 ({i}/{total}): {src.name}")
                tmp = temp_dir / f"{i:03d}.pdf"
                temp_pdfs.append(convert_hwp_to_pdf(hwp, src, tmp, picture_quality))
                if progress_cb:
                    progress_cb(i, total, f"완료 ({i}/{total}): {src.name}")

            if progress_cb:
                progress_cb(total, total, "PDF 병합 중...")
            merged = output_dir / merged_name
            results.append(merge_pdfs(temp_pdfs, merged))
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
        if hwp is not None:
            try:
                hwp.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def check_hwp_installed() -> bool:
    pythoncom.CoInitialize()
    hide_console_window()
    try:
        hwp = _create_hwp()
        try:
            hwp.Quit()
        except Exception:
            pass
        return True
    except Exception:
        return False
    finally:
        pythoncom.CoUninitialize()
