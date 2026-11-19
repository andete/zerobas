#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/SCANR.md's EXECUTABLE RULES (docs/spec-method.md §3a): SCANR ($012C) -- probes/bios/spec/xgfx6.asm, op 1
(the loader and the pixel model are xgfx6_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx6_model as G  # noqa: E402

PAGE = "docs/bios/SCANR.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(1)


S1 = "1. SCANR ($012C): scan right for the PAINT border"
ALL = lambda c: True  # noqa: E731


def scan(c):
    """(VRAM writes, HL, DE, CLOC / CMASK, the run's start CLOC / CMASK)"""
    return G.scanr(c)


RULES = [
    Rule("R-SR-SCAN", S1, "From the pixel at CLOC / CMASK (SCREEN 3: the block), first a skip: while the pixel is "
         "BDRATR's colour, count DE down; when that makes it 0 the call ends there -- CLOC / CMASK on that pixel, HL 0, "
         "nothing painted or saved (DE 1 stops on the first border pixel, DE 2 on the second) -- otherwise step right "
         "(from DE 0 it goes on below 0: 4 border pixels give $FFFC). Then the run: count the pixels that are not BDRATR's, rightwards, to the first that is or to the row's last "
         "(X 255 / block 63). HL := that count; DE := the counted-down skip; CLOC / CMASK := the stopping pixel (the "
         "row's last if none stopped it).", ALL,
         lambda c: (c.hl, c.de, (c.cloc, c.cmask)) == scan(c)[1:4]),
    Rule("R-SR-PAINT", S1, "The run is painted in ATRBYT -- in SCREEN 2 when B is not 0, as NSETCX sets pixels (a whole "
         "byte to pattern $00, colour ATRBYT); in SCREEN 3 whatever B is. Nothing else in VRAM changes.", ALL,
         lambda c: G.vram_after(c, scan(c)[0]) == (c.sums, (c.w1, c.w2))),
    Rule("R-SR-SAVE", S1, "CSAVEA / CSAVEM ($F942 / $F944) := the run's first pixel (kept when the skip ended the "
         "call); the rest of the work area recorded "
         "($F92D-$F933, $F945-$F954), ATRBYT and BDRATR are kept.", ALL,
         lambda c: c.gwork == (G.gwork_kept() if scan(c)[4] is None else G.gwork_kept()[0:7] + (
             lambda p: (p[0] & 0xFF, p[0] >> 8, p[1]))(scan(c)[4]) + G.gwork_kept()[10:])
         and (c.atrbyt, c.bdratr) == (c.catr, c.cbdr)),
    Rule("R-SR-KEEP", S1, "IX and IY are kept; RG0SAV-RG7SAV, SCRMOD and the VDP registers are kept; interrupts are on "
         "after. (A, F and BC are left holding working values: not compared, the group `XR`.)", ALL,
         lambda c: (c.ix, c.iy, c.iff) == (G.marker(c, 0x4321), G.marker(c, 0x8765), 1)
         and c.regs == (0xA5,) * 8 + (c.cscr,) + G.VPRE),
]
