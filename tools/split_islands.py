#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Split pasmo's full BASIC image into the relocated BASIC ($2812-$7FFF) and the
ISLANDS blob ($0000-$2811) -- lever B of "MAKING ROOM IN MAIN" (TODO.md; Joost,
2026-09-25: "B first, then A").

WHY. `basic/main.asm` may place code in C-BIOS's own alignment padding (islands
below $2812, e.g. `org $1ACF` before the font pinned at $1BBF). pasmo `--bin`
emits ONE image from the lowest address used to the highest, zero-filling the
gap -- so with an island the image no longer starts at $2812, and every consumer
that assumes it does (build_mainrom.py, the wall readouts, check_reloc, the
mappers) would silently read shifted bytes. The image always ENDS at $7FFF, so
its base is 0x8000 - len; this cuts it back into the two shapes those consumers
already expect and never touches them.

usage: split_islands.py <full.bin> <out basic-reloc.rom> <out islands.bin>
  islands.bin is always exactly $2812 bytes ($0000-$2811), zero where no island
  is; build_mainrom.py overlays its NON-ZERO bytes, refusing any outside the
  approved ranges or onto a non-zero C-BIOS byte.
"""
import sys

BASIC_BASE, TOP = 0x2812, 0x8000


def split(full: bytes):
    base = TOP - len(full)
    if base > BASIC_BASE:
        sys.exit(f"split_islands: image base ${base:04X} is ABOVE ${BASIC_BASE:04X} -- "
                 f"the image does not cover the relocated BASIC region")
    if base < 0:
        sys.exit(f"split_islands: image longer than 32 KB ({len(full)} B)")
    reloc = full[BASIC_BASE - base:]
    islands = bytes(base) + full[:BASIC_BASE - base]
    assert len(reloc) == TOP - BASIC_BASE and len(islands) == BASIC_BASE
    return reloc, islands


def main() -> int:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    full = open(sys.argv[1], "rb").read()
    reloc, islands = split(full)
    open(sys.argv[2], "wb").write(reloc)
    open(sys.argv[3], "wb").write(islands)
    used = sum(1 for b in islands if b)
    print(f"split_islands: base ${TOP - len(full):04X}; basic-reloc {len(reloc)} B; "
          f"islands {used} non-zero B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
