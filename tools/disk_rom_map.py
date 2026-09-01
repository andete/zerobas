#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""disk_rom_map — where the disk ROM's free space actually is.

🔴 WHY (2026-09-01). The disk ROM is a PINNED-ADDRESS layout: it is a Tier-2
provider ROM whose entry points must land on observed canonical addresses, so
`disk/*.asm` is full of `ds $XXXX - $, $00` pads that carry each region up to the
next pinned entry. The space between them is real and usable -- but the only way
to find it was to diff the built image by hand, and that produced two wrong
answers in one session:

  * "the tail has 3464 B free"  -- the TAIL has **2 B**; the big run is interior.
  * "space is not the obstacle" -- it is not, but you cannot APPEND, and three
    attempts to add 25 bytes drove a pad's `ds` count NEGATIVE and ran pasmo
    past 64 KB.

🎯 THE FIX IS A MAP, NOT A NUMBER IN A DOC. Figures rot; this reads the built ROM
every time. To USE a hole, put the code immediately BEFORE the `ds` that creates
it -- the pad shrinks by exactly what you add and every pinned address downstream
stays put.

⚠️ STATED LIMIT: a pad is measured as the run of $00 ending at the pinned target,
so a preceding body whose last bytes are genuinely $00 inflates its figure. The
number is an UPPER BOUND on free space, and the accounting line below is the
check that keeps it honest.

    python3 tools/disk_rom_map.py [--rom build/disk.rom]
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 0x4000
PAD = re.compile(r"^\s+ds\s+\$([0-9A-Fa-f]{4})\s*-\s*\$", re.M)
MIN_PADS = 10          # a parse finding fewer than this is broken, not a finding


def pads() -> list[tuple[str, int, int]]:
    """[(file:line, target address, source order), ...] for every fixed-address pad."""
    out = []
    for rel in ("init.asm", "pageenv.asm", "driver.asm", "fat.asm",
                "kernel.asm", "runtime.asm"):          # disk.asm's include order
        p = os.path.join(ROOT, "disk", rel)
        if not os.path.exists(p):
            continue
        for n, line in enumerate(open(p), 1):
            m = PAD.match(line)
            if m:
                out.append((f"disk/{rel}:{n}", int(m.group(1), 16), len(out)))
    return out


def run_before(rom: bytes, addr: int) -> int:
    """Length of the $00 run ending immediately before `addr`."""
    i = addr - BASE - 1
    n = 0
    while i >= 0 and rom[i] == 0:
        n += 1
        i -= 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", default=os.path.join(ROOT, "build", "disk.rom"))
    a = ap.parse_args()
    if not os.path.exists(a.rom):
        print(f"INSTRUMENT: {a.rom} is not built — nothing measured. `make disk`.")
        return 2
    rom = open(a.rom, "rb").read()
    ps = pads()
    if len(ps) < MIN_PADS:
        print(f"INSTRUMENT: parsed {len(ps)} fixed-address pad(s); floor is "
              f"{MIN_PADS}. The scan broke — nothing measured.")
        return 2

    rows = [(where, tgt, run_before(rom, tgt)) for where, tgt, _ in ps]
    rows.sort(key=lambda r: -r[2])
    print(f"disk ROM map — {len(rom)} B at ${BASE:04X}, {len(ps)} fixed-address pad(s)\n")
    print(f"  {'free':>6}  {'ends at':>8}  where the pad is written")
    for where, tgt, n in rows:
        if n >= 16:
            print(f"  {n:6}  ${tgt:04X}     {where}")
    small = sum(n for _, _, n in rows if n < 16)
    print(f"\n  (+{small} B in pads smaller than 16 B, across "
          f"{sum(1 for _, _, n in rows if n < 16)} pad(s))")

    last = max(i for i, b in enumerate(rom) if b != 0)
    print(f"\n  APPENDABLE TAIL: {len(rom) - 1 - last} B "
          f"(image ends at ${BASE + last:04X}) — this is what you do NOT have.")
    total = sum(n for _, _, n in rows)
    print(f"  total in pads : {total} B of {len(rom)} "
          f"({100.0 * total / len(rom):.1f}%)")
    print("\n  To use a hole: put the code immediately BEFORE the `ds` that makes "
          "it.\n  The pad shrinks by what you add; every pinned address after it "
          "stays put.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
