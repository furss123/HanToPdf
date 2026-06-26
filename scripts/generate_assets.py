"""사용자 제공 이미지로 앱 에셋 생성.

- icon.png / icon_2048.png / icon_4096.png : 투명 PNG 마스터
- icon.ico : Windows 멀티사이즈 아이콘
- banner_*.png : UI용 (아이콘에서 생성)
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CURSOR_ASSETS = Path(
    r"C:\Users\Namak1-4\.cursor\projects\c-Users-Namak1-4-Desktop-Work-HanToPdf\assets"
)
ICON_SRC_NAMES = (
    "icon_source.png",
    "c__Users_Namak1-4_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_"
    "hp-c2c515a4-49ae-4220-b0e9-9d3a00eaec64.png",
    "c__Users_Namak1-4_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_"
    "hp-d4179f37-cb86-477a-a506-929c854f508e.png",
)

ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256, 512)
ICO_BASE_SIZE = 256  # Pillow가 이 프레임에서 나머지 크기를 고품질 다운스케일
CANVAS_FILL = 0.97  # 캔버스의 96–98%


def _is_background_pixel(r: int, g: int, b: int, a: int) -> bool:
    """검정 배경·바닥 그림자 (가장자리 flood-fill 전용)."""
    if a < 8:
        return True
    if max(r, g, b) < 58:
        return True
    return False


def _flood_remove_background(im: Image.Image) -> Image.Image:
    rgba = im.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    visited = [[False] * w for _ in range(h)]
    q: deque[tuple[int, int]] = deque()

    def seed(x: int, y: int) -> None:
        if visited[y][x]:
            return
        r, g, b, a = px[x, y]
        if a == 0 or not _is_background_pixel(r, g, b, a):
            return
        visited[y][x] = True
        q.append((x, y))

    for x in range(w):
        seed(x, 0)
        seed(x, h - 1)
    for y in range(h):
        seed(0, y)
        seed(w - 1, y)

    while q:
        x, y = q.popleft()
        px[x, y] = (0, 0, 0, 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                r, g, b, a = px[nx, ny]
                if a > 0 and _is_background_pixel(r, g, b, a):
                    visited[ny][nx] = True
                    q.append((nx, ny))
    return rgba


def _normalize_transparency(im: Image.Image) -> Image.Image:
    rgba = im.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 16:
                px[x, y] = (0, 0, 0, 0)
    return rgba


def _fit_to_canvas(im: Image.Image, side: int, *, fill: float = CANVAS_FILL) -> Image.Image:
    """투명 정사각 캔버스에 아이콘을 fill 비율만큼 꽉 채움."""
    bbox = im.getbbox()
    if not bbox:
        return Image.new("RGBA", (side, side), (0, 0, 0, 0))
    cropped = im.crop(bbox)
    target = max(1, int(side * fill))
    cw, ch = cropped.size
    scale = target / max(cw, ch)
    new_w = max(1, round(cw * scale))
    new_h = max(1, round(ch * scale))
    resized = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    ox = (side - new_w) // 2
    oy = (side - new_h) // 2
    canvas.paste(resized, (ox, oy), resized)
    return _normalize_transparency(canvas)


def process_icon_source(src: Image.Image) -> Image.Image:
    """배경 제거 후 1024 캔버스에 맞춤."""
    cut = _flood_remove_background(src)
    return _fit_to_canvas(cut, 1024)


def _save_png(im: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="PNG", optimize=True)


def _resolve_icon_src() -> Path:
    for name in ICON_SRC_NAMES:
        for base in (ASSETS, CURSOR_ASSETS):
            candidate = base / name
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(f"아이콘 원본 없음: {ICON_SRC_NAMES[0]}")


def _save_icon_ico(im: Image.Image, path: Path) -> None:
    """고해상도 마스터에서 256px 기준 ICO 생성 (멀티 사이즈, 투명 유지)."""
    master = _normalize_transparency(im.convert("RGBA"))
    side = max(master.size)
    if side > ICO_BASE_SIZE:
        base = master.resize((ICO_BASE_SIZE, ICO_BASE_SIZE), Image.Resampling.LANCZOS)
    elif side < ICO_BASE_SIZE:
        base = master.resize((ICO_BASE_SIZE, ICO_BASE_SIZE), Image.Resampling.LANCZOS)
    else:
        base = master
    path.parent.mkdir(parents=True, exist_ok=True)
    base.save(
        path,
        format="ICO",
        sizes=[(s, s) for s in ICON_SIZES],
    )


def _resize_by_height(im: Image.Image, height: int) -> Image.Image:
    w, h = im.size
    new_w = max(1, round(w * height / h))
    return im.resize((new_w, height), Image.Resampling.LANCZOS)


def generate_icon(src: Path, out_dir: Path) -> Image.Image:
    master_1024 = process_icon_source(Image.open(src))
    _save_png(master_1024, out_dir / "icon.png")
    _save_png(
        master_1024.resize((2048, 2048), Image.Resampling.LANCZOS),
        out_dir / "icon_2048.png",
    )
    _save_png(
        master_1024.resize((4096, 4096), Image.Resampling.LANCZOS),
        out_dir / "icon_4096.png",
    )
    _save_icon_ico(master_1024, out_dir / "icon.ico")
    return master_1024


def generate_banner_from_icon(im: Image.Image, out_dir: Path) -> None:
    bbox = im.getbbox()
    banner_src = im.crop(bbox) if bbox else im
    _save_png(banner_src, out_dir / "banner.png")
    for height, name in ((44, "banner_h44.png"), (72, "banner_h72.png")):
        _save_png(_resize_by_height(banner_src, height), out_dir / name)


def main() -> None:
    icon_src = _resolve_icon_src()
    ASSETS.mkdir(parents=True, exist_ok=True)
    if icon_src.parent != ASSETS or icon_src.name != "icon_source.png":
        shutil_copy = ASSETS / "icon_source.png"
        Image.open(icon_src).save(shutil_copy, format="PNG")
        icon_src = shutil_copy

    master = generate_icon(icon_src, ASSETS)
    generate_banner_from_icon(master, ASSETS)

    for old in ("icon_48.png", "icon_96.png", "banner_h110.png", "_preview.png"):
        p = ASSETS / old
        if p.exists():
            p.unlink()

    print("생성 완료:", ASSETS)
    for p in sorted(ASSETS.glob("*")):
        if p.suffix.lower() in {".png", ".ico"}:
            if p.suffix.lower() == ".ico":
                print(f"  {p.name}: ICO {ICON_SIZES}")
            else:
                im = Image.open(p)
                print(f"  {p.name}: {im.size[0]}x{im.size[1]}")


if __name__ == "__main__":
    main()
