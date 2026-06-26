"""HanToPdf — Windows 11 Fluent Design UI 테마 (Tkinter)"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# ── Fluent palette ──
BG = "#F6F8FB"
CARD = "#FFFFFF"
CARD_BORDER = "#E5E7EB"
CARD_INNER = "#FFFFFF"
SHADOW = "#E8ECF1"

DROP_BG = "#FFFFFF"
DROP_HOVER = "#EFF6FF"
DROP_BORDER = "#CBD5E1"
DROP_BORDER_HOVER = "#2563EB"

ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
ACCENT_PRESSED = "#1E40AF"
ACCENT_DISABLED = "#93C5FD"
SUCCESS = "#16A34A"
WARNING = "#F59E0B"
STOP_BG = "#EF4444"
STOP_HOVER = "#DC2626"

TEXT = "#111827"
TEXT_SEC = "#6B7280"
TEXT_MUTED = "#9CA3AF"
SELECT_BG = "#EFF6FF"
SELECT_FG = TEXT

ENTRY_BG = "#FFFFFF"
ENTRY_BORDER = "#E5E7EB"
ENTRY_FOCUS = "#2563EB"
BTN_SEC_BG = "#FFFFFF"
BTN_SEC_BORDER = "#E5E7EB"
BTN_SEC_HOVER = "#F3F4F6"

RADIUS = 12
RADIUS_LG = 16
RADIUS_SM = 10
RADIUS_BTN = 10

PAD_OUTER = 20
PAD_SECTION = 16
PAD_CONTROL = 10
PAD_INNER = 14
SPACING_LABEL = 6
ENTRY_IPADY = 8
ROW_HEIGHT = 26

FONT_FAMILY = "Noto Sans KR"
FONT_TITLE = (FONT_FAMILY, 22, "bold")
FONT_SECTION = (FONT_FAMILY, 13, "bold")
FONT_LABEL = (FONT_FAMILY, 12)
FONT_BODY = (FONT_FAMILY, 12)
FONT_DESC = (FONT_FAMILY, 11)
FONT_SMALL = (FONT_FAMILY, 11)
FONT_HINT = (FONT_FAMILY, 11)
FONT_BTN_PRIMARY = (FONT_FAMILY, 13, "bold")
FONT_BTN = (FONT_FAMILY, 12)
FONT_LINK = (FONT_FAMILY, 12)
FONT_COPYRIGHT = (FONT_FAMILY, 10)

_font_refs: list[tkfont.Font] = []
FONT_DROP_TITLE = (FONT_FAMILY, 13, "bold")
FONT_DROP_HINT = (FONT_FAMILY, 11)


def _apply_font_family(family: str) -> None:
    global FONT_FAMILY, FONT_TITLE, FONT_SECTION, FONT_LABEL, FONT_BODY
    global FONT_DESC, FONT_SMALL, FONT_HINT, FONT_BTN_PRIMARY, FONT_BTN, FONT_LINK, FONT_COPYRIGHT

    FONT_FAMILY = family
    FONT_TITLE = (family, 22, "bold")
    FONT_SECTION = (family, 13, "bold")
    FONT_LABEL = (family, 12)
    FONT_BODY = (family, 12)
    FONT_DESC = (family, 11)
    FONT_SMALL = (family, 11)
    FONT_HINT = (family, 11)
    FONT_BTN_PRIMARY = (family, 13, "bold")
    FONT_BTN = (family, 12)
    FONT_LINK = (family, 12)
    FONT_COPYRIGHT = (family, 10)
    _sync_drop_fonts()


def configure_fonts(root: tk.Misc) -> None:
    """Noto Sans KR 로드 후 전체 UI에 적용."""
    from app_assets import install_app_fonts

    install_app_fonts()
    root.update_idletasks()
    families = set(tkfont.families(root))
    for candidate in ("Noto Sans KR", "Noto Sans CJK KR"):
        if candidate in families:
            _apply_font_family(candidate)
            return


def _sync_drop_fonts() -> None:
    global FONT_DROP_TITLE, FONT_DROP_HINT
    FONT_DROP_TITLE = (FONT_FAMILY, 13, "bold")
    FONT_DROP_HINT = (FONT_FAMILY, 11)


ANIM_MS = 150


def _bind_ghost_hover(btn: tk.Button, normal: str, hover: str) -> None:
    btn.bind("<Enter>", lambda _e: btn.configure(bg=hover))
    btn.bind("<Leave>", lambda _e: btn.configure(bg=normal))


def _fill_round_rect(
    canvas: tk.Canvas,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    radius: int,
    fill: str,
    *,
    outline: str | None = None,
) -> None:
    r = radius
    o = outline if outline is not None else fill
    canvas.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r, start=90, extent=90, fill=fill, outline=o)
    canvas.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r, start=0, extent=90, fill=fill, outline=o)
    canvas.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2, start=270, extent=90, fill=fill, outline=o)
    canvas.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2, start=180, extent=90, fill=fill, outline=o)
    canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline=fill)
    canvas.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline=fill)


def apply_ttk_theme(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "App.Horizontal.TProgressbar",
        troughcolor="#E5E7EB",
        background=ACCENT,
        bordercolor=CARD_BORDER,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        thickness=6,
    )
    style.configure(
        "App.Vertical.TScrollbar",
        troughcolor=BG,
        background="#D1D5DB",
        bordercolor=BG,
        arrowcolor=TEXT_SEC,
        gripcount=0,
        width=10,
    )
    style.map(
        "App.Vertical.TScrollbar",
        background=[("active", "#9CA3AF"), ("pressed", ACCENT)],
    )
    style.configure(
        "App.Horizontal.TScrollbar",
        troughcolor=BG,
        background="#D1D5DB",
        bordercolor=BG,
        arrowcolor=TEXT_SEC,
        gripcount=0,
        width=10,
    )
    style.map(
        "App.Horizontal.TScrollbar",
        background=[("active", "#9CA3AF"), ("pressed", ACCENT)],
    )
    style.configure(
        "File.Treeview",
        background=CARD_INNER,
        fieldbackground=CARD_INNER,
        foreground=TEXT,
        rowheight=ROW_HEIGHT,
        borderwidth=0,
        relief="flat",
        padding=(8, 4),
        font=FONT_BODY,
    )
    style.map(
        "File.Treeview",
        background=[("selected", SELECT_BG)],
        foreground=[("selected", SELECT_FG)],
    )
    style.configure(
        "File.Treeview.Heading",
        background=CARD,
        foreground=CARD,
        relief="flat",
        borderwidth=0,
        font=(FONT_FAMILY, 1),
    )
    return style


class SectionCard(tk.Frame):
    """Fluent 카드 — 위젯은 `.body`에 배치."""

    def __init__(self, parent: tk.Misc, **kwargs):
        super().__init__(parent, bg=BG)
        tk.Frame(self, bg=SHADOW, height=2).pack(side="bottom", fill="x")
        self.body = tk.Frame(
            self,
            bg=CARD,
            highlightbackground=CARD_BORDER,
            highlightthickness=1,
            **kwargs,
        )
        self.body.pack(fill="both", expand=True)


def section_card(parent: tk.Misc, **kwargs) -> SectionCard:
    return SectionCard(parent, **kwargs)


def section_label(parent: tk.Misc, text: str) -> tk.Label:
    return tk.Label(
        parent, text=text, font=FONT_SECTION, bg=parent.cget("bg"), fg=TEXT, anchor="w",
    )


def card_row(parent: tk.Misc) -> tk.Frame:
    """카드 내부 표준 행 — 동일 패딩."""
    row = tk.Frame(parent, bg=CARD)
    row.pack(fill="x", padx=PAD_INNER, pady=PAD_INNER)
    return row


def app_label(
    parent: tk.Misc,
    text: str = "",
    *,
    secondary: bool = False,
    hint: bool = False,
    **kwargs,
) -> tk.Label:
    if hint:
        fg, font = TEXT_MUTED, FONT_HINT
    elif secondary:
        fg, font = TEXT_SEC, FONT_DESC
    else:
        fg, font = TEXT, FONT_BODY
    defaults: dict = dict(bg=parent.cget("bg"), fg=fg, font=font)
    if text:
        defaults["text"] = text
    defaults.update(kwargs)
    return tk.Label(parent, **defaults)


def app_radio(parent: tk.Misc, text: str, variable: tk.Variable, value: str) -> tk.Radiobutton:
    return tk.Radiobutton(
        parent,
        text=text,
        variable=variable,
        value=value,
        font=FONT_LABEL,
        bg=parent.cget("bg"),
        fg=TEXT,
        selectcolor=ENTRY_BG,
        activebackground=parent.cget("bg"),
        activeforeground=TEXT,
        highlightthickness=0,
        borderwidth=0,
        anchor="w",
        padx=4,
        pady=6,
    )


def app_button(
    parent: tk.Misc,
    text: str,
    command=None,
    *,
    primary: bool = False,
    accent: bool = False,
    small: bool = False,
    outlined: bool = False,
) -> tk.Button:
    if primary:
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=FONT_BTN_PRIMARY,
            bg=ACCENT,
            fg="#FFFFFF",
            activebackground=ACCENT_HOVER,
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            bd=0,
            padx=0,
            pady=14,
        )
    if accent:
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=FONT_BTN_PRIMARY,
            bg=ACCENT,
            fg="#FFFFFF",
            activebackground=ACCENT_HOVER,
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            bd=0,
            padx=20,
            pady=10,
        )
    py = 7 if small else 8
    px = 16 if small else 16
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        font=FONT_BTN,
        bg=BTN_SEC_BG,
        fg=TEXT,
        activebackground=BTN_SEC_HOVER,
        activeforeground=TEXT,
        relief="flat",
        highlightbackground=BTN_SEC_BORDER,
        highlightthickness=1,
        cursor="hand2",
        bd=0,
        padx=px,
        pady=py,
    )
    _bind_ghost_hover(btn, BTN_SEC_BG, BTN_SEC_HOVER)
    return btn


def app_entry(parent: tk.Misc, textvariable: tk.Variable | None = None) -> tk.Entry:
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

    def _on_focus_in(_event=None) -> None:
        entry.configure(highlightbackground=ENTRY_FOCUS, highlightthickness=2)

    def _on_focus_out(_event=None) -> None:
        entry.configure(highlightbackground=ENTRY_BORDER, highlightthickness=1)

    entry.bind("<FocusIn>", _on_focus_in)
    entry.bind("<FocusOut>", _on_focus_out)
    return entry


def app_file_list(parent: tk.Misc, height: int = 13) -> ttk.Treeview:
    """파일명 목록 (체크 + 이름, 가로 스크롤 지원)."""
    tree = ttk.Treeview(
        parent,
        columns=("check", "name"),
        show="headings",
        height=height,
        style="File.Treeview",
        selectmode="extended",
    )
    tree.heading("check", text="")
    tree.column("check", width=36, anchor="center", stretch=False, minwidth=36)
    tree.heading("name", text="")
    tree.column("name", width=320, anchor="w", stretch=False, minwidth=80)
    return tree


def app_listbox(parent: tk.Misc, height: int = 10) -> tk.Listbox:
    return tk.Listbox(
        parent,
        height=height,
        font=FONT_BODY,
        bg=CARD_INNER,
        fg=TEXT,
        selectbackground=SELECT_BG,
        selectforeground=SELECT_FG,
        relief="flat",
        highlightthickness=1,
        highlightbackground=ENTRY_BORDER,
        highlightcolor=ENTRY_FOCUS,
        activestyle="none",
        bd=0,
    )


def link_label(parent: tk.Misc, text: str, command) -> tk.Label:
    lbl = tk.Label(
        parent,
        text=text,
        font=FONT_LINK,
        bg=parent.cget("bg"),
        fg=ACCENT,
        cursor="hand2",
    )
    lbl.bind("<Button-1>", lambda _e: command())
    lbl.bind("<Enter>", lambda _e: lbl.configure(fg=ACCENT_HOVER))
    lbl.bind("<Leave>", lambda _e: lbl.configure(fg=ACCENT))
    return lbl


def set_tree_bg(widget: tk.Misc, color: str) -> None:
    try:
        widget.configure(bg=color)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        set_tree_bg(child, color)


def _draw_rounded_outline(
    canvas: tk.Canvas,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    radius: int,
    color: str,
    *,
    width: float = 2.0,
    dash: tuple[int, ...] = (10, 6),
) -> None:
    """둥근 점선 — arc+line 중복 없이 smooth polygon 1개로만 그림."""
    r = min(radius, max(1, (x2 - x1) // 2 - 1), max(1, (y2 - y1) // 2 - 1))
    points = [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]
    canvas.create_polygon(
        points,
        smooth=True,
        splinesteps=48,
        outline=color,
        fill="",
        width=width,
        dash=dash,
        tags="border",
    )


class ListEmptyOverlay(tk.Frame):
    """변환 목록 빈 상태 — 클릭·드래그로 파일 추가."""

    def __init__(self, parent: tk.Misc, on_click=None):
        super().__init__(parent, bg=CARD, cursor="hand2")
        self._on_click = on_click
        self._normal = CARD
        self._hover = DROP_HOVER
        self._radius = RADIUS_LG

        self.canvas = tk.Canvas(
            self, bg=self._normal, highlightthickness=0, borderwidth=0, cursor="hand2",
        )
        self.canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=self._normal)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="center")

        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        if on_click:
            self.canvas.bind("<Button-1>", lambda _e: on_click())

    def _on_resize(self, _event=None) -> None:
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 20 or h < 20:
            return
        pad = 10
        inner_w = max(80, w - pad * 2 - 4)
        self.canvas.itemconfigure(self._win, width=inner_w)
        self.canvas.coords(self._win, w // 2, h // 2)
        self.canvas.delete("border")
        _draw_rounded_outline(
            self.canvas, pad, pad, w - pad, h - pad,
            self._radius, DROP_BORDER, width=2.0, dash=(10, 6),
        )

    def _set_bg(self, color: str) -> None:
        self.canvas.configure(bg=color)
        set_tree_bg(self.inner, color)

    def _on_enter(self, _event=None) -> None:
        self._set_bg(self._hover)
        self.canvas.delete("border")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        pad = 10
        _draw_rounded_outline(
            self.canvas, pad, pad, w - pad, h - pad,
            self._radius, DROP_BORDER_HOVER, width=2.0, dash=(10, 6),
        )

    def _on_leave(self, _event=None) -> None:
        self._set_bg(self._normal)
        self._on_resize()

    def bind_inner_clicks(self) -> None:
        if not self._on_click:
            return
        self._bind_clicks_deep(self.inner)

    def _bind_clicks_deep(self, widget: tk.Misc) -> None:
        try:
            widget.bind("<Button-1>", self._handle_click)
            widget.configure(cursor="hand2")
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._bind_clicks_deep(child)

    def _handle_click(self, _event=None) -> None:
        if self._on_click:
            self._on_click()


class DropZone(tk.Frame):
    """Fluent 드래그 앤 드롭 영역."""

    _PAD = 12

    def __init__(self, parent: tk.Misc, height: int = 168, on_click=None):
        super().__init__(parent, bg=BG)
        self._normal = DROP_BG
        self._hover = DROP_HOVER
        self._on_click = on_click
        self._radius = RADIUS_LG
        self._border_color = DROP_BORDER
        self._base_height = height

        self.canvas = tk.Canvas(
            self,
            height=height,
            bg=self._normal,
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
        )
        self.canvas.pack(fill="x")
        self.inner = tk.Frame(self.canvas, bg=self._normal)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="center")

        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        if on_click:
            self.canvas.bind("<Button-1>", lambda _e: on_click())

    def refresh_layout(self) -> None:
        """내용 높이에 맞춰 캔버스·테두리 갱신."""
        self.inner.update_idletasks()
        content_h = self.inner.winfo_reqheight()
        h = max(self._base_height, content_h + self._PAD * 2 + 8)
        if self.canvas.winfo_height() != h:
            self.canvas.configure(height=h)
        self._redraw_border()

    def _redraw_border(self) -> None:
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 40 or h < 40:
            return
        pad = self._PAD
        inner_w = max(80, w - pad * 2 - 4)
        self.canvas.itemconfigure(self._win, width=inner_w)
        self.canvas.coords(self._win, w // 2, h // 2)
        self.canvas.delete("border")
        _draw_rounded_outline(
            self.canvas,
            pad, pad, w - pad, h - pad,
            self._radius,
            self._border_color,
            width=2.0,
            dash=(10, 6),
        )

    def _on_resize(self, _event=None):
        self._redraw_border()

    def _set_bg(self, color: str) -> None:
        self.canvas.configure(bg=color)
        set_tree_bg(self.inner, color)

    def _on_enter(self, _event=None):
        self._hovering = True
        self._border_color = DROP_BORDER_HOVER
        self._set_bg(self._hover)
        self._redraw_border()

    def _on_leave(self, _event=None):
        self._hovering = False
        self._border_color = DROP_BORDER
        self._set_bg(self._normal)
        self._redraw_border()

    def bind_inner_clicks(self) -> None:
        if not self._on_click:
            return
        self._bind_clicks_deep(self.inner)

    def _bind_clicks_deep(self, widget: tk.Misc) -> None:
        try:
            widget.bind("<Button-1>", self._handle_click)
            widget.configure(cursor="hand2")
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._bind_clicks_deep(child)

    def _handle_click(self, _event=None) -> None:
        if self._on_click:
            self._on_click()


class PrimaryConvertButton(tk.Canvas):
    """Fluent 메인 CTA 버튼."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        text: str = "PDF 변환",
        command=None,
        height: int = 48,
        radius: int = RADIUS,
    ):
        super().__init__(
            parent,
            height=height + 4,
            bg=BG,
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
        )
        self._text = text
        self._command = command
        self._height = height
        self._radius = radius
        self._busy = False
        self._hover = False
        self._pressed = False
        self._font = tkfont.Font(
            family=FONT_BTN_PRIMARY[0],
            size=FONT_BTN_PRIMARY[1],
            weight="bold",
        )
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def _fill_color(self) -> str:
        if self._busy:
            return ACCENT_DISABLED
        if self._pressed:
            return ACCENT_PRESSED
        if self._hover:
            return ACCENT_HOVER
        return ACCENT

    def _draw(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 120)
        h = self._height
        r = self._radius
        color = self._fill_color()
        self.create_rectangle(0, 0, w, h + 4, fill=BG, outline=BG)
        _fill_round_rect(self, 2, 3, w - 2, h + 1, r, SHADOW)
        _fill_round_rect(self, 0, 0, w, h, r, color)
        self.create_text(w // 2, h // 2, text=self._text, fill="#FFFFFF", font=self._font)

    def set_busy(self, busy: bool, text: str | None = None) -> None:
        self._busy = busy
        if text is not None:
            self._text = text
        self.configure(cursor="arrow" if busy else "hand2")
        self._draw()

    def _on_enter(self, _event=None) -> None:
        if not self._busy:
            self._hover = True
            self._draw()

    def _on_leave(self, _event=None) -> None:
        self._hover = False
        self._pressed = False
        self._draw()

    def _on_press(self, _event=None) -> None:
        if not self._busy:
            self._pressed = True
            self._draw()

    def _on_release(self, _event=None) -> None:
        was_pressed = self._pressed
        self._pressed = False
        self._draw()
        if was_pressed and not self._busy and self._command:
            self._command()


class ScrollableFrame(tk.Frame):
    """내용이 뷰포트보다 길 때만 우측 세로 스크롤을 표시."""

    def __init__(self, parent: tk.Misc, **kwargs):
        kwargs.setdefault("bg", BG)
        super().__init__(parent, **kwargs)

        self._canvas = tk.Canvas(self, bg=BG, highlightthickness=0, borderwidth=0)
        self._vsb = ttk.Scrollbar(
            self, orient="vertical", command=self._canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        self.inner = tk.Frame(self._canvas, bg=BG)
        self._window = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self._canvas.configure(yscrollcommand=self._on_yscroll_command)
        self._canvas.pack(side="left", fill="both", expand=True)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._refresh_busy = False
        self._vsb_visible: bool | None = None

    def _on_yscroll_command(self, first: str, last: str) -> None:
        if self._needs_scrollbar():
            if not self._vsb.winfo_ismapped():
                self._vsb.pack(side="right", fill="y")
            self._vsb.set(first, last)
        elif self._vsb.winfo_ismapped():
            self._vsb.pack_forget()
            self._canvas.yview_moveto(0)

    def _needs_scrollbar(self) -> bool:
        view_h = self._canvas.winfo_height()
        content_h = self.inner.winfo_reqheight()
        return view_h > 0 and content_h > view_h + 1

    def _on_inner_configure(self, _event=None) -> None:
        bbox = self._canvas.bbox("all")
        if bbox:
            self._canvas.configure(scrollregion=bbox)
        if not self._refresh_busy:
            self.after_idle(self.refresh)

    def _on_canvas_configure(self, event) -> None:
        self._canvas.itemconfigure(self._window, width=event.width)
        if not self._refresh_busy:
            self.after_idle(self.refresh)

    def refresh(self) -> None:
        if self._refresh_busy:
            return
        self._refresh_busy = True
        try:
            bbox = self._canvas.bbox("all")
            if bbox:
                self._canvas.configure(scrollregion=bbox)
            need = self._needs_scrollbar()
            if need != self._vsb_visible:
                self._vsb_visible = need
                if need:
                    if not self._vsb.winfo_ismapped():
                        self._vsb.pack(side="right", fill="y")
                else:
                    if self._vsb.winfo_ismapped():
                        self._vsb.pack_forget()
                    self._canvas.yview_moveto(0)
        finally:
            self._refresh_busy = False

    def scroll_wheel(self, delta: int) -> None:
        if not self._needs_scrollbar():
            return
        self._canvas.yview_scroll(delta, "units")


class StopButton(tk.Canvas):
    """정사각형 중단 버튼."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        size: int = 48,
        command=None,
        bg: str = BG,
    ):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=bg,
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
        )
        self._size = size
        self._command = command
        self._hover = False
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw(self) -> None:
        self.delete("all")
        fill = STOP_HOVER if self._hover else STOP_BG
        s = self._size
        r = RADIUS_SM
        _fill_round_rect(self, 0, 0, s, s, r, fill)
        center = s // 2
        half = max(6, s // 6)
        self.create_rectangle(
            center - half, center - half, center + half, center + half,
            fill="#FFFFFF", outline="",
        )

    def _on_enter(self, _event=None) -> None:
        self._hover = True
        self._draw()

    def _on_leave(self, _event=None) -> None:
        self._hover = False
        self._draw()

    def _on_click(self, _event=None) -> None:
        if self._command:
            self._command()


class LoadingSpinner(tk.Canvas):
    """작은 회전 아크 로딩 스피너."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        size: int = 18,
        color: str = ACCENT,
        bg: str = BG,
        width: int = 2,
        interval_ms: int = 80,
    ):
        pad = 2
        super().__init__(
            parent,
            width=size + pad * 2,
            height=size + pad * 2,
            bg=bg,
            highlightthickness=0,
            borderwidth=0,
        )
        self._size = size
        self._pad = pad
        self._color = color
        self._width = width
        self._interval = interval_ms
        self._angle = 0
        self._job: str | None = None

    def start(self) -> None:
        if self._job is not None:
            return
        self._tick()

    def stop(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        self.delete("all")

    def set_colors(self, *, color: str | None = None, bg: str | None = None) -> None:
        if color is not None:
            self._color = color
        if bg is not None:
            self.configure(bg=bg)

    def _tick(self) -> None:
        self.delete("all")
        x0, y0 = self._pad, self._pad
        x1, y1 = x0 + self._size, y0 + self._size
        self.create_arc(
            x0, y0, x1, y1,
            start=self._angle, extent=270,
            style="arc", width=self._width, outline=self._color,
        )
        self._angle = (self._angle + 30) % 360
        self._job = self.after(self._interval, self._tick)


class LoadingOverlay:
    """시작 시 로딩 카드"""

    def __init__(self, parent: tk.Misc, logo: tk.PhotoImage | None = None):
        self._visible = False
        self._message = tk.StringVar(value="로딩 중...")

        self._dim = tk.Frame(parent, bg="#E5E7EB")
        card = section_card(self._dim)
        card.place(relx=0.5, rely=0.5, anchor="center", width=320, height=150)

        if logo is not None:
            tk.Label(card.body, image=logo, bg=CARD).pack(pady=(18, 8))
        else:
            tk.Label(
                card.body, text="HanToPdf", font=FONT_SECTION, bg=CARD, fg=TEXT,
            ).pack(pady=(22, 8))
        tk.Label(
            card.body, textvariable=self._message, font=FONT_DESC, bg=CARD, fg=TEXT_SEC,
            wraplength=280,
        ).pack(pady=(0, 12))
        self._bar = ttk.Progressbar(
            card.body, mode="indeterminate", length=240, style="App.Horizontal.TProgressbar",
        )
        self._bar.pack(pady=(0, 20))

    def show(self, message: str = "로딩 중...") -> None:
        self._message.set(message)
        if self._visible:
            return
        self._visible = True
        self._dim.place(x=0, y=0, relwidth=1, relheight=1)
        self._dim.lift()
        self._bar.start(10)

    def set_message(self, message: str) -> None:
        self._message.set(message)

    def hide(self) -> None:
        if not self._visible:
            return
        self._visible = False
        self._bar.stop()
        self._dim.place_forget()


glass_button = app_button
glass_entry = app_entry
glass_listbox = app_listbox
glass_label = app_label
glass_radio = app_radio
glass_group = section_card
