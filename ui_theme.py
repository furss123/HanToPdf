"""HanToPdf 글래스모피즘 UI 테마 (Tkinter)"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# ── 그라데이션 ──
BG_TOP = "#0f1b3d"
BG_BOTTOM = "#1a3a6e"
BG = BG_TOP

# ── 글래스 패널 (rgba 흰색 10~15% on 진한 파랑 근사) ──
GLASS = "#2a3f6a"
GLASS_LIGHT = "#354b78"
GLASS_BORDER = "#5a6f9a"
GLASS_GROUP = "#243a62"

# ── 드롭존 ──
DROP_BG = "#223760"
DROP_HOVER = "#2d4878"
DROP_BORDER = "#8fa8d8"

# ── 강조 / 텍스트 ──
ACCENT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
ACCENT_DISABLED = "#2d4a7a"
TEXT = "#FFFFFF"
TEXT_SEC = "#BFD0F0"
SELECT_BG = "#3B82F6"

# ── 입력 ──
ENTRY_BG = "#2c426e"
ENTRY_BORDER = "#6a82b0"
ENTRY_FOCUS = ACCENT

FONT = "맑은 고딕"
FONT_TITLE = (FONT, 18, "bold")
FONT_SUBTITLE = (FONT, 10)
FONT_SECTION = (FONT, 9, "bold")
FONT_BODY = (FONT, 9)
FONT_SMALL = (FONT, 8)
FONT_BTN_PRIMARY = (FONT, 11, "bold")
FONT_BTN = (FONT, 9)
FONT_LINK = (FONT, 9, "underline")


def draw_gradient(canvas: tk.Canvas, width: int, height: int) -> None:
    canvas.delete("grad")
    if width < 2 or height < 2:
        return
    r1, g1, b1 = 0x0F, 0x1B, 0x3D
    r2, g2, b2 = 0x1A, 0x3A, 0x6E
    steps = max(32, min(128, height // 4))
    band = max(1, height // steps)
    for i in range(steps):
        t = i / max(steps - 1, 1)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        color = f"#{r:02x}{g:02x}{b:02x}"
        y0 = i * band
        y1 = height if i == steps - 1 else (i + 1) * band
        canvas.create_rectangle(0, y0, width, y1, fill=color, outline=color, tags="grad")


def attach_gradient(root: tk.Misc) -> tk.Canvas:
    canvas = tk.Canvas(root, highlightthickness=0, borderwidth=0, bg=BG_TOP)
    canvas.place(x=0, y=0, relwidth=1, relheight=1)

    def _redraw(_event=None):
        draw_gradient(canvas, root.winfo_width(), root.winfo_height())

    root.bind("<Configure>", _redraw, add="+")
    root.after_idle(_redraw)
    return canvas


def apply_ttk_theme(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "Glass.Horizontal.TProgressbar",
        troughcolor=GLASS,
        background=ACCENT,
        bordercolor=GLASS_BORDER,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        thickness=6,
    )
    style.configure(
        "Glass.Vertical.TScrollbar",
        troughcolor=GLASS,
        background=GLASS_BORDER,
        bordercolor=GLASS,
        arrowcolor=TEXT_SEC,
        gripcount=0,
    )
    style.map(
        "Glass.Vertical.TScrollbar",
        background=[("active", ACCENT), ("pressed", ACCENT_HOVER)],
    )
    return style


def glass_frame(parent: tk.Misc, **kwargs) -> tk.Frame:
    return tk.Frame(parent, bg=GLASS, highlightbackground=GLASS_BORDER,
                    highlightthickness=1, **kwargs)


def glass_group(parent: tk.Misc, title: str) -> tk.LabelFrame:
    return tk.LabelFrame(
        parent,
        text=f" {title} ",
        font=FONT_SECTION,
        bg=GLASS_GROUP,
        fg=TEXT,
        bd=0,
        relief="flat",
        highlightbackground=GLASS_BORDER,
        highlightthickness=1,
        padx=12,
        pady=8,
        labelanchor="nw",
    )


def glass_label(parent: tk.Misc, text: str = "", *, secondary: bool = False, **kwargs) -> tk.Label:
    defaults: dict = dict(bg=parent.cget("bg"), fg=TEXT_SEC if secondary else TEXT, font=FONT_BODY)
    if text:
        defaults["text"] = text
    defaults.update(kwargs)
    return tk.Label(parent, **defaults)


def glass_radio(parent: tk.Misc, text: str, variable: tk.Variable, value: str) -> tk.Radiobutton:
    return tk.Radiobutton(
        parent,
        text=text,
        variable=variable,
        value=value,
        font=FONT_BODY,
        bg=parent.cget("bg"),
        fg=TEXT,
        selectcolor=GLASS,
        activebackground=parent.cget("bg"),
        activeforeground=TEXT,
        anchor="w",
    )


def glass_button(
    parent: tk.Misc,
    text: str,
    command=None,
    *,
    primary: bool = False,
    accent: bool = False,
    small: bool = False,
) -> tk.Button:
    if primary:
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=FONT_BTN_PRIMARY,
            bg=ACCENT,
            fg=TEXT,
            activebackground=ACCENT_HOVER,
            activeforeground=TEXT,
            relief="flat",
            cursor="hand2",
            bd=0,
            padx=0,
            pady=12,
        )
    if accent:
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=(FONT, 9, "bold"),
            bg=ACCENT,
            fg=TEXT,
            activebackground=ACCENT_HOVER,
            activeforeground=TEXT,
            relief="flat",
            cursor="hand2",
            bd=0,
            padx=16,
            pady=6,
        )
    font = FONT_SMALL if small else FONT_BTN
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=font,
        bg=GLASS_LIGHT,
        fg=TEXT,
        activebackground=GLASS_BORDER,
        activeforeground=TEXT,
        relief="flat",
        highlightbackground=GLASS_BORDER,
        highlightthickness=1,
        cursor="hand2",
        bd=0,
        padx=12,
        pady=6 if not small else 4,
    )


def glass_entry(parent: tk.Misc, textvariable: tk.Variable | None = None) -> tk.Entry:
    entry = tk.Entry(
        parent,
        textvariable=textvariable,
        font=FONT_BODY,
        bg=ENTRY_BG,
        fg=TEXT,
        insertbackground=TEXT,
        relief="flat",
        highlightthickness=1,
        highlightbackground=ENTRY_BORDER,
        highlightcolor=ENTRY_FOCUS,
    )
    return entry


def glass_listbox(parent: tk.Misc, height: int = 4) -> tk.Listbox:
    return tk.Listbox(
        parent,
        height=height,
        font=FONT_BODY,
        bg=GLASS,
        fg=TEXT,
        selectbackground=SELECT_BG,
        selectforeground=TEXT,
        relief="flat",
        highlightthickness=1,
        highlightbackground=GLASS_BORDER,
        activestyle="none",
        bd=0,
    )


def set_tree_bg(widget: tk.Misc, color: str) -> None:
    try:
        widget.configure(bg=color)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        set_tree_bg(child, color)


class DropZone(tk.Frame):
    """점선 테두리 드롭존 (Canvas)"""

    def __init__(self, parent: tk.Misc, height: int = 150, on_click=None):
        super().__init__(parent, bg=BG)
        self._normal = DROP_BG
        self._hover = DROP_HOVER
        self._on_click = on_click

        self.canvas = tk.Canvas(
            self,
            height=height,
            bg=self._normal,
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
        )
        self.canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=self._normal)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="center")

        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        if on_click:
            self.canvas.bind("<Button-1>", lambda e: on_click())

    def _on_resize(self, event=None):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.canvas.coords(self._win, w // 2, h // 2)
        self.canvas.delete("border")
        self.canvas.create_rectangle(
            6, 6, w - 6, h - 6,
            outline=DROP_BORDER,
            dash=(8, 5),
            width=2,
            tags="border",
        )

    def _set_bg(self, color: str):
        self.canvas.configure(bg=color)
        set_tree_bg(self.inner, color)

    def _on_enter(self, _event=None):
        self._set_bg(self._hover)

    def _on_leave(self, _event=None):
        self._set_bg(self._normal)
