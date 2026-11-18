#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/SETC.md's EXECUTABLE RULES (docs/spec-method.md §3a): SETC ($0120) -- probes/bios/spec/xgfx3.asm, op 1
(the loader and the VRAM model are xgfx3_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx3_model as G  # noqa: E402

PAGE = "docs/bios/SETC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(1)


S1 = "1. SETC ($0120): set the current pixel"
ALL = lambda c: True  # noqa: E731


def writes(c):
    """VRAM: in SCREEN 2 the pattern byte at CLOC gets CMASK's bit set, and the colour byte at GRPCOL + CLOC - GRPCGP
    gets ATRBYT in its foreground nibble ((ATRBYT x 16) AND $F0: $1A gives $A0), the background nibble kept; in
    SCREEN 3 the nibble CMASK selects becomes ATRBYT's low nibble (the high one: (ATRBYT x 16) AND $F0). Nothing
    else changes. GRPCOL / GRPCGP from the cells (set 1: GRPCGP $2000, GRPCOL $0000)."""
    a = c.cclo & 0x3FFF
    if c.cscr == 2:
        ca = G.colour_addr(c, c.cclo)
        return {a: G.fill(a) | c.ccm, ca: ((c.catr << 4) & 0xF0) | (G.fill(ca) & 0x0F)}
    old = G.fill(a)
    new = (old & 0xF0) | (c.catr & 0x0F) if c.ccm == 0x0F else (old & 0x0F) | ((c.catr << 4) & 0xF0)
    return {a: new}


def new_byte(c):
    w = writes(c)
    return w[G.colour_addr(c, c.cclo)] if c.cscr == 2 else w[c.cclo & 0x3FFF]


RULES = [
    G.vram_rule("SC", S1, " ".join(writes.__doc__.split()), writes),
    Rule("R-SC-AF", S1, "A := the byte written last -- the colour byte in SCREEN 2, the pixel byte in SCREEN 3 -- and F "
         "its flags as an OR leaves them -- whatever A and F were on entry.", ALL,
         lambda c: c.a == new_byte(c) and c.f == G.logical(c.a)),
    Rule("R-SC-KEEP", S1, "BC, DE, HL, IX and IY are kept; CLOC, CMASK and ATRBYT are kept.", ALL,
         lambda c: ((c.bc, c.de, c.hl, c.ix, c.iy) == tuple(G.marker(c, v) for v in (0x1357, 0x9BDF))
                    + (c.chl, G.marker(c, 0x4321), G.marker(c, 0x8765))
                    and (c.cloc, c.cmask, c.atrbyt) == (c.cclo, c.ccm, c.catr))),
    G.ei_rule("SC", S1),
]
