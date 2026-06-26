"""사용자 제공 이미지로 앱 에셋 생성.

- icon.ico / icon.png : 정사각 앱 아이콘 (exe·바로가기·창 아이콘)
- banner_*.png        : 가로 배너 (UI, 비율 유지 리사이즈)
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CURSOR_ASSETS = Path(
    r"C:\Users\Namak1-4\.cursor\projects\c-Users-Namak1-4-Desktop-Work-HanToPdf\assets"
)
ICON_SRC = CURSOR_ASSETS / (
    "c__Users_Namak1-4_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_"
    "11-13480776-98cd-44e2-81ce-7975f00fd0a1.png"
)
BANNER_SRC = CURSOR_ASSETS / (
    "c__Users_Namak1-4_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images_"
    "image-1d57a9b5-6dbc-4ceb-b604-d324efe40ef2.png"
)

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _remove_near_black(im: Image.Image, threshold: int = 35) -> Image.Image:
    rgba = im.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r <= threshold and g <= threshold and b <= threshold:
                px[x, y] = (r, g, b, 0)
    return rgba


def _is_icon_background(r: int, g: int, b: int) -> bool:
    """실행 아이콘의 검정·연한 파란 배경."""
    if r <= 60 and g <= 60 and b <= 60:
        return True
    if r >= 165 and g >= 165 and b >= 190 and max(r, g, b) - min(r, g, b) < 55:
        return True
    return False


def _apply_round_clip(im: Image.Image, radius_ratio: float = 0.19) -> Image.Image:
    """정사각 아이콘 바깥 모서리(둥근 사각 밖)를 투명 처리."""
    rgba = im.convert("RGBA")
    w, h = rgba.size
    radius = max(8, int(min(w, h) * radius_ratio))
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    r, g, b, a = rgba.split()
    clipped_a = ImageChops.multiply(a, mask)
    out = Image.merge("RGBA", (r, g, b, clipped_a))
    return out


def _normalize_transparency(im: Image.Image) -> Image.Image:
    """투명 픽셀 RGB를 0으로 정리 (Windows 아이콘 검은 테두리 방지)."""
    rgba = im.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 16:
                px[x, y] = (0, 0, 0, 0)
            elif a < 255:
                # 반투명 가장자리도 배경색 혼입 최소화
                px[x, y] = (r, g, b, a)
    return rgba


def _remove_icon_background(im: Image.Image) -> Image.Image:
    """테두리에서 flood-fill로 배경을 투명 처리."""
    from collections import deque

    rgba = im.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    visited = [[False] * w for _ in range(h)]
    q: deque[tuple[int, int]] = deque()

    def try_seed(x: int, y: int) -> None:
        if visited[x][y]:
            return
        r, g, b, a = px[x, y]
        if a == 0 or not _is_icon_background(r, g, b):
            return
        visited[x][y] = True
        q.append((x, y))

    for x in range(w):
        try_seed(x, 0)
        try_seed(x, h - 1)
    for y in range(h):
        try_seed(0, y)
        try_seed(w - 1, y)

    while q:
        x, y = q.popleft()
        px[x, y] = (0, 0, 0, 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not visited[nx][ny]:
                nr, ng, nb, na = px[nx, ny]
                if na > 0 and _is_icon_background(nr, ng, nb):
                    visited[nx][ny] = True
                    q.append((nx, ny))

    rgba = _apply_round_clip(rgba)
    rgba = _normalize_transparency(rgba)

    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)
        side = max(rgba.size)
        square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        ox = (side - rgba.width) // 2
        oy = (side - rgba.height) // 2
        square.paste(rgba, (ox, oy), rgba)
        rgba = _apply_round_clip(square)
        rgba = _normalize_transparency(rgba)
    return rgba


def _save_icon_ico(im: Image.Image, path: Path) -> None:
    """크기별로 리사이즈한 RGBA 프레임으로 ICO 저장."""
    master = _normalize_transparency(im.convert("RGBA"))
    frames = [
        _normalize_transparency(master.resize((size, size), Image.Resampling.LANCZOS))
        for size in ICON_SIZES
    ]
    frames[0].save(
        path,
        format="ICO",
        sizes=[(s, s) for s in ICON_SIZES],
        append_images=frames[1:],
    )


def _resize_by_height(im: Image.Image, height: int) -> Image.Image:
    w, h = im.size
    new_w = max(1, round(w * height / h))
    return im.resize((new_w, height), Image.Resampling.LANCZOS)


def _save_png(im: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="PNG", optimize=True)


def generate_icon(src: Path, out_dir: Path) -> None:
    im = _remove_icon_background(Image.open(src))
    _save_png(im, out_dir / "icon.png")
    _save_icon_ico(im, out_dir / "icon.ico")


def generate_banner(src: Path, out_dir: Path) -> None:
    im = _remove_near_black(Image.open(src))
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)

    _save_png(im, out_dir / "banner.png")
    for height, name in ((44, "banner_h44.png"), (72, "banner_h72.png")):
        _save_png(_resize_by_height(im, height), out_dir / name)


def main() -> None:
    if not ICON_SRC.exists():
        raise SystemExit(f"아이콘 원본 없음: {ICON_SRC}")
    if not BANNER_SRC.exists():
        raise SystemExit(f"배너 원본 없음: {BANNER_SRC}")

    ASSETS.mkdir(parents=True, exist_ok=True)
    generate_icon(ICON_SRC, ASSETS)
    generate_banner(BANNER_SRC, ASSETS)

    for old in ("icon_48.png", "icon_96.png", "banner_h110.png"):
        p = ASSETS / old
        if p.exists():
            p.unlink()

    print("생성 완료:", ASSETS)
    for p in sorted(ASSETS.glob("*")):
        im = Image.open(p)
        print(f"  {p.name}: {im.size[0]}x{im.size[1]}")


if __name__ == "__main__":
    main()
