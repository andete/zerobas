#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Verify the relocated BASIC image (cbios-repack arc, WS-2 / S3).

The relocated variant (basic/main-reloc.asm, ROM_BASE=$2812) must:
  1. span $2812-$7FFF exactly (22510 bytes),
  2. keep the "AB" cartridge header pinned at $4000 (C-BIOS boots via the page-1
     cartridge scan; page 0 is never scanned),
  3. leave the reclaimed low region $2812-$3FFF reserved ($00) for now, and
  4. carry a page-1 body ($4000-$7FFF) byte-identical to the shipping basic.rom
     (proving the relocation changed no interpreter bytes — everything is
     label-based, per docs/cbios-repack-ws2-audit.md).

This is a proof gate for the assemble-clean landing, not a shipping check.

    python3 tools/check_reloc.py build/basic-reloc.rom build/basic.rom
"""
from __future__ import annotations

import sys

LOW = 0x2812
HDR = 0x4000
TOP = 0x8000
SIZE = TOP - LOW  # 22510


def main() -> int:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    reloc = open(sys.argv[1], "rb").read()
    ship = open(sys.argv[2], "rb").read()
    off = HDR - LOW  # header offset within the relocated image
    errs = []
    if len(reloc) != SIZE:
        errs.append(f"size {len(reloc)} != {SIZE} ($2812-$7FFF)")
    if reloc[off:off + 2] != b"AB":
        errs.append(f'"AB" header not at $4000 (offset {off:#x}): {reloc[off:off+2]!r}')
    if set(reloc[:off]) not in ({0}, set()):
        errs.append("reclaimed low region $2812-$3FFF is not all $00")
    if len(ship) != HDR:
        errs.append(f"shipping basic.rom size {len(ship)} != 16384")
    elif reloc[off:off + HDR] != ship:
        errs.append("page-1 body differs from shipping basic.rom")
    if errs:
        for e in errs:
            print("FAIL:", e, file=sys.stderr)
        return 1
    print(f"OK: relocated image {len(reloc)} B, header @ $4000, "
          f"low region $2812-$3FFF reserved, page-1 body == shipping basic.rom")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
