"""GitHub 자동 업데이트 저장소 설정."""

from __future__ import annotations

import os

# GitHub 저장소 (예: "사용자명/HanToPdf")
GITHUB_REPO = os.environ.get("HANTOPDF_GITHUB_REPO", "furss123/HanToPdf")

# version.json · ZIP 이 있는 브랜치
GITHUB_BRANCH = os.environ.get("HANTOPDF_GITHUB_BRANCH", "main")

# 저장소 내 릴리스 폴더
RELEASES_DIR = "releases"
VERSION_FILE = f"{RELEASES_DIR}/version.json"

# GitHub API / raw URL 이 실패할 때만 사용하는 manifest 주소
FALLBACK_MANIFEST_URL = os.environ.get(
    "HANTOPDF_UPDATE_URL",
    f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{VERSION_FILE}",
)
