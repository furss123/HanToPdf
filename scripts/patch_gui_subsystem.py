"""PyInstaller release runw.exe bootloader가 CUI(3) 서브시스템인 경우 GUI(2)로 패치."""

from __future__ import annotations

import struct
import sys

IMAGE_SUBSYSTEM_WINDOWS_GUI = 2


def _subsystem_offset(data: bytes) -> int:
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    magic = struct.unpack_from("<H", data, pe_off + 24)[0]
    if magic not in (0x10B, 0x20B):
        raise ValueError(f"Unknown PE optional header magic: {hex(magic)}")
    return pe_off + 24 + 68


def read_subsystem(exe_path: str) -> int:
    with open(exe_path, "rb") as f:
        data = f.read()
    return struct.unpack_from("<H", data, _subsystem_offset(data))[0]


def patch_to_gui(exe_path: str) -> int:
    """PE 서브시스템을 WINDOWS_GUI로 설정. 이전 값을 반환."""
    with open(exe_path, "rb") as f:
        data = bytearray(f.read())
    off = _subsystem_offset(data)
    old = struct.unpack_from("<H", data, off)[0]
    if old != IMAGE_SUBSYSTEM_WINDOWS_GUI:
        struct.pack_into("<H", data, off, IMAGE_SUBSYSTEM_WINDOWS_GUI)
        with open(exe_path, "wb") as f:
            f.write(data)

    try:
        from PyInstaller.utils.win32 import winutils

        winutils.update_exe_pe_checksum(exe_path)
    except Exception:
        pass

    return old


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: patch_gui_subsystem.py <exe>", file=sys.stderr)
        return 2
    path = sys.argv[1]
    old = read_subsystem(path)
    if old == IMAGE_SUBSYSTEM_WINDOWS_GUI:
        print(old)
        return 0
    if old != 3:
        print(f"unexpected subsystem: {old}", file=sys.stderr)
        return 1
    patched = patch_to_gui(path)
    new = read_subsystem(path)
    if new != IMAGE_SUBSYSTEM_WINDOWS_GUI:
        print(f"patch failed: still subsystem {new}", file=sys.stderr)
        return 1
    print(f"{patched} -> {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
