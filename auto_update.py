"""HanToPdf 자동 업데이트 (Windows onedir 배포용)."""

from __future__ import annotations

import hashlib
import json
import os
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import messagebox, ttk

from ui_theme import (
    ACCENT,
    BG,
    CARD,
    FONT_BODY,
    FONT_DESC,
    FONT_SECTION,
    TEXT,
    TEXT_SEC,
    LoadingSpinner,
    app_button,
    section_card,
)
from update_config import (
    FALLBACK_MANIFEST_URL,
    GITHUB_BRANCH,
    GITHUB_REPO,
    RELEASES_DIR,
    VERSION_FILE,
)
from version import __version__

_FETCH_TIMEOUT = 12
_DOWNLOAD_TIMEOUT = 300
_USER_AGENT = f"HanToPdf/{__version__}"
_URL_RETRIES = 3

# 전체 진행률 구간
_PCT_START = 3
_PCT_DOWNLOAD_END = 88
_PCT_VERIFY_END = 94
_PCT_APPLY = 100
_SNOOZE_DAYS = 7
_SNOOZE_SECONDS = _SNOOZE_DAYS * 24 * 60 * 60


def _snooze_path() -> Path:
    base = Path(os.environ.get("APPDATA", str(Path.home())))
    return base / "HanToPdf" / "update_snooze.json"


def _is_update_snoozed() -> bool:
    path = _snooze_path()
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return time.time() < float(data.get("until", 0))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def _snooze_update_prompt() -> None:
    path = _snooze_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"until": time.time() + _SNOOZE_SECONDS}
    path.write_text(json.dumps(payload), encoding="utf-8")


def schedule_update_check(root: tk.Misc) -> None:
    """앱 시작 후 백그라운드에서 업데이트 확인 (exe 배포본만)."""
    if not getattr(sys, "frozen", False):
        return
    if os.environ.get("HANTOPDF_SKIP_UPDATE") == "1":
        return
    try:
        from update_apply import cleanup_legacy_update_artifacts

        cleanup_legacy_update_artifacts()
    except Exception:
        pass
    try:
        from av_trust import ensure_update_paths_trusted

        ensure_update_paths_trusted(_install_dir())
    except Exception:
        pass
    threading.Thread(target=_check_worker, args=(root,), name="UpdateCheck", daemon=True).start()


def _parse_version(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in value.strip().lstrip("vV").split("."):
        digits = ""
        for ch in piece:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts) if parts else (0,)


def _is_newer(remote: str, local: str) -> bool:
    return _parse_version(remote) > _parse_version(local)


def _install_dir() -> Path:
    return Path(sys.executable).resolve().parent


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    try:
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    except ssl.SSLError:
        pass
    return ctx


_SSL_CTX = _ssl_context()


def _is_retriable_url_error(exc: BaseException) -> bool:
    reason = getattr(exc, "reason", exc)
    msg = str(reason).lower()
    return any(
        token in msg
        for token in (
            "unexpected_eof",
            "eof occurred",
            "timed out",
            "10054",
            "connection reset",
            "connection aborted",
            "certificate verify failed",
        )
    )


def _urlopen(req: urllib.request.Request, timeout: float, *, retries: int = _URL_RETRIES):
    last_exc: BaseException | None = None
    for attempt in range(retries):
        try:
            return urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX)
        except urllib.error.URLError as exc:
            last_exc = exc
            if attempt + 1 < retries and _is_retriable_url_error(exc):
                time.sleep(0.6 * (attempt + 1))
                continue
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("urlopen failed")


def _release_tag(version: str) -> str:
    version = version.strip()
    return version if version.startswith(("v", "V")) else f"v{version}"


def _release_zip_url(repo: str, version: str, filename: str) -> str:
    name = Path(filename).name
    return f"https://github.com/{repo}/releases/download/{_release_tag(version)}/{name}"


