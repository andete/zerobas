#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Pad (or verify) a raw ROM image to an exact size, filling with $00.

$00 matches empty C-BIOS page 1, keeping the slot-0 page-1 patch minimal (see
build_patches.py). main.asm already pads with `ds`, so this is normally a no-op
size check.

Usage: pad_rom.py <rom> <size>
"""
import sys


def main() -> int:
    path, size = sys.argv[1], int(sys.argv[2])
    with open(path, "rb") as f:
        data = f.read()
    if len(data) > size:
        print(f"{path}: {len(data)} bytes exceeds target {size}", file=sys.stderr)
        return 1
    if len(data) < size:
        data += b"\x00" * (size - len(data))
        with open(path, "wb") as f:
            f.write(data)
    print(f"{path}: {size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
