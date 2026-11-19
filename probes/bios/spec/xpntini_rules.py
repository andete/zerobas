#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/PNTINI.md's EXECUTABLE RULES (docs/spec-method.md §3a): PNTINI ($0129) -- probes/bios/spec/xgfx6.asm, op 0
(the loader is xgfx6_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx6_model as G  # noqa: E402
from xsetatr_rules import cp_ccf  # noqa: E402

PAGE = "docs/bios/PNTINI.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(0)


S1 = "1. PNTINI ($0129): set the PAINT border colour"
ALL = lambda c: True  # noqa: E731


def logical(v):
    return (v & 0xA8) | (0x40 if v == 0 else 0) | (0x04 if bin(v).count("1") % 2 == 0 else 0)


RULES = [
    Rule("R-PI-BDR", S1, "BDRATR ($FCB2) := ATRBYT in SCREEN 2, whatever A is ($05, $0F, $10, $FF measured); := A in any "
         "other mode (SCREEN 3: $05, $09, $10, $80, $FF; SCRMOD 0 and 1: $05 measured; none refused). ATRBYT whole: "
         "$1A gives $1A.", ALL,
         lambda c: c.bdratr == (c.catr if c.cscr == 2 else c.ca)),
    Rule("R-PI-AF", S1, "SCREEN 2: A := ATRBYT, F its flags as an AND leaves them (H set: $10 for $07, $54 for $00, $1C for $0A). Other modes: A "
         "kept, F as CP $10 then CCF leave it (as SETATR: the carry set when A is $10 or more) -- whatever F was.", ALL,
         lambda c: (c.a, c.f) == ((c.catr, logical(c.catr) | 0x10) if c.cscr == 2 else (c.ca, cp_ccf(c.ca)))),
    Rule("R-PI-KEEP", S1, "BC, DE, HL, IX, IY and the interrupt state are kept; CLOC, CMASK, ATRBYT, the work area "
         "$F92D-$F933 / $F942-$F954, VRAM, RG0SAV-RG7SAV, SCRMOD and the VDP registers are kept.", ALL,
         lambda c: ((c.bc, c.de, c.hl, c.ix, c.iy, c.iff) == (c.cb << 8 | G.marker(c, 0x57) & 0xFF, c.cde, 0x2468,
                                                               G.marker(c, 0x4321), G.marker(c, 0x8765), c.ei)
                    and (c.cloc, c.cmask, c.atrbyt) == (c.cclo, c.ccm, c.catr) and c.gwork == G.gwork_kept()
                    and G.vram_after(c, {}) == (c.sums, (c.w1, c.w2))
                    and c.regs == (0xA5,) * 8 + (c.cscr,) + G.VPRE)),
]
