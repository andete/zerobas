#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Measure disk.rom's free space — the wall readout the disk ROM never had.

`make basic-reloc` prints four walls (main low region, main page 1, sub page 0,
sub page 1) and this project's standing rule is to RUN it rather than quote a
remembered figure. `build/disk.rom` had no such readout at all, and the cost of
that showed immediately: asked whether the disk verbs could move into it, the
first answer was "no room -- a 2-byte trailing free run", from an ad-hoc
TRAILING scan that cannot see interior holes. The real figure is ~9 KB.
docs/spec-basic-nodisk.md §5.1.

WHY A RAW BYTE COUNT IS NOT THE ANSWER EITHER. This is a provider ROM with 68
PINNED entry addresses, each reached by `ds $XXXX - $, $00` padding, so most of
the $00 fill is the gap BEFORE the next pinned entry. A hole is only usable up
to that pin -- placing 3 KB in a 200 B gap does not fail here, it fails in
pasmo with a negative `ds` count (which, per tools/pad_rom.py, makes pasmo write
NOTHING and exit 0). So the guardable figure is per-hole "room before the next
pin", and that is what this prints.

⚠️ THIS IS A READOUT, NOT A NEW GUARD. Overrun is ALREADY caught: a negative
`ds` yields an empty image and `pad_rom.py` refuses it. What was missing is the
NUMBER -- so a slice can be priced, and so the figure comes from a tool instead
of from someone's memory.

🔴 IT REFUSES A DEGENERATE INPUT rather than printing a plausible table: no ROM,
the wrong size, or zero pins parsed all exit 2. An instrument that answers from
an input it misread is the failure this tree keeps filing.
"""
from __future__ import annotations

import glob
import os
import re
import sys

ROM_SIZE = 16384
BASE = 0x4000                       # disk.rom is mapped at $4000
PIN_RE = re.compile(r'\bds\s+\$([0-9A-Fa-f]{4})\s*-\s*\$')


def pins(src_dir: str) -> list[int]:
    found = set()
    for f in sorted(glob.glob(os.path.join(src_dir, "*.asm"))):
        for line in open(f, errors="replace"):
            code = line.split(";", 1)[0]        # a pin in a COMMENT is prose
            for m in PIN_RE.finditer(code):
                found.add(int(m.group(1), 16))
    return sorted(found)


def runs(b: bytes, fill: int, minlen: int):
    out, i = [], 0
    while i < len(b):
        if b[i] == fill:
            j = i
            while j < len(b) and b[j] == fill:
                j += 1
            if j - i >= minlen:
                out.append((i, j - i))
            i = j
        else:
            i += 1
    return out


def main() -> int:
    rom = sys.argv[1] if len(sys.argv) > 1 else "build/disk.rom"
    minlen = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    if not os.path.isfile(rom):
        print(f"REFUSED: no such ROM: {rom}  (build it: make disk)")
        return 2
    b = open(rom, "rb").read()
    if len(b) != ROM_SIZE:
        print(f"REFUSED: {rom} is {len(b)} B, expected {ROM_SIZE} "
              "-- nothing measured (see tools/pad_rom.py)")
        return 2
    p = pins("disk")
    if not p:
        print("REFUSED: parsed ZERO pinned addresses from disk/*.asm -- the "
              "`ds $XXXX - $` form must have changed; the free figures below "
              "would be meaningless, so none are printed")
        return 2

    free = runs(b, 0x00, minlen)
    total = sum(n for _, n in free)
    print(f"OK: disk ROM {len(b)} B, mapped ${BASE:04X}-${BASE + len(b) - 1:04X}, "
          f"{len(p)} pinned entry address(es) parsed from disk/*.asm")
    print(f"    measure: disk free (0x00 runs >= {minlen} B) = {total} B "
          f"in {len(free)} run(s)")
    # per-hole: how much can actually be placed there before the next pin
    rows = []
    for off, n in free:
        start = BASE + off
        end = start + n
        nxt = min((a for a in p if a >= end), default=BASE + ROM_SIZE)
        rows.append((n, start, end, nxt, nxt - start))
    rows.sort(reverse=True)
    print(f"    the 6 largest, with the pin that bounds each:")
    for n, start, end, nxt, room in rows[:6]:
        print(f"      ${start:04X}-${end - 1:04X}  {n:5d} B fill   "
              f"next pin ${nxt:04X}   room-before-pin {room} B")
    big = rows[0]
    print(f"    measure: largest usable hole = {big[0]} B at ${big[1]:04X} "
          f"(bounded by ${big[3]:04X})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
