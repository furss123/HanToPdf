"""앱 설정 저장/불러오기"""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS = {
    "sort_order": "asc",
    "pdf_quality": "high",
}

VALID_PDF_QUALITY = ("original", "high", "medium", "low")

SORT_OPTIONS = {
    "none": "정렬 안 함",
    "asc": "이름 오름차순",
    "desc": "이름 내림차순",
}

CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "HanToPdf"
CONFIG_PATH = CONFIG_DIR / "config.json"


def load_settings() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULTS)

    merged = dict(DEFAULTS)
    for key in DEFAULTS:
        if key in data:
            merged[key] = data[key]
    if merged["sort_order"] not in SORT_OPTIONS:
        merged["sort_order"] = DEFAULTS["sort_order"]
    if merged["pdf_quality"] not in VALID_PDF_QUALITY:
        merged["pdf_quality"] = DEFAULTS["pdf_quality"]
    return merged


def save_settings(settings: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {key: settings.get(key, DEFAULTS[key]) for key in DEFAULTS}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
