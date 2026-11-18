#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/MAPXYC.md's EXECUTABLE RULES (docs/spec-method.md §3a): MAPXYC ($0111) -- probes/bios/spec/xgfx1.asm, op 4
(the loader is xgfx1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx1_model as G  # noqa: E402

PAGE = "docs/bios/MAPXYC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(4)


S1 = "1. MAPXYC ($0111): turn coordinates into a graphics position"
ALL = lambda c: True  # noqa: E731

MLT = lambda c: c.cscr != 2  # noqa: E731


def grp(c):
    x, y = c.cbc & 0xFF, c.cde & 0xFF
    off = (y & 0xF8) * 32 + (x & 0xF8) + (y & 7)
    return (0x2000 + off) & 0xFFFF, 0x80 >> (x & 7)


def mlt(c):
    x, y = c.cbc & 0xFF, c.cde & 0xFF
    off = ((y >> 3) & 7) * 256 + ((x >> 1) & 31) * 8 + (y & 7)
    return (0x1000 + off) & 0xFFFF, 0x0F if x & 1 else 0xF0


RULES = [
    Rule("R-MX-GRP", S1, "In SCREEN 2 (SCRMOD 2), with X in C and Y in E: CLOC := GRPCGP + (Y AND $F8) x 32 + (X AND "
         "$F8) + (Y AND 7), GRPCGP ($F3CB) as it holds ($2000 in the probe), and CMASK := $80 >> (X AND 7), for X 0-255.",
         lambda c: not MLT(c), lambda c: c.cloc == grp(c)[0] and (c.src == "XGX" or c.cmask == grp(c)[1])),
    Rule("R-MX-MLT", S1, "In any other SCRMOD (3, and 0 and 1 too), X and Y are multicolour block numbers: CLOC := "
         "MLTCGP + ((Y >> 3) AND 7) x 256 + ((X >> 1) AND 31) x 8 + (Y AND 7), MLTCGP ($F3D5) as it holds ($1000), and "
         "CMASK := $F0 for even X, $0F for odd -- X and Y count modulo 64.", MLT,
         lambda c: (c.cloc, c.cmask) == mlt(c)),
    Rule("R-MX-AF", S1, "SCREEN 2: A := CLOC's low byte, F's S, Z and P/V that byte's (as an OR leaves them) and its "
         "bits 5 / 3 from CLOC's high byte, H, N, C clear. Other SCRMOD: A := (Y >> 3) AND 7 and F that value's flags as "
         "an OR leaves them. Whatever A and F were on entry.", ALL,
         lambda c: (c.a == (c.cloc & 0xFF) and c.f == (G.logical(c.cloc & 0xFF) & 0xC4) | ((c.cloc >> 8) & 0x28))
         if not MLT(c) else (c.a == (c.cde >> 3) & 7 and c.f == G.logical(c.a))),
    Rule("R-MX-REGS", S1, "BC and DE are kept but for D := X's low byte in SCREEN 2 (DE $0700 for X 7, Y 0); HL := "
         "CLOC; IX, IY and the interrupt state are kept; ATRBYT, ASPCT1 / ASPCT2 and SCRMOD are kept.", ALL,
         lambda c: (c.bc == c.cbc and c.hl == c.cloc
                    and c.de == (((c.cbc & 0xFF) << 8 | (c.cde & 0xFF)) if not MLT(c) else c.cde)
                    and G.kept(c, ["ix", "iy", "iff", "atrbyt", "aspct", "scrmod"]))),
]
