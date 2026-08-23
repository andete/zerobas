#!/usr/bin/env python3
"""Per-INCLUDE main-ROM sizes, split by region, from build/basic-reloc.sym.

The walls are COUPLED (basic/main.asm: "page 1 and the low region are co-mapped
slot-0 pages, so a pressure-placed leaf can be moved between them freely"), so
closing the DEF FN gap ends in a PROMOTION: move a page-1 block down into the
low region until `$ > $8000` stops firing. This says which blocks are the right
size to move.

The size of an include is (first label of the next include) - (its own first
label): the files are laid out contiguously in include order, so that is exact
for everything but the last one in each region.
"""
from __future__ import annotations
import re
import sys

MAIN = "basic/main.asm"
SYM = "build/basic-reloc.sym"


def sym_table():
    t = {}
    for line in open(SYM):
        m = re.match(r"^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H", line)
        if m:
            t[m.group(1)] = int(m.group(2), 16)
    return t


def first_label(path, syms):
    """The lowest-addressed label defined in this source file."""
    best = None
    for line in open(path):
        m = re.match(r"^([A-Za-z_]\w*):", line)
        if m and m.group(1) in syms:
            a = syms[m.group(1)]
            if best is None or a < best:
                best = a
    return best


def main():
    syms = sym_table()
    low_end, p1_end = syms["__MEAS_LOW_END"], syms["__MEAS_PAGE1_END"]
    rows = []
    for line in open(MAIN):
        m = re.match(r'^\s*include\s+"([^"]+)"', line)
        if not m:
            continue
        path = m.group(1)
        if not path.endswith(".asm"):
            continue
        a = first_label(path, syms)
        if a is None:
            continue
        rows.append((a, path))
    rows.sort()
    print(f"  __MEAS_LOW_END = ${low_end:04X} ({0x4000-low_end} B free)   "
          f"__MEAS_PAGE1_END = ${p1_end:04X} ({p1_end-0x8000:+d} vs the ceiling)")
    print(f"  {'start':>6}  {'size':>5}  region  file")
    for i, (a, path) in enumerate(rows):
        end = rows[i + 1][0] if i + 1 < len(rows) else (
            low_end if a < 0x4000 else p1_end)
        if a < 0x4000 <= end:
            end = low_end
        region = "low" if a < 0x4000 else "page1"
        print(f"  ${a:04X}  {end - a:5d}  {region:6}  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
