#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BFPERF prerequisite -- what does a FULLY COVERED cell's COLOUR byte hold?

The timing rows say the reference fills a horizontal run BYTE-WISE (a filled
scanline costs ~29 us/px against ~460 us/px for the same pixels drawn as a
line, and our own line rasteriser is at 1.00x parity). Any byte-wise fast path
in `gfx_box_fill` has to write the colour byte too, and when all 8 pixels of a
cell row are foreground the BACKGROUND nibble stops being visible as pixels --
but it is NOT invisible in the plane, and a plane differential compares it.
So this is a PRICE PREREQUISITE: a fast path that guesses the background
nibble is a fast path that fails the gate.

    keep_bg   the old background nibble survives (a true read-modify-write)
    fg_fg     the byte becomes (C<<4)|C

🔴 ROUND 1 OF THIS PROBE WAS INVALID AND ITS DEAD SUBJECT SAID SO. It read the
cells with `SCREEN0:PRINT"C";VPEEK(0);...` -- which switches to SCREEN 0, where
$0000 is the NAME TABLE, and then PRINTs into that very table before the later
VPEEKs are evaluated. The readout was overwriting what it was reading, and the
`dead_nofill` row diverged (32 vs 67 = a space vs the letter 'C') with no fill
in the program at all. A row that answers when the subject is absent is the
apparatus talking.

Round 2 uses the gate's own mechanism instead: hold SCREEN 2 in a GOTO-self
loop and capture the VRAM bytes through the debugger, so nothing is printed and
no mode switch happens.

    python3 -u scratchpad/bfperf_colour.py [--dry]
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

# cells (0..2, 0): pattern rows $0000-$0017, colour rows $2000-$2017.
SEGS = [(0x0000, 24), (0x2000, 24)]

CASES = [
    ("dead_nofill", "",
     "⭐ DEAD SUBJECT: no fill. COLOR15,4,7:SCREEN2 pins every colour byte to "
     "$04 (fg 0 | bg 4) and every pattern byte to $00. A row that moves here "
     "is the fixture, not the fill."),
    ("full_cell", "LINE(0,0)-(7,7),15,BF",
     "⭐ one cell FULLY covered. pattern -> $FF x8. colour: keep_bg -> $F4, "
     "fg_fg -> $FF."),
    ("full_cell_stained", "LINE(0,0)-(7,0),6:LINE(0,0)-(7,7),15,BF",
     "⭐ the same cell PRE-STAINED to fg 6 by a colour-6 line, then fully "
     "covered in 15. The stain proves the fill rewrote the byte rather than "
     "inheriting the fixture."),
    ("half_cell", "LINE(0,0)-(3,7),15,BF",
     "HALF a cell (x 0..3): the run is NOT byte-aligned, so the per-pixel "
     "clash rule must still apply -- pattern $F0, colour $F4. The row that "
     "says a fast path did not swallow the partial case."),
    ("full_row", "LINE(0,0)-(255,0),15,BF",
     "a whole SCANLINE: only cell row 0 is touched, so pattern row 0 = $FF "
     "and rows 1..7 stay $00 -- the widest byte-wise run there is."),
    ("line_not_fill", "LINE(0,0)-(7,0),15",
     "CONTROL: the same 8 pixels drawn as a LINE, not a fill. Whatever the "
     "fill does to the colour byte, the per-pixel path must already do -- if "
     "these two disagree ON THE SAME MACHINE, the fill has its own rule."),

    # --- round 3: pin the ENCODING and the BOUNDARY, and show the teeth -----
    ("full_cell_c6", "LINE(0,0)-(7,7),6,BF",
     "⭐ THE ENCODING. Round 2 saw colour $0F for a full byte filled in 15. "
     "$0F is fg 0 | bg 15, but with C=15 that is indistinguishable from any "
     "rule that happens to produce $0F. In 6 the prediction is $06 -- one "
     "colour cannot pin a two-nibble encoding."),
    ("span_partial_ends", "LINE(3,0)-(20,0),15,BF",
     "⭐ THE BOUNDARY: cell 0 covers x3..7 (PARTIAL), cell 1 covers x8..15 "
     "(FULL), cell 2 covers x16..20 (PARTIAL). One row that shows the fast "
     "path taking the middle byte and the per-pixel path taking both ends."),
    ("teeth_fill_then_pset", "LINE(0,0)-(7,7),15,BF:PSET(0,0),6",
     "⭐⭐ THE TEETH -- the row that makes the divergence VISIBLE. Filling a "
     "full byte then PSETting ONE pixel in it: on the reference the cell held "
     "pattern $00 (all background), so the PSET sets one bit and takes the "
     "FOREGROUND nibble -> one pixel in 6, seven still 15. On zerobas the "
     "cell held pattern $FF (all foreground), so the PSET clashes with the "
     "existing fg and repaints ALL EIGHT pixels 6. Same picture before, "
     "different picture after."),
]


def main() -> int:
    print("=== D-BFPERF prerequisite: the colour byte of a covered cell ===")
    print("    captured through the debugger while SCREEN 2 is still up:")
    print("    pattern $0000-$0007, colour $2000-$2007 (cell 0,0)\n")
    for lbl, ops, why in CASES:
        print(f"  {lbl:18} {ops or '(nothing)'}")
        print(f"      why: {why}")
    if "--dry" in sys.argv:
        return 0

    import omsx_repl

    def prog(ops):
        stmts = ["COLOR15,4,7:SCREEN2" + (":" + ops if ops else "")]
        return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]

    def run(machine, ops):
        return omsx_repl.run_cases(machine, [("stored", prog(ops))],
                                   batch=False,
                                   capture=("vram_segs", SEGS), step=30.0)[0]

    def show(hexs):
        if not hexs or len(hexs) != 96:
            return None, None
        b = bytes.fromhex(hexs)
        pat, col = b[:24], b[24:]
        f = lambda x: " ".join(x[i:i + 8].hex() for i in (0, 8, 16))
        return f(pat), f(col)

    print(f"\n--- MEASURED  ref={REF}  zb={ZB} ---")
    bad = 0
    for lbl, ops, _ in CASES:
        rp, rc = show(run(REF, ops))
        zp, zc = show(run(ZB, ops))
        same = (rp, rc) == (zp, zc)
        bad += not same
        print(f"  {'agree' if same else 'DIFF '} {lbl:18}")
        print(f"        ref pattern={rp} colour={rc}")
        print(f"        zb  pattern={zp} colour={zc}")
    print(f"\n=== rows where the machines DIFFER: {bad} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
