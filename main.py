"""HanToPdf - 한글 파일 드래그앤드롭 PDF 변환기"""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

from converter import (
    HWP_EXTENSIONS,
    PDF_QUALITY_ORDER,
    PDF_QUALITY_PRESETS,
    check_hwp_installed,
    convert_files,
    get_picture_quality,
)
from settings import SORT_OPTIONS, load_settings, save_settings
from ui_theme import (
    ACCENT,
    ACCENT_DISABLED,
    ACCENT_HOVER,
    BG,
    DROP_BG,
    FONT_BODY,
    FONT_SECTION,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
    TEXT,
    TEXT_SEC,
    DropZone,
    apply_ttk_theme,
    attach_gradient,
    glass_button,
    glass_entry,
    glass_group,
    glass_label,
    glass_listbox,
    glass_radio,
)
from winutil import hide_console_window


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

        attach_gradient(self)
        apply_ttk_theme(self)

        self.sort_order = tk.StringVar(value=parent.settings["sort_order"])
        self.pdf_quality = tk.StringVar(value=parent.settings["pdf_quality"])

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=20)

        sort_lf = glass_group(body, "파일 정렬")
        sort_lf.pack(fill="x", pady=(0, 16))
        for value, label in SORT_OPTIONS.items():
            glass_radio(sort_lf, label, self.sort_order, value).pack(anchor="w", pady=2)

        quality_lf = glass_group(body, "한글 → PDF 변환 화질")
        quality_lf.pack(fill="x", pady=(0, 8))
        glass_label(
            quality_lf,
            "한글 파일을 PDF로 저장할 때 이미지·그림 품질을 선택합니다.",
            secondary=True,
            wraplength=self.WIDTH - 80,
        ).pack(anchor="w", pady=(0, 8))

        for key in PDF_QUALITY_ORDER:
            preset = PDF_QUALITY_PRESETS[key]
            row = tk.Frame(quality_lf, bg=quality_lf.cget("bg"))
            row.pack(anchor="w", fill="x", pady=3)
            glass_radio(row, preset["label"], self.pdf_quality, key).pack(side="left")
            glass_label(
                row, preset["desc"], secondary=True, wraplength=self.WIDTH - 160,
            ).pack(side="left", padx=(8, 0))

        btn_row = tk.Frame(body, bg=BG)
        btn_row.pack(fill="x", pady=(16, 0))
        glass_button(btn_row, "취소", command=self.destroy).pack(side="right")
        glass_button(btn_row, "저장", command=self._save, accent=True).pack(side="right", padx=(0, 8))

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
    def __init__(self):
        super().__init__()
        self.title("HanToPdf")
        self.geometry("480x600")
        self.minsize(480, 580)
        self.configure(bg=BG)
        self.resizable(True, True)

        attach_gradient(self)
        apply_ttk_theme(self)

        self.settings = load_settings()
        self.files: list[Path] = []
        self.output_dir = tk.StringVar(value=str(Path.home() / "Desktop"))
        self.mode = tk.StringVar(value="separate")
        self._busy = False

        self._build_ui()
        self._bind_dnd()
        self.after(300, self._check_hwp_async)

    def _check_hwp_async(self):
        def run():
            if not check_hwp_installed():
                self.after(
                    0,
                    lambda: messagebox.showwarning(
                        "한컴오피스 필요",
                        "한컴오피스(한글)가 설치되어 있어야 변환이 가능합니다.\n"
                        "설치 후 다시 실행해 주세요.",
                    ),
                )

        threading.Thread(target=run, daemon=True).start()

    # ── UI ──

    def _build_ui(self):
        # ① 헤더
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=24, pady=(20, 4))
        header_left = tk.Frame(header, bg=BG)
        header_left.pack(side="left", fill="x", expand=True)
        tk.Label(
            header_left, text="HanToPdf", font=FONT_TITLE, bg=BG, fg=TEXT,
        ).pack(anchor="w")
        tk.Label(
            header_left, text="한글 파일을 PDF로 변환", font=FONT_SUBTITLE,
            bg=BG, fg=TEXT_SEC,
        ).pack(anchor="w", pady=(2, 0))
        glass_button(header, "설정", command=self._open_settings, small=True).pack(
            side="right", anchor="n",
        )

        # ② 드롭존
        self.drop_frame = DropZone(self, height=150, on_click=self._browse_files)
        self.drop_frame.pack(fill="both", expand=True, padx=24, pady=(16, 8))
        inner = self.drop_frame.inner

        tk.Label(inner, text="📄", font=("Segoe UI Emoji", 28), bg=DROP_BG, fg=TEXT).pack()
        glass_label(inner, "한글 파일을 여기에 드래그", bg=DROP_BG).pack(pady=(4, 0))
        glass_label(inner, ".hwp  ·  .hwpx", secondary=True, bg=DROP_BG).pack()
        btn_add = tk.Label(
            inner, text="파일 선택", font=("맑은 고딕", 9, "underline"),
            bg=DROP_BG, fg=ACCENT, cursor="hand2",
        )
        btn_add.pack(pady=(8, 0))
        btn_add.bind("<Button-1>", lambda e: self._browse_files())

        # ③ 파일 목록
        list_frame = tk.Frame(self, bg=BG)
        list_frame.pack(fill="both", expand=False, padx=24, pady=(0, 8))

        self.listbox = glass_listbox(list_frame, height=4)
        self.listbox.pack(fill="both", expand=True, side="left")

        sb = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.listbox.yview,
            style="Glass.Vertical.TScrollbar",
        )
        sb.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=sb.set)

        # ④ 삭제 버튼
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=24, pady=(0, 8))
        glass_button(btn_row, "선택 삭제", command=self._remove_selected, small=True).pack(
            side="right",
        )
        glass_button(btn_row, "전체 삭제", command=self._clear_files, small=True).pack(
            side="right", padx=(0, 8),
        )

        # ⑤ 변환 방식
        mode_frame = glass_group(self, "변환 방식")
        mode_frame.pack(fill="x", padx=24, pady=(0, 8))
        glass_radio(mode_frame, "개별 PDF (파일마다)", self.mode, "separate").pack(anchor="w")
        glass_radio(mode_frame, "하나의 PDF로 합치기", self.mode, "merge").pack(anchor="w")

        # ⑥ PDF 화질
        quality_row = tk.Frame(self, bg=BG)
        quality_row.pack(fill="x", padx=24, pady=(0, 8))
        glass_label(quality_row, "PDF 변환 화질", font=FONT_SECTION).pack(side="left")
        self.quality_label = tk.StringVar()
        self._update_quality_label()
        glass_label(
            quality_row, textvariable=self.quality_label, secondary=True,
        ).pack(side="left", padx=(8, 0))
        link = tk.Label(
            quality_row, text="변경", font=("맑은 고딕", 8, "underline"),
            bg=BG, fg=ACCENT, cursor="hand2",
        )
        link.pack(side="right")
        link.bind("<Button-1>", lambda e: self._open_settings())

        # ⑦ 저장 위치
        out_frame = tk.Frame(self, bg=BG)
        out_frame.pack(fill="x", padx=24, pady=(0, 12))
        glass_label(out_frame, "저장 위치", font=FONT_SECTION).pack(anchor="w")

        out_row = tk.Frame(out_frame, bg=BG)
        out_row.pack(fill="x", pady=(4, 0))
        self.out_entry = glass_entry(out_row, self.output_dir)
        self.out_entry.pack(side="left", fill="x", expand=True, ipady=6)
        glass_button(out_row, "찾기", command=self._browse_output, small=True).pack(
            side="right", padx=(8, 0),
        )

        # ⑧ PDF 변환 버튼
        self.convert_btn = glass_button(
            self, "PDF 변환", command=self._start_convert, primary=True,
        )
        self.convert_btn.pack(fill="x", padx=24, pady=(0, 8))

        # ⑨ 하단 안내
        self.status = tk.StringVar(value="파일을 추가해 주세요")
        glass_label(self, textvariable=self.status, secondary=True, font=FONT_SMALL).pack(
            pady=(0, 16),
        )

        self.progress = ttk.Progressbar(self, mode="determinate", style="Glass.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=24, pady=(0, 12))
        self.progress.pack_forget()

    # ── 드래그앤드롭 ──

    def _bind_dnd(self):
        targets = [self, self.drop_frame, self.drop_frame.canvas, self.drop_frame.inner, self.listbox]

        def walk(widget):
            for child in widget.winfo_children():
                targets.append(child)
                walk(child)

        walk(self.drop_frame.inner)

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
            self.status.set(f"{len(self.files)}개 파일 준비됨")
        elif paths:
            self.status.set("한글 파일(.hwp, .hwpx)만 추가할 수 있습니다")
        return event.action

    # ── 파일 관리 ──

    def _browse_files(self):
        paths = filedialog.askopenfilenames(
            title="한글 파일 선택",
            filetypes=[("한글 파일", "*.hwp *.hwpx"), ("모든 파일", "*.*")],
        )
        if paths:
            for p in paths:
                path = Path(p)
                if path.resolve() not in {f.resolve() for f in self.files}:
                    self.files.append(path)
            self._apply_sort()
            self._refresh_list()
            self.status.set(f"{len(self.files)}개 파일 준비됨")

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

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for f in self.files:
            self.listbox.insert(tk.END, f.name)

    def _remove_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        for i in reversed(sel):
            del self.files[i]
        self._refresh_list()
        self.status.set(f"{len(self.files)}개 파일 준비됨" if self.files else "파일을 추가해 주세요")

    def _clear_files(self):
        self.files.clear()
        self._refresh_list()
        self.status.set("파일을 추가해 주세요")

    # ── 변환 ──

    def _start_convert(self):
        if self._busy:
            return
        if not self.files:
            messagebox.showinfo("알림", "변환할 파일을 추가해 주세요.")
            return
        if not check_hwp_installed():
            messagebox.showerror("오류", "한컴오피스(한글)가 설치되어 있지 않습니다.")
            return

        out = self.output_dir.get().strip()
        if not out:
            messagebox.showinfo("알림", "저장 위치를 선택해 주세요.")
            return

        self._busy = True
        self.convert_btn.configure(state="disabled", text="변환 중...", bg=ACCENT_DISABLED)
        self.progress.pack(fill="x", padx=24, pady=(0, 4))
        self.progress["maximum"] = len(self.files)
        self.progress["value"] = 0
        self.status.set("한글 프로그램 준비 중... (파일당 시간이 걸릴 수 있습니다)")

        mode = self.mode.get()
        files_copy = list(self.files)
        out_dir = out
        quality_key = self.settings.get("pdf_quality", "high")
        picture_quality = get_picture_quality(quality_key)

        def run():
            try:
                def prog(cur, total, msg):
                    self.after(0, lambda: self._update_progress(cur, total, msg))

                results = convert_files(
                    files_copy, out_dir, mode=mode,
                    picture_quality=picture_quality, progress_cb=prog,
                )
                self.after(0, lambda: self._on_done(results, None))
            except Exception as exc:
                self.after(0, lambda: self._on_done(None, exc))

        threading.Thread(target=run, daemon=True).start()

    def _update_progress(self, cur, total, msg):
        self.progress["value"] = cur
        self.status.set(msg)

    def _on_done(self, results, error):
        self._busy = False
        self.convert_btn.configure(state="normal", text="PDF 변환", bg=ACCENT, activebackground=ACCENT_HOVER)
        self.progress.pack_forget()

        if error:
            self.status.set("변환 실패")
            messagebox.showerror("변환 오류", str(error))
            return

        count = len(results)
        out = self.output_dir.get()
        self.status.set(f"완료! {count}개 PDF 생성됨")
        if count == 1:
            msg = f"저장됨:\n{results[0]}"
        else:
            msg = f"{count}개 PDF가 저장되었습니다.\n\n위치: {out}"
        messagebox.showinfo("변환 완료", msg)


def main():
    hide_console_window()
    app = HanToPdfApp()
    app.mainloop()


if __name__ == "__main__":
    main()
