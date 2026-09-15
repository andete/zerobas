#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Which MAIN-IMAGE bytes are DISK-only or TAPE-only, and in which region?

🎚️ JOOST RULED 2026-09-15: *"disk code should be as much as possible in the disk
rom, and tape code is a good candidate for using the sub rom"*. This is the
measurement that ruling needs BEFORE a byte moves: main page 1 has single digits
of headroom while `disk.rom` has kilobytes, so a migration is worth far more than
any instruction-level shave -- but only if the spans really are disk- or
tape-only.

Method, and its limits said out loud:
  * every `label:` in `basic/*.asm` / `basic/*.inc` is mapped to its FILE, then
    to its address from `build/basic-reloc.sym`;
  * a symbol's SIZE is the gap to the next symbol by address. That is exact for
    the last symbol of a routine and an OVERESTIMATE for a label that merely
    marks a branch target inside one -- so per-FILE totals are right and
    per-LABEL ones are a guide, which is why the report totals by file;
  * the REGION split is the same boundary `basic-reloc` prints: below $4000 is
    the low region, $4000 and up is page 1. They share one budget.
  * `basic/*.inc` bodies included into BOTH the main image and a sub-ROM tenant
    are counted once per file, under the file that defines them.

It reports, not decides: a span being disk-only does not mean it can move (the
`diskrom-abi-check` / `subrom-closure-check` contracts decide that), and this
says nothing about callers in the other direction.
"""
import io
import os
import re
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYM = os.path.join(REPO, "build", "basic-reloc.sym")
PAGE1 = 0x4000

# What each file IS. Read from the includes in basic/main.asm and the file's own
# subject; the classification is the JUDGEMENT this scout makes and the reason it
# prints the file list rather than only the totals.
KIND = {
    "fat.asm": "disk", "bload.asm": "disk", "files.asm": "disk",
    "field.asm": "disk", "format.asm": "disk",
    "cload.asm": "tape",
    "save.asm": "disk+tape",
}


def symbols() -> dict:
    out = {}
    for line in io.open(SYM, errors="replace"):
        m = re.match(r"(\w+)\s+EQU\s+0?([0-9A-Fa-f]+)H", line)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out


def label_file() -> dict:
    """label -> the basic/ source file that defines it."""
    out = {}
    d = os.path.join(REPO, "basic")
    for fn in sorted(os.listdir(d)):
        if not fn.endswith((".asm", ".inc")):
            continue
        for line in io.open(os.path.join(d, fn), encoding="utf-8",
                            errors="replace"):
            m = re.match(r"^([A-Za-z_][\w]*):", line)
            if m:
                out.setdefault(m.group(1), fn)
    return out


def main() -> int:
    sym, owner = symbols(), label_file()
    known = sorted(((a, n) for n, a in sym.items() if n in owner),
                   key=lambda t: t[0])
    low = defaultdict(int)
    p1 = defaultdict(int)
    for i, (addr, name) in enumerate(known):
        nxt = known[i + 1][0] if i + 1 < len(known) else addr
        size = max(0, nxt - addr)
        if size > 4096:            # a gap across a region/section break
            continue
        (p1 if addr >= PAGE1 else low)[owner[name]] += size
    files = sorted(set(low) | set(p1),
                   key=lambda f: -(low[f] + p1[f]))
    print(f"{'file':28} {'kind':10} {'low':>7} {'page1':>7} {'total':>7}")
    print("-" * 64)
    tl = tp = 0
    for f in files:
        k = KIND.get(f, "")
        if not k:
            continue
        print(f"{f:28} {k:10} {low[f]:7} {p1[f]:7} {low[f] + p1[f]:7}")
        tl += low[f]
        tp += p1[f]
    print("-" * 64)
    print(f"{'DISK/TAPE TOTAL':28} {'':10} {tl:7} {tp:7} {tl + tp:7}")
    other_l = sum(v for f, v in low.items() if f not in KIND)
    other_p = sum(v for f, v in p1.items() if f not in KIND)
    print(f"{'everything else':28} {'':10} {other_l:7} {other_p:7} "
          f"{other_l + other_p:7}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