def _prefer_release_zip_url(repo: str, version: str, download_url: str) -> str:
    """대용량 ZIP은 raw.githubusercontent.com 대신 GitHub Releases CDN 사용."""
    if not version or not download_url.lower().endswith(".zip"):
        return download_url
    filename = download_url.rsplit("/", 1)[-1]
    if "raw.githubusercontent.com" in download_url and f"/{RELEASES_DIR}/" in download_url:
        return _release_zip_url(repo, version, filename)
    if download_url.startswith(f"https://github.com/{repo}/releases/download/"):
        return download_url
    return download_url


def _download_url_candidates(repo: str, version: str, download_url: str) -> list[str]:
    primary = _prefer_release_zip_url(repo, version, download_url)
    candidates = [primary]
    if primary != download_url:
        candidates.append(download_url)
    if primary.startswith(f"https://github.com/{repo}/releases/download/"):
        raw_name = primary.rsplit("/", 1)[-1]
        raw = _raw_github_url(repo, GITHUB_BRANCH.strip(), f"{RELEASES_DIR}/{raw_name}")
        if raw not in candidates:
            candidates.append(raw)
    return candidates


def _map_download_pct(download_pct: int) -> int:
    span = _PCT_DOWNLOAD_END - _PCT_START
    return _PCT_START + int(download_pct * span / 100)


