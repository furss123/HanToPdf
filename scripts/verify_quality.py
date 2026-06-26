"""PictureQuality 적용 여부 확인 (한컴오피스 필요)"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pythoncom

from converter import (
    PDF_QUALITY_PRESETS,
    _apply_pdf_quality,
    _create_hwp,
    _open_document,
    build_pdf_save_argument,
    get_picture_quality,
)

QUALITY_LEVELS = [0, 2, 3, 4, 5]


def find_hwp(min_size: int = 50_000) -> Path | None:
    for root in (Path.home() / "Desktop", Path.home() / "Documents"):
        if not root.exists():
            continue
        for path in root.rglob("*.hwp"):
            if path.is_file() and path.stat().st_size >= min_size:
                return path
    return None


def convert_once(src: Path, picture_quality: int) -> tuple[bool, int, str]:
    pythoncom.CoInitialize()
    hwp = _create_hwp()
    try:
        out = Path(tempfile.gettempdir()) / f"hantopdf_q{picture_quality}.pdf"
        if out.exists():
            out.unlink()

        _open_document(hwp, src)
        fos = hwp.HParameterSet.HFileOpenSave
        hwp.HAction.GetDefault("FileSaveAsPdf", fos.HSet)
        fos.filename = str(out)
        _apply_pdf_quality(fos, picture_quality)
        argument = str(fos.Argument)
        ok = bool(hwp.HAction.Execute("FileSaveAsPdf", fos.HSet))
        size = out.stat().st_size if out.exists() else -1
        return ok, size, argument
    finally:
        try:
            hwp.Quit()
        except OSError:
            pass
        pythoncom.CoUninitialize()


def main() -> int:
    src = find_hwp()
    if src is None:
        print("테스트용 HWP 파일을 찾지 못했습니다.")
        return 1

    print(f"테스트 파일: {src.name}")
    print(f"HWP 크기: {src.stat().st_size:,} bytes\n")

    print("=== 프리셋 → PictureQuality 매핑 ===")
    for key, preset in PDF_QUALITY_PRESETS.items():
        pq = get_picture_quality(key)
        print(f"  {key:8} {preset['label']:6} -> PictureQuality={pq}")
        arg = build_pdf_save_argument(pq)
        if f"PictureQuality={pq}" not in arg:
            print(f"    오류: 인자 생성 실패 ({arg})")
            return 1

    print("\n=== 실제 변환 크기 비교 ===")
    results: dict[int, int] = {}
    for q in QUALITY_LEVELS:
        ok, size, argument = convert_once(src, q)
        results[q] = size
        print(f"  PictureQuality={q}: ok={ok}, pdf={size:,} bytes")
        if f"PictureQuality={q}" not in argument:
            print(f"    경고: HWP에 설정된 Argument 불일치: {argument}")

    spread = max(results.values()) - min(results.values())
    print(f"\n크기 차이: {spread:,} bytes")
    if spread <= 100:
        print("이 문서는 그림이 적어 화질 차이가 거의 없을 수 있습니다.")
    else:
        print("화질 설정에 따라 PDF 용량 차이가 확인되었습니다.")

    ordered = sorted(results.items(), key=lambda x: x[1])
    if ordered[0][0] != ordered[-1][0]:
        print(
            f"최소={ordered[0][0]}({ordered[0][1]:,}), "
            f"최대={ordered[-1][0]}({ordered[-1][1]:,})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
