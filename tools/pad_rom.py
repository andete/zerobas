#!/usr/bin/env python3
"""Pad (or verify) a raw ROM image to an exact size, filling with $FF.

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
        data += b"\xff" * (size - len(data))
        with open(path, "wb") as f:
            f.write(data)
    print(f"{path}: {size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