def _github_api_headers() -> dict[str, str]:
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "application/vnd.github+json",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _raw_github_url(repo: str, branch: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{path.lstrip('/')}"


def _fetch_github_contents_json(repo: str, path: str, branch: str) -> dict | None:
    """GitHub 저장소 파일 — 업로드 직후 최신 내용 반영."""
    encoded = urllib.parse.quote(path, safe="/")
    url = f"https://api.github.com/repos/{repo}/contents/{encoded}?ref={urllib.parse.quote(branch)}"
    try:
        req = urllib.request.Request(url, headers=_github_api_headers())
        with _urlopen(req, _FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not isinstance(data, dict) or data.get("encoding") != "base64":
            return None
        import base64

        raw = base64.b64decode(data["content"]).decode("utf-8-sig")
        payload = json.loads(raw)
        return payload if isinstance(payload, dict) else None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        return None


def _fetch_github_latest_release(repo: str) -> dict | None:
    """GitHub Releases 에 ZIP 을 올린 경우."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        req = urllib.request.Request(url, headers=_github_api_headers())
        with _urlopen(req, _FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not isinstance(data, dict) or data.get("draft"):
            return None
        tag = str(data.get("tag_name", "")).strip().lstrip("vV")
        assets = data.get("assets") or []
        zip_url = ""
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name", "")).lower()
            if name.endswith(".zip"):
                zip_url = str(asset.get("browser_download_url", "")).strip()
                break
        if not tag or not zip_url:
            return None
        return {
            "version": tag,
            "download_url": zip_url,
            "sha256": "",
            "release_notes": str(data.get("body", "")).strip(),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        return None


def _normalize_manifest(manifest: dict, repo: str, branch: str) -> dict:
    """download_url 이 파일명만 있으면 GitHub raw 주소로 변환."""
    result = dict(manifest)
    version = str(result.get("version", "")).strip()
    download_url = str(result.get("download_url", "")).strip()
    if not download_url and version:
        download_url = f"HanToPdf-{version}.zip"
    if download_url and not download_url.startswith(("http://", "https://")):
        zip_name = download_url.rsplit("/", 1)[-1]
        if "/" not in download_url:
            download_url = f"{RELEASES_DIR}/{download_url}"
            zip_name = download_url.rsplit("/", 1)[-1]
        if zip_name.lower().endswith(".zip") and version:
            download_url = _release_zip_url(repo, version, zip_name)
        else:
            download_url = _raw_github_url(repo, branch, download_url)
    elif version:
        download_url = _prefer_release_zip_url(repo, version, download_url)
    result["download_url"] = download_url
    return result


def _fetch_update_manifest() -> dict | None:
    """GitHub releases/version.json → Releases → fallback 순으로 확인."""
    repo = GITHUB_REPO.strip()
    branch = GITHUB_BRANCH.strip()
    if repo:
        manifest = _fetch_github_contents_json(repo, VERSION_FILE, branch)
        if manifest:
            return _normalize_manifest(manifest, repo, branch)
        manifest = _fetch_github_latest_release(repo)
        if manifest:
            return manifest
        try:
            return _normalize_manifest(
                _fetch_json(_raw_github_url(repo, branch, VERSION_FILE)),
                repo,
                branch,
            )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
            pass
    try:
        payload = _fetch_json(FALLBACK_MANIFEST_URL)
        if repo:
            return _normalize_manifest(payload, repo, branch)
        return payload
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        return None


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with _urlopen(req, _FETCH_TIMEOUT) as resp:
        data = resp.read()
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    return payload


def _download_file(
    url: str,
    dest: Path,
    progress_cb: Callable[[int], None] | None = None,
    *,
    version: str = "",
) -> None:
    repo = GITHUB_REPO.strip()
    urls = _download_url_candidates(repo, version, url) if repo and version else [url]
    last_exc: BaseException | None = None
    for candidate in urls:
        try:
            _download_file_once(candidate, dest, progress_cb)
            return
        except urllib.error.URLError as exc:
            last_exc = exc
            if dest.exists():
                try:
                    dest.unlink()
                except OSError:
                    pass
            continue
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("download failed")


def _download_file_once(
    url: str,
    dest: Path,
    progress_cb: Callable[[int], None] | None = None,
) -> None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "*/*",
        },
    )
    with _urlopen(req, _DOWNLOAD_TIMEOUT, retries=_URL_RETRIES) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        read = 0
        chunk_size = 256 * 1024
        last_report = _PCT_START
        pulse_at = time.monotonic()
        with dest.open("wb") as out:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                read += len(chunk)
                if not progress_cb:
                    continue
                if total > 0:
                    dl_pct = min(100, int(read * 100 / total))
                    overall = _map_download_pct(dl_pct)
                else:
                    now = time.monotonic()
                    if now - pulse_at >= 0.4:
                        pulse_at = now
                        last_report = min(_PCT_DOWNLOAD_END - 2, last_report + 2)
                    overall = last_report
                progress_cb(overall)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _check_worker(root: tk.Misc) -> None:
    try:
        if _is_update_snoozed():
            return
        manifest = _fetch_update_manifest()
        if not manifest:
            return
        remote_ver = str(manifest.get("version", "")).strip()
        download_url = str(manifest.get("download_url", "")).strip()
        if not remote_ver or not download_url:
            return
        if not _is_newer(remote_ver, __version__):
            return
        notes = str(manifest.get("release_notes", "")).strip()
        sha256 = str(manifest.get("sha256", "")).strip().lower()
        root.after(
            0,
            lambda: _prompt_update(root, remote_ver, download_url, notes, sha256),
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        return
    except Exception:
        return


def _prompt_update(
    root: tk.Misc,
    remote_ver: str,
    download_url: str,
    notes: str,
    sha256: str,
) -> None:
    if not root.winfo_exists():
        return
    choice = _UpdatePromptDialog.ask(
        root,
        remote_ver=remote_ver,
        notes=notes,
    )
    if choice == "update":
        _start_auto_update(root, remote_ver, download_url, notes, sha256)
    elif choice == "snooze":
        _snooze_update_prompt()


class _UpdatePromptDialog:
    """업데이트 확인 — 지금 업데이트 / 7일 동안 보지 않기 / 나중에."""

    @classmethod
    def ask(cls, parent: tk.Misc, *, remote_ver: str, notes: str) -> str:
        dlg = cls(parent, remote_ver=remote_ver, notes=notes)
        return dlg.result

    def __init__(self, parent: tk.Misc, *, remote_ver: str, notes: str):
        self.result = "later"
        self._top = tk.Toplevel(parent)
        self._top.title("업데이트")
        self._top.configure(bg=BG)
        self._top.transient(parent)
        self._top.resizable(False, False)
        self._top.grab_set()
        self._top.protocol("WM_DELETE_WINDOW", self._on_later)

        body = f"새 버전 {remote_ver} 이(가) 있습니다.\n현재 버전: {__version__}"
        if notes:
            body += f"\n\n{notes}"

        card = section_card(self._top)
        card.pack(fill="both", expand=True, padx=20, pady=20)
        tk.Label(
            card.body,
            text=body,
            font=FONT_BODY,
            bg=CARD,
            fg=TEXT,
            justify="left",
            wraplength=320,
        ).pack(fill="x", padx=20, pady=(20, 16))

        btn_row = tk.Frame(card.body, bg=CARD)
        btn_row.pack(fill="x", padx=20, pady=(0, 20))
        app_button(btn_row, "나중에", command=self._on_later, small=True).pack(side="right")
        app_button(
            btn_row,
            "7일 동안 보지 않기",
            command=self._on_snooze,
            small=True,
        ).pack(side="right", padx=(0, 8))
        app_button(
            btn_row,
            "지금 업데이트",
            command=self._on_update,
            accent=True,
        ).pack(side="right", padx=(0, 8))

        self._top.update_idletasks()
        w, h = self._top.winfo_reqwidth(), self._top.winfo_reqheight()
        px = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        py = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self._top.geometry(f"+{px}+{py}")
        parent.wait_window(self._top)

    def _close(self) -> None:
        try:
            self._top.grab_release()
            self._top.destroy()
        except tk.TclError:
            pass

    def _on_update(self) -> None:
        self.result = "update"
        self._close()

    def _on_snooze(self) -> None:
        self.result = "snooze"
        self._close()

    def _on_later(self) -> None:
        self.result = "later"
        self._close()


def _start_auto_update(
    root: tk.Misc,
    remote_ver: str,
    download_url: str,
    notes: str,
    sha256: str,
) -> None:
    if not root.winfo_exists():
        return
    overlay = _UpdateOverlay(root)
    title = f"버전 {remote_ver} 업데이트 중"
    detail = notes or f"{__version__} → {remote_ver}"
    overlay.show(title, detail)
    overlay.set_progress(_PCT_START)
    _run_update_flow(root, overlay, remote_ver, download_url, sha256)


def _run_update_flow(
    root: tk.Misc,
    overlay: _UpdateOverlay,
    remote_ver: str,
    download_url: str,
    sha256: str,
) -> None:
    def worker() -> None:
        zip_path: Path | None = None
        try:
            fd, raw = tempfile.mkstemp(prefix="hantopdf_update_", suffix=".zip")
            os.close(fd)
            zip_path = Path(raw)

            def on_progress(pct: int) -> None:
                root.after(0, lambda p=pct: overlay.set_progress(p))

            root.after(0, lambda: overlay.set_detail("업데이트 파일 다운로드 중…"))
            _download_file(download_url, zip_path, on_progress, version=remote_ver)
            root.after(0, lambda: overlay.set_progress(_PCT_DOWNLOAD_END))

            root.after(0, lambda: overlay.set_detail("다운로드 파일 검증 중…"))
            if sha256 and _sha256_file(zip_path) != sha256:
                raise ValueError("다운로드 파일 검증에 실패했습니다.")
            root.after(0, lambda: overlay.set_progress(_PCT_VERIFY_END))

            root.after(0, lambda: overlay.set_detail("업데이트 적용 중…"))
            pid = os.getpid()
            install = _install_dir()
            exe_path = install / "HanToPdf.exe"
            from av_trust import ensure_update_paths_trusted
            from update_apply import launch_apply_update

            ensure_update_paths_trusted(install, force=True)

            launch_apply_update(
                parent_pid=pid,
                install_dir=install,
                zip_path=zip_path,
                exe_path=exe_path,
            )
            root.after(0, lambda: overlay.set_progress(_PCT_APPLY))

            def exit_app() -> None:
                overlay.close()
                try:
                    root.quit()
                except tk.TclError:
                    pass
                try:
                    root.destroy()
                except tk.TclError:
                    pass
                sys.exit(0)

            root.after(400, exit_app)
        except Exception as exc:
            msg = str(exc) or "알 수 없는 오류"
            root.after(0, lambda: _show_update_error(root, overlay, msg, zip_path))

    threading.Thread(target=worker, name="UpdateDownload", daemon=True).start()


def _show_update_error(
    root: tk.Misc,
    overlay: _UpdateOverlay,
    message: str,
    zip_path: Path | None,
) -> None:
    overlay.close()
    if zip_path and zip_path.exists():
        try:
            zip_path.unlink()
        except OSError:
            pass
    if root.winfo_exists():
        messagebox.showerror(
            "업데이트 실패",
            "자동 업데이트를 완료하지 못했습니다.\n"
            "앱은 계속 사용할 수 있습니다.\n\n"
            f"{message}\n\n"
            f"자세한 내용: {_update_log_hint()}",
            parent=root,
        )


def _update_log_hint() -> str:
    from update_apply import _LOG_PATH

    return str(_LOG_PATH)


class _UpdateOverlay:
    """전체 화면 업데이트 오버레이 — 스피너 + 0~100% 진행 바."""

    def __init__(self, parent: tk.Misc):
        self._parent = parent
        self._visible = False
        self._dim = tk.Frame(parent, bg="#E5E7EB")
        self._title = tk.StringVar(value="업데이트 중")
        self._detail = tk.StringVar(value="")
        self._percent = tk.StringVar(value="0%")
        self._spinner: LoadingSpinner | None = None

        card = section_card(self._dim)
        card.place(relx=0.5, rely=0.5, anchor="center", width=340, height=190)

        head = tk.Frame(card.body, bg=CARD)
        head.pack(fill="x", padx=20, pady=(20, 8))
        self._spinner = LoadingSpinner(head, size=20, color=ACCENT, bg=CARD)
        self._spinner.pack(side="left", padx=(0, 10))
        tk.Label(
            head, textvariable=self._title, font=FONT_SECTION, bg=CARD, fg=TEXT, anchor="w",
        ).pack(side="left", fill="x", expand=True)

        tk.Label(
            card.body,
            textvariable=self._detail,
            font=FONT_DESC,
            bg=CARD,
            fg=TEXT_SEC,
            wraplength=300,
            justify="left",
        ).pack(fill="x", padx=20, pady=(0, 12))

        bar_row = tk.Frame(card.body, bg=CARD)
        bar_row.pack(fill="x", padx=20, pady=(0, 6))
        self._bar = ttk.Progressbar(
            bar_row,
            mode="determinate",
            maximum=100,
            length=260,
            style="App.Horizontal.TProgressbar",
        )
        self._bar.pack(side="left", fill="x", expand=True)
        tk.Label(
            bar_row,
            textvariable=self._percent,
            font=FONT_BODY,
            bg=CARD,
            fg=TEXT,
            width=5,
            anchor="e",
        ).pack(side="right", padx=(8, 0))

        tk.Label(
            card.body,
            text="잠시만 기다려 주세요. 완료되면 앱이 다시 시작됩니다.",
            font=FONT_DESC,
            bg=CARD,
            fg=TEXT_SEC,
        ).pack(padx=20, pady=(0, 18))

    def show(self, title: str, detail: str) -> None:
        self._title.set(title)
        self._detail.set(detail)
        self._percent.set("0%")
        self._bar["value"] = 0
        if self._visible:
            return
        self._visible = True
        self._dim.place(x=0, y=0, relwidth=1, relheight=1)
        self._dim.lift()
        if self._spinner is not None:
            self._spinner.start()

    def set_detail(self, text: str) -> None:
        self._detail.set(text)

    def set_progress(self, value: int) -> None:
        pct = max(0, min(100, int(value)))
        self._bar["value"] = pct
        self._percent.set(f"{pct}%")

    def close(self) -> None:
        if not self._visible:
            return
        self._visible = False
        if self._spinner is not None:
            self._spinner.stop()
        self._dim.place_forget()
