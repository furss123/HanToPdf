"""HanToPdf - 한글 파일 드래그앤드롭 PDF 변환기"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    try:
        from winutil import hide_console_window

        hide_console_window()
    except Exception:
        pass

import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

from app_assets import apply_window_icon, load_photo
from converter import (
    HWP_EXTENSIONS,
    PDF_QUALITY_ORDER,
    PDF_QUALITY_PRESETS,
    ConversionCancelled,
    convert_files,
    get_picture_quality,
    is_hwp_available_fast,
)
from settings import SORT_OPTIONS, load_settings, save_settings
from ui_theme import (
    ACCENT,
    ACCENT_HOVER,
    BG,
    CARD,
    FONT_BODY,
    FONT_COPYRIGHT,
    FONT_DESC,
    FONT_DROP_HINT,
    FONT_DROP_TITLE,
    FONT_LABEL,
    FONT_SECTION,
    ENTRY_IPADY,
    PAD_CONTROL,
    PAD_INNER,
    PAD_OUTER,
    PAD_SECTION,
    SPACING_LABEL,
    TEXT,
    TEXT_SEC,
    ListEmptyOverlay,
    LoadingOverlay,
    LoadingSpinner,
    PrimaryConvertButton,
    ScrollableFrame,
    StopButton,
    app_button,
    app_entry,
    app_file_list,
    app_label,
    app_radio,
    apply_ttk_theme,
    card_row,
    configure_fonts,
    section_card,
    section_label,
)
from auto_update import schedule_update_check
from winutil import ConsoleSuppressor, hide_console_window, set_main_window_hwnd, suppress_background_windows


class SettingsDialog(tk.Toplevel):
    WIDTH = 460
    HEIGHT = 540

    def __init__(self, parent: HanToPdfApp):
        super().__init__(parent)
        self.title("설정")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(self.WIDTH, self.HEIGHT)
        self.transient(parent)
        self.grab_set()

        apply_window_icon(self)
        configure_fonts(self)
        apply_ttk_theme(self)

        self.sort_order = tk.StringVar(value=parent.settings["sort_order"])
        self.pdf_quality = tk.StringVar(value=parent.settings["pdf_quality"])

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=PAD_OUTER, pady=PAD_OUTER)

        sort_lf = section_card(body)
        sort_lf.pack(fill="x", pady=(0, PAD_SECTION))
        section_label(sort_lf.body, "파일 정렬").pack(anchor="w", padx=PAD_INNER, pady=(PAD_INNER, SPACING_LABEL))
        sort_inner = tk.Frame(sort_lf.body, bg=CARD)
        sort_inner.pack(fill="x", padx=PAD_INNER, pady=(0, PAD_INNER))
        for value, label in SORT_OPTIONS.items():
            app_radio(sort_inner, label, self.sort_order, value).pack(anchor="w", pady=2)

        quality_lf = section_card(body)
        quality_lf.pack(fill="x", pady=(0, PAD_SECTION))
        quality_content_w = self.WIDTH - PAD_OUTER * 2 - PAD_INNER * 2
        quality_radio_w = 96
        quality_desc_wrap = quality_content_w - quality_radio_w - PAD_CONTROL
        section_label(quality_lf.body, "한글 → PDF 변환 화질").pack(
            anchor="w", padx=PAD_INNER, pady=(PAD_INNER, SPACING_LABEL),
        )
        quality_inner = tk.Frame(quality_lf.body, bg=CARD)
        quality_inner.pack(fill="x", padx=PAD_INNER, pady=(0, PAD_INNER))
        app_label(
            quality_inner,
            "한글 파일을 PDF로 저장할 때 이미지·그림 품질을 선택합니다.",
            secondary=True,
            wraplength=quality_content_w,
        ).pack(fill="x", anchor="w", pady=(0, 8))

        for key in PDF_QUALITY_ORDER:
            preset = PDF_QUALITY_PRESETS[key]
            row = tk.Frame(quality_inner, bg=CARD)
            row.pack(fill="x", pady=3)
            row.grid_columnconfigure(1, weight=1)
            app_radio(row, preset["label"], self.pdf_quality, key).grid(
                row=0, column=0, sticky="nw",
            )
            app_label(
                row,
                preset["desc"],
                secondary=True,
                wraplength=quality_desc_wrap,
            ).grid(row=0, column=1, sticky="w", padx=(PAD_CONTROL, 0))

        btn_row = tk.Frame(body, bg=BG)
        btn_row.pack(fill="x", pady=(16, 0))
        app_button(btn_row, "취소", command=self.destroy, small=True).pack(side="right")
        app_button(btn_row, "저장", command=self._save, accent=True).pack(side="right", padx=(0, 8))

        self._parent = parent
        self._place_on_screen(parent)

    def _place_on_screen(self, parent: HanToPdfApp) -> None:
        self.update_idletasks()
        width = max(self.WIDTH, self.winfo_reqwidth())
        height = max(self.HEIGHT, self.winfo_reqheight())
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = px + max(0, (pw - width) // 2)
        y = py + max(0, (ph - height) // 2)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = min(max(0, x), max(0, sw - width))
        y = min(max(0, y), max(0, sh - height))
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _save(self):
        self._parent.settings["sort_order"] = self.sort_order.get()
        self._parent.settings["pdf_quality"] = self.pdf_quality.get()
        save_settings(self._parent.settings)
        self._parent._apply_sort()
        self._parent._refresh_list()
        self._parent._update_quality_label()
        self.destroy()


class HanToPdfApp(TkinterDnD.Tk):
    LIST_ROWS = 10
    LIST_ROW_PX = 26
    WIN_WIDTH = 480
    CONTENT_WRAP = WIN_WIDTH - PAD_OUTER * 2 - PAD_INNER * 2
    CHECK_ON = "☑"
    CHECK_OFF = "☐"

    def __init__(self):
        super().__init__()
        self.title("HanToPdf")
        self.geometry(f"{self.WIN_WIDTH}x600")
        self.minsize(self.WIN_WIDTH, 500)
        self.maxsize(self.WIN_WIDTH, self.winfo_screenheight())
        self.configure(bg=BG)
        self.resizable(False, True)

        apply_window_icon(self)
        configure_fonts(self)
        apply_ttk_theme(self)
        self._list_measure_font = tkfont.Font(font=FONT_BODY)

        self.settings = load_settings()
        self.files: list[Path] = []
        self._file_checked: set[int] = set()
        self._drag_from_idx: int | None = None
        self.output_dir = tk.StringVar(value=str(Path.home() / "Desktop"))
        self.output_filename = tk.StringVar(value="")
        self.mode = tk.StringVar(value="separate")
        self._busy = False
        self._loading_depth = 0
        self._cancel_event = threading.Event()
        self._list_layout_job: str | None = None
        self._list_layout_busy = False
        self._last_list_col_w = 0
        self._last_list_hscroll: bool | None = None
        self._convert_started_at: float | None = None
        self._eta_deadline: float | None = None
        self._eta_tick_job: str | None = None
        self._last_root_h = 0
        self._list_measure_font: tkfont.Font | None = None

        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        self.content = self.scroll.inner

        self._build_ui()
        self.loading = LoadingOverlay(self, logo=load_photo(self, "banner_h44.png"))
        self.update_idletasks()
        set_main_window_hwnd(self.winfo_id())
        self._bind_dnd()
        self._bind_main_scroll()
        self._fit_window_size()
        self.bind("<Configure>", self._on_root_configure)
        suppress_background_windows()
        self.after(50, self._check_hwp_async)

    def _begin_loading(self, message: str = "로딩 중...") -> None:
        self._loading_depth += 1
        self.loading.show(message)
        suppress_background_windows()

    def _end_loading(self) -> None:
        self._loading_depth = max(0, self._loading_depth - 1)
        if self._loading_depth == 0:
            self.loading.hide()

    def _check_hwp_async(self):
        if not is_hwp_available_fast():
            messagebox.showwarning(
                "한컴오피스 필요",
                "한컴오피스(한글)가 설치되어 있어야 변환이 가능합니다.\n"
                "설치 후 다시 실행해 주세요.",
            )

    def _fit_window_size(self) -> None:
        """내용 높이에 맞추되 화면을 넘으면 스크롤로 처리."""
        self.update_idletasks()
        req_w = self.WIN_WIDTH
        content_h = self.content.winfo_reqheight() + 4
        screen_h = self.winfo_screenheight()
        max_h = max(500, int(screen_h * 0.88))
        win_h = min(content_h, max_h)
        self.geometry(f"{req_w}x{win_h}")
        self.minsize(self.WIN_WIDTH, 500)
        self.maxsize(self.WIN_WIDTH, screen_h)
        self.scroll.refresh()

    def _on_root_configure(self, event) -> None:
        if event.widget is not self or event.height == self._last_root_h:
            return
        self._last_root_h = event.height
        self.after_idle(self._refresh_scroll_and_list)

    def _refresh_scroll_and_list(self) -> None:
        self.scroll.refresh()
        self._sync_file_list_layout()

    def _bind_main_scroll(self) -> None:
        self.bind_all("<MouseWheel>", self._on_main_mousewheel)

    def _is_descendant(self, widget: tk.Misc, ancestor: tk.Misc) -> bool:
        w = widget
        while w is not None:
            if w == ancestor:
                return True
            w = w.master
        return False

    def _on_main_mousewheel(self, event) -> None:
        target = self.winfo_containing(event.x_root, event.y_root)
        if target and self._is_descendant(target, self.file_list):
            return
        delta = int(-1 * (event.delta / 120))
        if delta:
            self.scroll.scroll_wheel(delta)

    def _refresh_scroll(self) -> None:
        self.update_idletasks()
        self.scroll.refresh()
        self._sync_file_list_layout()

    # ── UI ──

    def _build_ui(self):
        pad = PAD_OUTER
        root = self.content
        sec_gap = (0, PAD_SECTION)
        label_gap = (0, SPACING_LABEL)

        # 변환 목록
        list_section = tk.Frame(root, bg=BG)
        list_section.pack(fill="x", padx=pad, pady=(pad, PAD_CONTROL))

        list_card = section_card(list_section)
        list_card.pack(fill="x")
        list_h = self.LIST_ROWS * self.LIST_ROW_PX + 8
        list_inner = tk.Frame(list_card.body, bg=CARD, height=list_h)
        list_inner.pack(fill="x", padx=PAD_INNER, pady=PAD_INNER)
        list_inner.pack_propagate(False)
        list_inner.grid_rowconfigure(0, weight=1)
        list_inner.grid_columnconfigure(0, weight=1)

        self.list_empty_overlay = ListEmptyOverlay(
            list_inner, on_click=self._browse_files,
        )
        empty_inner = self.list_empty_overlay.inner
        icon_wrap = tk.Frame(empty_inner, bg=CARD)
        icon_wrap.pack(anchor="center", pady=(10, 8))
        icon_lg = load_photo(self, "banner_h44.png")
        if icon_lg is not None:
            tk.Label(icon_wrap, image=icon_lg, bg=CARD).pack()
        app_label(
            empty_inner,
            "클릭하여 파일 선택",
            bg=CARD,
            font=FONT_DROP_TITLE,
            fg=TEXT,
        ).pack(anchor="center", pady=(0, 6))
        app_label(
            empty_inner,
            "또는 .hwp · .hwpx 파일을 여기에 드래그하세요",
            bg=CARD,
            font=FONT_DROP_HINT,
            fg=TEXT_SEC,
            wraplength=self.CONTENT_WRAP,
            justify="center",
        ).pack(anchor="center", pady=(0, 10))
        self.list_empty_overlay.bind_inner_clicks()

        self.file_list = app_file_list(list_inner, height=self.LIST_ROWS)
        self._list_sb = ttk.Scrollbar(
            list_inner, orient="vertical", command=self.file_list.yview,
            style="App.Vertical.TScrollbar",
        )
        self._list_hsb = ttk.Scrollbar(
            list_inner, orient="horizontal", command=self.file_list.xview,
            style="App.Horizontal.TScrollbar",
        )
        self.file_list.configure(
            yscrollcommand=self._list_sb.set,
            xscrollcommand=self._list_hsb.set,
        )
        self.file_list.grid(row=0, column=0, sticky="nsew")
        self.list_empty_overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self._list_sb.grid(row=0, column=1, sticky="ns")
        self._list_hsb.grid(row=1, column=0, sticky="ew")
        self._list_hsb.grid_remove()
        self._bind_file_list_interactions()

        self._sync_file_list_layout()

        # 삭제 · 순서
        btn_row = tk.Frame(root, bg=BG)
        btn_row.pack(fill="x", padx=pad, pady=(PAD_CONTROL, PAD_SECTION))
        order_btns = tk.Frame(btn_row, bg=BG)
        order_btns.pack(side="left")
        app_button(order_btns, "▲", command=self._move_file_up, small=True).pack(
            side="left", padx=(0, 4),
        )
        app_button(order_btns, "▼", command=self._move_file_down, small=True).pack(side="left")
        app_button(btn_row, "선택 삭제", command=self._remove_selected, small=True).pack(
            side="right",
        )
        app_button(btn_row, "전체 삭제", command=self._clear_files, small=True).pack(
            side="right", padx=(0, 8),
        )

        # 변환 방식
        mode_section = tk.Frame(root, bg=BG)
        mode_section.pack(fill="x", padx=pad, pady=sec_gap)
        section_label(mode_section, "변환 방식").pack(anchor="w", pady=label_gap)
        mode_card = section_card(mode_section)
        mode_card.pack(fill="x")
        mode_inner = card_row(mode_card.body)
        app_radio(mode_inner, "개별 PDF (파일마다)", self.mode, "separate").pack(
            side="left", padx=(0, PAD_CONTROL),
        )
        app_radio(mode_inner, "하나의 PDF로 합치기", self.mode, "merge").pack(side="left")

        # PDF 화질
        quality_section = tk.Frame(root, bg=BG)
        quality_section.pack(fill="x", padx=pad, pady=sec_gap)
        section_label(quality_section, "PDF 변환 화질").pack(anchor="w", pady=label_gap)
        quality_card = section_card(quality_section)
        quality_card.pack(fill="x")
        quality_row = card_row(quality_card.body)
        self.quality_label = tk.StringVar()
        self._update_quality_label()
        app_label(
            quality_row, textvariable=self.quality_label, font=FONT_BODY,
        ).pack(side="left", fill="x", expand=True)
        app_button(quality_row, "변경", command=self._open_settings, small=True).pack(
            side="right", padx=(PAD_CONTROL, 0),
        )

        # 저장 위치 · 파일명
        out_section = tk.Frame(root, bg=BG)
        out_section.pack(fill="x", padx=pad, pady=sec_gap)
        section_label(out_section, "저장 위치").pack(anchor="w", pady=label_gap)
        out_card = section_card(out_section)
        out_card.pack(fill="x")
        out_row = card_row(out_card.body)
        self.out_entry = app_entry(out_row, self.output_dir)
        self.out_entry.pack(side="left", fill="x", expand=True, ipady=ENTRY_IPADY)
        app_button(out_row, "찾기", command=self._browse_output, small=True).pack(
            side="right", padx=(PAD_CONTROL, 0),
        )

        section_label(out_section, "저장 파일명").pack(anchor="w", pady=(PAD_SECTION, SPACING_LABEL))
        name_card = section_card(out_section)
        name_card.pack(fill="x")
        name_row = card_row(name_card.body)
        self.out_name_entry = app_entry(name_row, self.output_filename)
        self.out_name_entry.pack(fill="x", ipady=ENTRY_IPADY)
        app_label(
            out_section,
            "비워두면 자동 (개별: 원본 이름 / 합치기: merged.pdf)",
            hint=True,
        ).pack(anchor="w", pady=(SPACING_LABEL, 0))

        # PDF 변환
        self._convert_btn_height = 46
        self.convert_wrap = tk.Frame(root, bg=BG)
        self.convert_wrap.pack(fill="x", padx=pad, pady=(PAD_SECTION, PAD_CONTROL))

        self.convert_primary = PrimaryConvertButton(
            self.convert_wrap,
            text="PDF 변환",
            command=self._start_convert,
            height=self._convert_btn_height,
        )
        self.convert_primary.pack(side="left", fill="x", expand=True)

        self.convert_stop = StopButton(
            self.convert_wrap,
            size=self._convert_btn_height,
            command=self._cancel_convert,
            bg=BG,
        )

        # 변환 진행 (작업 중에만 표시)
        self.progress_pct = tk.StringVar(value="0%")
        self.progress_eta = tk.StringVar(value="")
        self.progress_task = tk.StringVar(value="")
        self.progress_panel = tk.Frame(root, bg=BG)
        prog_row = tk.Frame(self.progress_panel, bg=BG)
        prog_row.pack(fill="x")
        self.progress_spinner = LoadingSpinner(prog_row, size=16, color=ACCENT, bg=BG)
        self.progress_spinner.pack(side="left", padx=(0, 8))
        self.progress = ttk.Progressbar(
            prog_row, mode="determinate", maximum=100, style="App.Horizontal.TProgressbar",
        )
        self.progress.pack(side="left", fill="x", expand=True, ipady=3)
        tk.Label(
            prog_row, textvariable=self.progress_pct, font=FONT_LABEL,
            bg=BG, fg=TEXT, width=5, anchor="e",
        ).pack(side="right", padx=(10, 0))
        tk.Label(
            prog_row, textvariable=self.progress_eta, font=FONT_LABEL,
            bg=BG, fg=TEXT_SEC, width=6, anchor="e",
        ).pack(side="right", padx=(4, 0))
        app_label(
            self.progress_panel, textvariable=self.progress_task, font=FONT_DESC,
        ).pack(anchor="w", pady=(SPACING_LABEL, 0))

        self.status = tk.StringVar(value="")
        self.status_label = app_label(
            root, textvariable=self.status, secondary=True, font=FONT_DESC,
        )
        self.status_label.pack(pady=(SPACING_LABEL, 4))
        app_label(
            root,
            f"© {date.today().year} HyoT. All rights reserved.",
            hint=True,
            font=FONT_COPYRIGHT,
        ).pack(pady=(0, pad), anchor="center")
        self._show_list_content()

    def _show_list_content(self) -> None:
        if self.files:
            self.list_empty_overlay.place_forget()
        else:
            self.list_empty_overlay.place(x=0, y=0, relwidth=1, relheight=1)
            self.list_empty_overlay.lift()

    def _bind_dnd(self):
        targets = [
            self, self.scroll, self.scroll._canvas, self.content,
            self.list_empty_overlay, self.list_empty_overlay.canvas,
            self.list_empty_overlay.inner,
            self.file_list,
        ]

        def walk(widget):
            for child in widget.winfo_children():
                targets.append(child)
                walk(child)

        walk(self.list_empty_overlay.inner)

        seen = set()
        for widget in targets:
            wid = widget.winfo_id()
            if wid in seen:
                continue
            seen.add(wid)
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop_event)

    def _on_drop_event(self, event):
        paths = self.tk.splitlist(event.data)
        added = 0
        known = {f.resolve() for f in self.files}
        for text in paths:
            p = Path(text.strip().strip("{}"))
            if not p.is_file():
                continue
            if p.suffix.lower() not in HWP_EXTENSIONS:
                continue
            resolved = p.resolve()
            if resolved in known:
                continue
            self.files.append(resolved)
            known.add(resolved)
            added += 1
        self._apply_sort()
        self._refresh_list()
        if added:
            self._update_status_count()
        elif paths:
            self.status.set("한글 파일(.hwp, .hwpx)만 추가할 수 있습니다")
        return event.action

    # ── 파일 관리 ──

    def _bind_file_list_interactions(self) -> None:
        self.file_list.bind("<Button-1>", self._on_file_list_press, add=True)
        self.file_list.bind("<ButtonRelease-1>", self._on_file_list_release, add=True)

    def _on_file_list_press(self, event) -> str | None:
        if not self.files:
            return None
        region = self.file_list.identify_region(event.x, event.y)
        if region != "cell":
            return None
        iid = self.file_list.identify_row(event.y)
        if not iid:
            return None
        col = self.file_list.identify_column(event.x)
        idx = int(iid)
        if col == "#1":
            self._toggle_file_check(idx)
            return "break"
        self._drag_from_idx = idx
        self.file_list.selection_set(iid)
        return None

    def _on_file_list_release(self, event) -> None:
        if self._drag_from_idx is None:
            return
        from_idx = self._drag_from_idx
        iid = self.file_list.identify_row(event.y)
        self._drag_from_idx = None
        if not iid:
            return
        to_idx = int(iid)
        if from_idx != to_idx:
            self._move_file_to_index(from_idx, to_idx)

    def _toggle_file_check(self, idx: int) -> None:
        if idx in self._file_checked:
            self._file_checked.discard(idx)
        else:
            self._file_checked.add(idx)
        mark = self.CHECK_ON if idx in self._file_checked else self.CHECK_OFF
        self.file_list.set(str(idx), "check", mark)

    @staticmethod
    def _remap_checked_indices(checked: set[int], from_idx: int, to_idx: int) -> set[int]:
        remapped: set[int] = set()
        for i in checked:
            if i == from_idx:
                remapped.add(to_idx)
            elif from_idx < to_idx and from_idx < i <= to_idx:
                remapped.add(i - 1)
            elif to_idx < from_idx and to_idx <= i < from_idx:
                remapped.add(i + 1)
            else:
                remapped.add(i)
        return remapped

    def _move_file_to_index(self, from_idx: int, to_idx: int) -> None:
        if not (0 <= from_idx < len(self.files) and 0 <= to_idx < len(self.files)):
            return
        item = self.files.pop(from_idx)
        self.files.insert(to_idx, item)
        self._file_checked = self._remap_checked_indices(self._file_checked, from_idx, to_idx)
        self._refresh_list()
        self.file_list.selection_set(str(to_idx))

    def _primary_file_index(self) -> int | None:
        if len(self._file_checked) == 1:
            return next(iter(self._file_checked))
        sel = self.file_list.selection()
        if sel:
            return int(sel[0])
        if self._file_checked:
            return min(self._file_checked)
        return None

    def _move_file_up(self) -> None:
        idx = self._primary_file_index()
        if idx is None or idx <= 0:
            return
        self._move_file_to_index(idx, idx - 1)

    def _move_file_down(self) -> None:
        idx = self._primary_file_index()
        if idx is None or idx >= len(self.files) - 1:
            return
        self._move_file_to_index(idx, idx + 1)

    def _browse_files(self):
        paths = filedialog.askopenfilenames(
            title="한글 파일 선택",
            filetypes=[("한글 파일", "*.hwp *.hwpx"), ("모든 파일", "*.*")],
        )
        if paths:
            known = {f.resolve() for f in self.files}
            for p in paths:
                path = Path(p)
                if path.resolve() not in known:
                    self.files.append(path)
                    known.add(path.resolve())
            self._apply_sort()
            self._refresh_list()
            self._update_status_count()

    def _open_settings(self):
        if self._busy:
            return
        SettingsDialog(self)

    def _update_quality_label(self) -> None:
        key = self.settings.get("pdf_quality", "high")
        preset = PDF_QUALITY_PRESETS.get(key, PDF_QUALITY_PRESETS["high"])
        self.quality_label.set(f"{preset['label']} — {preset['desc']}")

    def _apply_sort(self):
        order = self.settings.get("sort_order", "asc")
        if order == "asc":
            self.files.sort(key=lambda f: f.name.lower())
        elif order == "desc":
            self.files.sort(key=lambda f: f.name.lower(), reverse=True)

    def _browse_output(self):
        d = filedialog.askdirectory(title="저장 위치 선택")
        if d:
            self.output_dir.set(d)

    def _sync_file_list_layout(self, event=None) -> None:
        if self._list_layout_busy:
            return
        if self._list_layout_job is not None:
            self.after_cancel(self._list_layout_job)
        self._list_layout_job = self.after_idle(self._apply_file_list_layout)

    def _apply_file_list_layout(self) -> None:
        self._list_layout_job = None
        if not hasattr(self, "file_list"):
            return

        self._list_layout_busy = True
        try:
            font = self._list_measure_font or tkfont.Font(font=FONT_BODY)
            content_w = max((font.measure(f.name) for f in self.files), default=0) + 44
            list_inner = self.file_list.master
            vsb_w = self._list_sb.winfo_width() if self._list_sb.winfo_ismapped() else 0
            viewport_w = max(list_inner.winfo_width() - vsb_w - 2, 80)
            col_w = int(max(content_w, viewport_w))
            need_hscroll = content_w > viewport_w

            if col_w != self._last_list_col_w:
                self._last_list_col_w = col_w
                self.file_list.column("name", width=col_w)

            if need_hscroll != self._last_list_hscroll:
                self._last_list_hscroll = need_hscroll
                if need_hscroll:
                    self._list_hsb.grid(row=1, column=0, sticky="ew")
                else:
                    self._list_hsb.grid_remove()
                    self.file_list.xview_moveto(0)
        finally:
            self._list_layout_busy = False

    def _refresh_list(self):
        checked_paths = {
            self.files[i].resolve()
            for i in self._file_checked
            if 0 <= i < len(self.files)
        }
        self.file_list.delete(*self.file_list.get_children())
        new_checked: set[int] = set()
        for i, f in enumerate(self.files):
            if f.resolve() in checked_paths:
                new_checked.add(i)
            mark = self.CHECK_ON if i in new_checked else self.CHECK_OFF
            self.file_list.insert("", tk.END, iid=str(i), values=(mark, f.name))
        self._file_checked = new_checked
        self._show_list_content()
        self._sync_file_list_layout()

    def _remove_selected(self):
        indices = sorted(self._file_checked, reverse=True)
        if not indices:
            sel = self.file_list.selection()
            indices = sorted((int(iid) for iid in sel), reverse=True)
        if not indices:
            return
        for i in indices:
            if 0 <= i < len(self.files):
                del self.files[i]
        self._file_checked.clear()
        self._refresh_list()
        self._update_status_count()

    def _clear_files(self):
        self.files.clear()
        self._file_checked.clear()
        self._drag_from_idx = None
        self._refresh_list()
        self.status.set("")

    def _update_status_count(self) -> None:
        if self.files:
            self.status.set(f"{len(self.files)}개 파일 준비됨")
        else:
            self.status.set("")

    # ── 변환 ──

    @staticmethod
    def _truncate_text(text: str, max_len: int = 52) -> str:
        if len(text) <= max_len:
            return text
        keep = max_len - 3
        left = keep // 2 + keep % 2
        right = keep // 2
        return f"{text[:left]}...{text[-right:]}"

    def _set_convert_busy(self, busy: bool) -> None:
        if busy:
            self.convert_primary.set_busy(True, "변환 중...")
            self.convert_stop.pack(side="right", padx=(8, 0))
        else:
            self.convert_primary.set_busy(False, "PDF 변환")
            self.convert_stop.pack_forget()

    def _reset_eta(self) -> None:
        self._convert_started_at = None
        self._eta_deadline = None
        self.progress_eta.set("")
        self._stop_eta_tick()

    def _start_eta_tick(self) -> None:
        self._stop_eta_tick()
        self._convert_started_at = time.monotonic()
        self._eta_deadline = None
        self.progress_eta.set("")
        self._tick_eta()

    def _stop_eta_tick(self) -> None:
        if self._eta_tick_job is not None:
            self.after_cancel(self._eta_tick_job)
            self._eta_tick_job = None

    def _recalc_eta(self, pct: int) -> None:
        if self._convert_started_at is None:
            return
        if pct >= 100:
            self._eta_deadline = time.monotonic()
            self.progress_eta.set("0초")
            return
        if pct < 3:
            self.progress_eta.set("—")
            return
        elapsed = time.monotonic() - self._convert_started_at
        remaining = elapsed * (100 - pct) / pct
        self._eta_deadline = time.monotonic() + remaining

    def _tick_eta(self) -> None:
        if not self._busy:
            self._eta_tick_job = None
            return
        if self._eta_deadline is not None:
            sec = max(0, int(round(self._eta_deadline - time.monotonic())))
            self.progress_eta.set(f"{sec}초")
        self._eta_tick_job = self.after(1000, self._tick_eta)

    def _cancel_convert(self) -> None:
        if not self._busy:
            return
        self._cancel_event.set()
        self.progress_task.set("중단 중...")
        self.progress_eta.set("—")

    def _show_progress_panel(self) -> None:
        if not self.progress_panel.winfo_ismapped():
            self.progress_panel.pack(fill="x", padx=PAD_OUTER, pady=(0, 8), after=self.convert_wrap)
        self.progress_spinner.start()
        self.status_label.pack_forget()
        self._refresh_scroll()
        if self.scroll._needs_scrollbar():
            self.after_idle(lambda: self.scroll._canvas.yview_moveto(1.0))

    def _hide_progress_panel(self) -> None:
        self.progress_spinner.stop()
        self._reset_eta()
        self.progress_panel.pack_forget()
        if not self.status_label.winfo_ismapped():
            self.status_label.pack(pady=(4, 2))
        self._refresh_scroll()

    def _start_convert(self):
        if self._busy:
            return
        if not self.files:
            messagebox.showinfo("알림", "변환할 파일을 추가해 주세요.")
            return

        out = self.output_dir.get().strip()
        if not out:
            messagebox.showinfo("알림", "저장 위치를 선택해 주세요.")
            return

        self._busy = True
        self._cancel_event.clear()
        suppress_background_windows()
        self._set_convert_busy(True)
        self._show_progress_panel()
        self.progress["value"] = 0
        self.progress_pct.set("0%")
        self.progress_task.set("준비 중...")
        self._start_eta_tick()
        self.status.set("")

        mode = self.mode.get()
        files_copy = list(self.files)
        out_dir = out
        output_filename = self.output_filename.get().strip()
        quality_key = self.settings.get("pdf_quality", "high")
        picture_quality = get_picture_quality(quality_key)

        def run():
            try:
                if not is_hwp_available_fast():
                    self.after(0, lambda: self._on_convert_blocked(
                        "한컴오피스(한글)가 설치되어 있지 않습니다.",
                    ))
                    return

                def prog(percent, filename, action):
                    self.after(
                        0,
                        lambda p=percent, f=filename, a=action: self._update_progress(p, f, a),
                    )

                results = convert_files(
                    files_copy, out_dir, mode=mode,
                    output_filename=output_filename or None,
                    picture_quality=picture_quality, progress_cb=prog,
                    should_cancel=self._cancel_event.is_set,
                )
                self.after(0, lambda: self._on_done(results, None))
            except ConversionCancelled:
                self.after(0, lambda: self._on_cancelled())
            except Exception as exc:
                self.after(0, lambda e=exc: self._on_done(None, e))

        threading.Thread(target=run, daemon=True).start()

    def _on_convert_blocked(self, message: str):
        self._busy = False
        self._set_convert_busy(False)
        self._hide_progress_panel()
        self.status.set("변환 실패")
        messagebox.showerror("오류", message)

    def _update_progress(self, percent: float, filename: str, action: str):
        pct = int(round(percent))
        self.progress["value"] = pct
        self.progress_pct.set(f"{pct}%")
        self._recalc_eta(pct)
        if filename:
            short = self._truncate_text(filename)
            self.progress_task.set(f"{short} · {action}")
        else:
            self.progress_task.set(action)

    def _on_cancelled(self) -> None:
        self._busy = False
        self._set_convert_busy(False)
        self._hide_progress_panel()
        self.status.set("변환 중단됨")
        messagebox.showinfo("중단", "변환을 중단했습니다.")

    def _on_done(self, results, error):
        self._busy = False
        self._set_convert_busy(False)

        if error:
            self._hide_progress_panel()
            self.status.set("변환 실패")
            messagebox.showerror("변환 오류", str(error))
            return

        self._update_progress(100, "", "완료")
        self.after(600, self._hide_progress_panel)

        count = len(results)
        out = self.output_dir.get()
        self.status.set(f"완료! {count}개 PDF 생성됨")
        if count == 1:
            msg = f"저장됨:\n{results[0]}"
        else:
            msg = f"{count}개 PDF가 저장되었습니다.\n\n위치: {out}"
        messagebox.showinfo("변환 완료", msg)


def main():
    if len(sys.argv) >= 6 and sys.argv[1] == "--hantopdf-apply-update":
        from update_apply import run_apply_update_cli

        raise SystemExit(run_apply_update_cli(sys.argv[2:6]))

    hide_console_window()
    if getattr(sys, "frozen", False):
        from winutil import silence_stdio

        silence_stdio()

    suppressor = ConsoleSuppressor()
    suppressor.start()
    try:
        app = HanToPdfApp()
        schedule_update_check(app)
        app.mainloop()
    finally:
        suppressor.stop()


if __name__ == "__main__":
    main()
