#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BFBYTE round 4 -- the edges the fast path's CODE has to handle.

D-BFPERF pinned the rule (a fully covered cell row becomes pattern $00 with the
colour in the BACKGROUND nibble) on aligned, forward, colour-15/6 fills. The
implementation has to survive three cases that characterization never rowed,
and each one is a branch I would otherwise be writing on a guess:

  * REVERSED CORNERS -- gfx_box_stash does not sort, so the run splitter must.
  * COLOUR 0 -- the colour byte would become $00, indistinguishable from "not
    drawn". Does the fast path still engage?
  * AN 8-WIDE RUN THAT IS NOT BYTE-ALIGNED -- eight pixels, zero whole bytes.
    The fast path must NOT engage; a splitter that counts pixels instead of
    computing cell boundaries would get this wrong.

Capture is two cell ROWS (y 0..7 and y 8..15) across three cell COLUMNS, so a
fill taller than one cell is visible too.

    python3 -u scratchpad/bfperf_edges.py [--dry]
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                    "C-BIOS_MSX1_EU_REPACK_DISK")

# cell row 0 = $0000 (pattern) / $2000 (colour); cell row 1 = $0100 / $2100.
SEGS = [(0x0000, 24), (0x0100, 24), (0x2000, 24), (0x2100, 24)]

CASES = [
    ("dead_nofill", "",
     "⭐ DEAD SUBJECT: pattern all $00, colour all $04."),
    ("fwd_span", "LINE(3,0)-(20,0),15,BF",
     "the anchor, repeated from round 3: partial | FULL | partial."),
    ("rev_span", "LINE(20,0)-(3,0),15,BF",
     "⭐ THE SAME BOX, CORNERS REVERSED. gfx_box_stash copies without "
     "sorting, so if this matches fwd_span the splitter must sort too."),
    ("c0_full", "LINE(0,0)-(7,7),0,BF",
     "⭐ COLOUR 0 over a full cell: does the fast path still engage, leaving "
     "pattern $00 / colour $00? If instead it looks like the per-pixel path "
     "($00 pattern / $04 colour, background preserved) then colour 0 is "
     "special and the branch needs a guard."),
    ("unaligned8", "LINE(4,0)-(11,0),15,BF",
     "⭐ EIGHT pixels, ZERO whole bytes (x 4..11 straddles the cell edge). "
     "Both cells must take the per-pixel path: cell0 $0f, cell1 $f0."),
    ("tall_full", "LINE(0,0)-(15,15),15,BF",
     "⭐ two cells wide by TWO CELL ROWS tall, every byte fully covered -- "
     "the fast path across a cell-row boundary."),
    ("one_px", "LINE(5,3)-(5,3),15,BF",
     "CONTROL: a 1x1 fill. No whole byte, so per-pixel; pattern row 3 = $04."),
]


def fmt(b):
    return " ".join(b[i:i + 8].hex() for i in (0, 8, 16))


def main() -> int:
    print("=== D-BFBYTE round 4: the edges the fast path must handle ===")
    print("    cell row 0 = $0000/$2000, cell row 1 = $0100/$2100,"
          " three cell columns each\n")
    for lbl, ops, why in CASES:
        print(f"  {lbl:14} {ops or '(nothing)'}")
        print(f"      why: {why}")
    if "--dry" in sys.argv:
        return 0

    import omsx_repl

    def run(machine, ops):
        stmts = ["COLOR15,4,7:SCREEN2" + (":" + ops if ops else "")]
        return omsx_repl.run_cases(
            machine, [("stored", stmts + [f"GOTO {10 * (len(stmts) + 1)}"])],
            batch=False, capture=("vram_segs", SEGS), step=30.0)[0]

    def show(hexs):
        if not hexs or len(hexs) != 192:
            return None
        b = bytes.fromhex(hexs)
        return dict(p0=fmt(b[0:24]), p1=fmt(b[24:48]),
                    c0=fmt(b[48:72]), c1=fmt(b[72:96]))

    print(f"\n--- MEASURED  ref={REF}  zb={ZB} ---")
    bad = 0
    for lbl, ops, _ in CASES:
        r, z = show(run(REF, ops)), show(run(ZB, ops))
        same = r == z
        bad += not same
        print(f"  {'agree' if same else 'DIFF '} {lbl}")
        for k in ("p0", "p1", "c0", "c1"):
            rv = r[k] if r else None
            zv = z[k] if z else None
            mark = " " if rv == zv else "*"
            print(f"      {mark}{k}  ref={rv}")
            if rv != zv:
                print(f"       {k}  zb ={zv}")
    print(f"\n=== rows where the machines DIFFER: {bad} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
