#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GATEBLIND -- the instrument for `PSET(0,192)`, and the two things that
would have made it blind. Arithmetic only, no emulator.

D-GATEBLIND split the blind `clip_noop` into two rows and FILED the third
statement: with the clip removed `PSET(0,192)` writes $1800, outside the
6144-byte pattern plane, and the filed residual said "band_segs() clamps to 24
cell rows so no band phase A can express reaches it".

🔴 **THAT BLOCKER NAMED THE WRONG OBSTACLE.** `band_segs()` is phases C/D/E's
instrument (LINE / CIRCLE / DRAW bands), and it is clamped. PHASE A DOES NOT USE
IT: every phase-A row captures `[(paddr(x,y), 1), (paddr(x,y) + $2000, 1)]`, two
explicit one-byte segments, and `paddr(0,192)` is 6144 = $1800 EXACTLY. The
capture shape reached the cell all along. [[a-filed-blocker-can-name-the-wrong-obstacle]]

What was actually missing is smaller and nastier, and it is the same question
the whole slice turns on -- *what would a failure WRITE?*

    gfx_plot: read pattern[$1800] and colour[$3800], then gfx_color_rmw:
        c == (colour & $0F)  ->  CLEAR the pattern bit, colour UNTOUCHED
        otherwise            ->  SET the bit, colour = (c << 4) | (colour & $0F)

$3800 is the SPRITE PATTERN GENERATOR in SCREEN 2, not a pixel plane, and its
byte 0 is whatever the BIOS left. If its low nibble happens to equal the plot
colour, an unclipped `PSET(0,192)` CLEARS a pattern bit that is already 0 and
writes no colour byte at all: **both captured cells would read back unchanged
and the new row would be as blind as the one it replaces.** So the row pins the
pre-state with `SPRITE$(0)=STRING$(8,0)` -- a BASIC statement, not a VPOKE (the
phase-A docstring's rule) -- which zeroes $3800..$3807 on both machines. That
also removes the second hazard: the two BIOSes need not agree on the boot
contents of a sprite table nobody has written yet.

    python3 -u scratchpad/y192_proof.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))

from basic_probe_graphics import DRAW_CASES, paddr  # noqa: E402

FORCLR = 15                     # COLOR15,4,7 -- phase A's pinned INIT


def main() -> int:
    print("=== the instrument for PSET(0,192) ===\n")
    pa = paddr(0, 192)
    ca = pa + 0x2000
    print(f"  paddr(0,192)          = ${pa:04X} ({pa}) -- the SCREEN 2 NAME TABLE")
    print(f"  its colour-half cell  = ${ca:04X} -- the SPRITE PATTERN GENERATOR")
    print(f"  the pattern plane is 0..6143, so ${pa:04X} is one byte past its end\n")
    assert pa == 0x1800 and ca == 0x3800

    print("  phase A captures [(pa,1),(pa+$2000,1)] -- EXPLICIT one-byte segments,")
    print("  not a band_segs() band -- so both cells a failure would write are")
    print("  inside the row's capture. The instrument was never the obstacle.\n")

    print("=== what an unclipped PSET(0,192),15 would write, per pre-state ===\n")
    print("   colour[$3800]   bg nibble   rmw       pattern[$1800]  colour[$3800]")
    blind = []
    for cur in (0x00, 0x04, 0xF4, 0x0F, 0xFF, 0x1F):
        bg = cur & 0x0F
        if bg == FORCLR:
            pat, col, rule = 0x00, cur, "CLEAR"
            blind.append(cur)
        else:
            pat, col, rule = 0x80, (FORCLR << 4) | bg, "SET"
        print(f"        ${cur:02X}          {bg:2d}      {rule:5}         "
              f"${pat:02X}             ${col:02X}"
              f"{'   <- BOTH CELLS UNCHANGED: BLIND' if bg == FORCLR else ''}")

    print(f"\n  🔴 for {len(blind)} of the pre-states above the row cannot see its own")
    print("     failure: the clash rule CLEARS a bit that is already 0 and leaves")
    print("     the colour byte alone. Whether the gate row is blind is decided by")
    print("     a byte of a sprite table nobody wrote.")

    row = [c for c in DRAW_CASES if c[0] == "clip_noop_y192"]
    print("\n=== the row as it now ships ===")
    if not row:
        print("  🔴 clip_noop_y192 is NOT in DRAW_CASES")
        return 1
    label, ops, xy, ep, ec = row[0]
    print(f"  {label}: {ops}")
    print(f"    reads (x,y)={xy} -> ${paddr(*xy):04X} / ${paddr(*xy) + 0x2000:04X}, "
          f"oracle pattern {ep} colour {ec}")
    ok = "SPRITE$(0)=STRING$(8,0)" in ops and "PSET(0,192)" in ops
    print("    pre-state pinned: " + ("yes" if ok else
          "🔴 NO -- blind for any pre-state whose colour low nibble is 15"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
