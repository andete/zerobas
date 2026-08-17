#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GATEBLIND -- is `clip_noop` blind? Proved by arithmetic, no emulator.

The blindness sweep flagged phase A's `clip_noop`:

    PSET(300,100):PSET(0,192):PSET(-1,0)   band = the cell at (0,0),
                                           expected pattern $00 / colour $04

It asserts that three off-screen PSETs draw nothing, and it checks that by
reading the cell at (0,0). But the question a coverage row has to answer is not
"is the cell I read blank" -- it is "IS THE CELL I READ THE CELL A FAILURE WOULD
WRITE". So: strip the clip out of `gfx_plot_cur` on paper, run each coordinate
through `gfx_calc_addr` exactly as the tenant would, and see where the pixel
would land.

    addr = (y >> 3) * 256 + (x & $F8) + (y & 7)        [8-bit x, 8-bit y]

The sweep is a hand-listed battery and cannot prove blindness by itself; this
can, because it enumerates the row's ENTIRE failure surface -- three statements,
three addresses -- and compares it with the row's band.

    python3 -u scratchpad/clipnoop_proof.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))

from basic_probe_graphics import band_segs, paddr  # noqa: E402


def calc_addr(x, y):
    """gfx_calc_addr with the clip REMOVED: the low bytes are what the tenant
    would actually feed the VDP, so a 16-bit coordinate is truncated to 8."""
    xl, yl = x & 0xFF, y & 0xFF
    return (yl >> 3) * 256 + (xl & 0xF8) + (yl & 7)


CASES = [("PSET(300,100)", 300, 100),
         ("PSET(0,192)", 0, 192),
         ("PSET(-1,0)", -1, 0)]


def main() -> int:
    segs = band_segs((0, 0), (0, 0))
    covered = {a + i for a, n in segs for i in range(n)}
    print("=== is `clip_noop` blind? ===\n")
    print(f"  the row reads the cell at (0,0): addresses "
          f"{min(covered)}..{max(covered)} ({len(covered)} bytes)")
    print(f"  the pattern plane is 0..6143; the name table starts at "
          f"{0x1800}\n")
    print("  if the clip were REMOVED, each statement would write:")
    blind = True
    for label, x, y in CASES:
        a = calc_addr(x, y)
        inband = a in covered
        inplane = a < 6144
        blind &= not inband
        print(f"    {label:16} -> addr ${a:04X} ({a:5d})   "
              f"{'IN BAND' if inband else 'not in the band'}"
              f"{'' if inplane else '   [outside the pattern plane entirely]'}")
    print()
    if blind:
        print("  🔴 NOT ONE of the three lands in the band the row reads.")
        print("     `clip_noop` is GREEN WHETHER OR NOT THE CLIP WORKS -- it")
        print("     would pass with every clip in gfx_plot_cur deleted.")
    else:
        print("  the row can see at least one of its own failure modes.")

    print("\n=== bands that CAN see each failure ===")
    for label, x, y in CASES:
        a = calc_addr(x, y)
        if a >= 6144:
            print(f"  {label:16} writes ${a:04X}, OUTSIDE the 6144-byte "
                  f"pattern plane -- no band_segs() band can reach it, so this")
            print(f"  {'':16} statement needs a different instrument, not a "
                  f"wider band.")
            continue
        row, rest = a // 256, a % 256
        cx, cy = (rest // 8) * 8, row * 8
        print(f"  {label:16} writes ${a:04X} -> cell col {rest // 8}, row {row}"
              f"  => band x {cx}..{cx + 7}, y {cy}..{cy + 7}")
        chk = {aa + i for aa, n in band_segs((cx, cx + 7), (cy, cy + 7))
               for i in range(n)}
        assert a in chk, "proposed band still misses it"
        print(f"  {'':16} verified: the proposed band contains ${a:04X}")
    return 0 if blind else 1


if __name__ == "__main__":
    sys.exit(main())
