"""ZIP / exe 안의 버전 문자열 확인."""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "releases/HanToPdf-1.0.6.zip")
    with zipfile.ZipFile(path) as zf:
        data = zf.read("HanToPdf.exe")
    versions = sorted(set(re.findall(rb"1\.0\.\d+", data)))
    print(path.name, "->", [v.decode() for v in versions])


if __name__ == "__main__":
    main()
