#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DISJOINT scout -- is Joost's option (c) affordable, and WHERE does it go?

Joost ruled (c) on 2026-09-23: **make the two ROMs' RAM maps DISJOINT**, after a
Fable-agent measurement showed that is what the reference does (its directory/raw
sector buffer and its file-data sector buffer never write each other's range, and
each channel's live bytes sit in a per-channel record buffer besides).

🔴 THE QUESTION THIS ANSWERS IS THE ONE THE ITEM FLAGGED AS UNMEASURED: whether
there is anywhere for disk's buffers to GO. Today three things sit inside main's
`FSECTOR_BUF` ($E5C0..$E7BF): the top 416 B of disk's `WBUF`, and ~23 disk cells
in the top 96 B. Disk's `SECTOR_BUF` ($E2A0..$E49F) sits on main's live cells too
(spec-diskcode-eviction.md §6.6q names six of them).

🎯 SO THE COMPUTATION IS THE UNION, NOT EITHER MAP. `tools/ram_map.py` already
warns that a gap in ONE component's map is full of the other's cells it cannot
see -- it says so in its own output. This walks both components' declared cells
and reports spans free in BOTH.

⚠️ A FREE SPAN HERE IS A CANDIDATE, NOT A GUARANTEE, and for two reasons the tool
states about itself: width coverage is ~92% (basic) / ~88% (disk), and a cell
addressed only as an offset in code has no `equ` at all and is invisible. So a
span this reports as free must still be confirmed against the machine before
anything is moved into it. [[a-claim-about-empty-space-read-as-a-cells-extent]]

⚠️ AND IT REUSES `ram_map.py`'s PARSE rather than re-reading the sources. A second
parser would agree with its own mistakes, and this project has already paid for
re-implementing a syntax another tool owns.

    python3 scratchpad/disjoint_scout.py [--selftest] [--min N]
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ram_map  # noqa: E402

LO, HI = 0xE000, 0xF380
# What has to find a new home for (c), from docs/ram-map.md and §6.6q.
MOVERS = [("disk WBUF", 0xE560, 512), ("disk SECTOR_BUF", 0xE2A0, 512)]


def occupancy(maps):
    """{addr: set(component)} for every byte a component's declared cells cover."""
    occ: dict[int, set] = {}
    for comp, m in maps.items():
        for a, w in m.width.items():
            for b in range(a, min(a + w, HI)):
                occ.setdefault(b, set()).add(comp)
    return occ


def free_spans(occ, lo=LO, hi=HI, comps=("basic", "disk")):
    """[(start, length)] of maximal runs no component in `comps` declares."""
    out, start = [], None
    for a in range(lo, hi):
        taken = occ.get(a, set()) & set(comps)
        if taken and start is not None:
            out.append((start, a - start))
            start = None
        elif not taken and start is None:
            start = a
    if start is not None:
        out.append((start, hi - start))
    return out


def selftest():
    fails = 0

    def arm(label, cond):
        nonlocal fails
        if not cond:
            print(f"  selftest: FAIL {label}")
            fails += 1

    occ = {0xE000: {"basic"}, 0xE001: {"disk"}, 0xE005: {"basic", "disk"}}
    sp = free_spans(occ, 0xE000, 0xE008)
    arm("a run between two owned bytes is found", (0xE002, 3) in sp)
    # NEGATIVE: a byte owned by EITHER component is not free. Without this the
    # scout would report disk's own buffers as free space to move them into.
    arm("NEGATIVE: a byte owned by basic alone is not free",
        all(not (s <= 0xE000 < s + n) for s, n in sp))
    arm("NEGATIVE: a byte owned by disk alone is not free",
        all(not (s <= 0xE001 < s + n) for s, n in sp))
    arm("a trailing run reaches the window top", (0xE006, 2) in sp)
    # NEGATIVE: an empty occupancy is one span, not many -- a scout that
    # fragmented would under-report the largest hole, which is the answer.
    arm("NEGATIVE: nothing owned -> exactly one span",
        free_spans({}, 0xE000, 0xE010) == [(0xE000, 16)])
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def main(argv):
    print("D-DISJOINT: is option (c) affordable? spans free in BOTH maps\n")
    if "--selftest" in argv:
        return 1 if selftest() else 0
    minsz = 32
    if "--min" in argv:
        minsz = int(argv[argv.index("--min") + 1])
    # 🔴 THE QUESTION THAT MATTERS IS "FREE OF *MAIN*", NOT "FREE OF BOTH".
    # disk's buffers only have to stop overlapping MAIN's map -- disk's own
    # cells are ours to rearrange, so counting them as occupied asks a stricter
    # question than (c) actually poses and under-reports the room by a lot.
    avoid = ("basic",) if "--avoid-main-only" in argv else ("basic", "disk")
    maps = {c: ram_map.Map(c, LO, HI) for c in ("basic", "disk")}
    occ = occupancy(maps)
    print(f"  (treating as occupied: {', '.join(avoid)})")
    spans = [(s, n) for s, n in free_spans(occ, comps=avoid) if n >= minsz]
    spans.sort(key=lambda t: -t[1])
    total = sum(n for _, n in spans)
    print(f"  spans >= {minsz} B free in BOTH components, in [{LO:04X},{HI:04X}):")
    for s, n in spans:
        print(f"    {n:5d} B  ${s:04X}..${s + n - 1:04X}")
    print(f"  ---- {len(spans)} span(s), {total} B total\n")
    for name, addr, w in MOVERS:
        fits = [f"${s:04X}" for s, n in spans if n >= w]
        print(f"  {name} ({w} B, now ${addr:04X}): "
              + (f"{len(fits)} span(s) big enough: {', '.join(fits[:4])}"
                 if fits else "🔴 NO single free span is big enough"))
    print("\n⚠️  A span here is a CANDIDATE. Width coverage is ~92%/88% and a "
          "cell addressed\n   only as a code offset has no `equ` at all, so "
          "confirm against the machine\n   before moving anything in.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
