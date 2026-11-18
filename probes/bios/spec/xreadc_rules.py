#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/READC.md's EXECUTABLE RULES (docs/spec-method.md §3a): READC ($011D) -- probes/bios/spec/xgfx3.asm, op 0
(the loader and the VRAM model are xgfx3_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx3_model as G  # noqa: E402

PAGE = "docs/bios/READC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(0)


S1 = "1. READC ($011D): read the colour of the current pixel"
ALL = lambda c: True  # noqa: E731


def colour(c):
    if c.cscr == 2:
        pat = G.fill(c.cclo & 0x3FFF)
        col = G.fill(G.colour_addr(c, c.cclo))
        return col >> 4 if pat & c.ccm else col & 0x0F
    b = G.fill(c.cclo & 0x3FFF)
    return b & 0x0F if c.ccm == 0x0F else b >> 4


RULES = [
    Rule("R-RD-A", S1, "A := the current pixel's colour: in SCREEN 2 the foreground nibble of its colour byte "
         "(CLOC XOR $2000; GRPCOL and GRPCGP are not used) when its pattern bit (CLOC, CMASK) is set, the background nibble when not; in "
         "SCREEN 3 the nibble CMASK selects ($0F the low one, $F0 the high one).", ALL, lambda c: c.a == colour(c)),
    Rule("R-RD-F", S1, "F is A's flags as an AND leaves them (H set; S, Z, bits 5 / 3 and P/V from A) -- whatever F "
         "was on entry.", ALL, lambda c: c.f == G.logical(c.a) | 0x10),
    Rule("R-RD-KEEP", S1, "BC, DE, HL, IX and IY are kept; CLOC, CMASK and ATRBYT are kept; VRAM is not changed.", ALL,
         lambda c: ((c.bc, c.de, c.hl, c.ix, c.iy) == tuple(G.marker(c, v) for v in (0x1357, 0x9BDF))
                    + (c.chl, G.marker(c, 0x4321), G.marker(c, 0x8765))
                    and (c.cloc, c.cmask, c.atrbyt) == (c.cclo, c.ccm, c.catr)
                    and G.vram_after(c, {}) == (c.sums, (c.w1, c.w2, c.w3)))),
    G.regs_rule("RD", S1),
    G.ei_rule("RD", S1),
]
