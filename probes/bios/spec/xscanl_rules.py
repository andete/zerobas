#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/SCANL.md's EXECUTABLE RULES (docs/spec-method.md §3a): SCANL ($012F) -- probes/bios/spec/xgfx6.asm, op 2
(the loader and the pixel model are xgfx6_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx6_model as G  # noqa: E402

PAGE = "docs/bios/SCANL.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(2)


S1 = "1. SCANL ($012F): scan left for the PAINT border, and paint"
ALL = lambda c: True  # noqa: E731


def scan(c):
    """(VRAM writes, HL, CLOC / CMASK)"""
    v, (x0, y) = {}, G.start(c)
    x = x0 - 1
    while x >= 0 and G.colour(c, v, x, y) != c.cbdr:
        x -= 1
    n, xl = x0 - 1 - x, x + 1
    G.paint(c, v, xl, y, n + (8 if c.cscr == 2 else 0))
    return v, n, G.place(c, xl, y)


RULES = [
    Rule("R-SL-SCAN", S1, "From the pixel left of CLOC / CMASK (SCREEN 3: the block), count the pixels that are not "
         "BDRATR's colour, leftwards, to the first that is or to X 0. HL := that count; CLOC / CMASK := the leftmost "
         "counted pixel (the start itself when the count is 0). B, DE, A and HL on entry are not used.", ALL,
         lambda c: (c.hl, (c.cloc, c.cmask)) == (scan(c)[1], scan(c)[2])),
    Rule("R-SL-PAINT", S1, "It paints, whatever B is, in ATRBYT from the new CLOC rightwards: in SCREEN 2 HL + 8 pixels "
         "-- through the start pixel and 7 more, on into the next character row's cells past X 255 -- as NSETCX "
         "sets them; in SCREEN 3 HL blocks, the start block not included. Nothing else in VRAM changes.", ALL,
         lambda c: G.vram_after(c, scan(c)[0]) == (c.sums, (c.w1, c.w2))),
    Rule("R-SL-KEEP", S1, "IX and IY are kept; the work area recorded ($F92D-$F933, $F942-$F954), ATRBYT, BDRATR, "
         "RG0SAV-RG7SAV, SCRMOD and the VDP registers are kept; interrupts are on after. (A, F, BC and DE are left "
         "holding working values: not compared, the group `XL`.)", ALL,
         lambda c: (c.ix, c.iy, c.iff) == (G.marker(c, 0x4321), G.marker(c, 0x8765), 1)
         and c.gwork == G.gwork_kept() and (c.atrbyt, c.bdratr) == (c.catr, c.cbdr)
         and c.regs == (0xA5,) * 8 + (c.cscr,) + G.VPRE),
]
