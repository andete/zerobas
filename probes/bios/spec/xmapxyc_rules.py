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
    """SCREEN 2: (CLOC, CMASK, A) from X (C) and Y (E) and GRPCGP"""
    x, y = c.cbc & 0xFF, c.cde & 0xFF
    cloc = (c.cgcg + (y & 0xF8) * 32 + (x & 0xF8) + (y & 7)) & 0xFFFF
    return cloc, 0x80 >> (x & 7)


def mlt(c):
    x, y = c.cbc & 0xFF, c.cde & 0xFF
    cloc = (c.cmcg + ((y >> 3) & 7) * 256 + ((x >> 1) & 31) * 8 + (y & 7)) & 0xFFFF
    return cloc, 0x0F if x & 1 else 0xF0


def want_af(c):
    if not MLT(c):
        cloc = grp(c)[0]
        a = (cloc - c.cgcg) & 0xFF            # the offset's low byte, before GRPCGP is added
    else:
        cloc = mlt(c)[0]
        a = (c.cde >> 3) & 7
    return a, (G.logical(a) & 0xC4) | ((cloc >> 8) & 0x28)


RULES = [
    Rule("R-MX-GRP", S1, "In SCREEN 2 (SCRMOD 2), with X in C and Y in E (their high bytes play no part): CLOC := GRPCGP "
         "+ (Y AND $F8) x 32 + (X AND $F8) + (Y AND 7), with GRPCGP ($F3CB) as it holds -- an addition ($20F8 carries "
         "into the high byte; GRPCGP $0000, $1804, $2000, $20F8 measured) -- and CMASK := $80 >> (X AND 7).",
         lambda c: not MLT(c), lambda c: c.cloc == grp(c)[0] and (c.src == "XGX" or c.cmask == grp(c)[1])),
    Rule("R-MX-MLT", S1, "In any other SCRMOD (3; and 0, 1, 4, $FF too), X and Y are multicolour block numbers, their "
         "high bytes playing no part: CLOC := MLTCGP + ((Y >> 3) AND 7) x 256 + ((X >> 1) AND 31) x 8 + (Y AND 7), with "
         "MLTCGP ($F3D5) as it holds -- an addition ($1100 with Y 8 gives $1201; $0000, $0300, $0B00, $1000, $2800 "
         "measured) -- and CMASK := $F0 for even X, $0F for odd: X and Y count modulo 64.", MLT,
         lambda c: (c.cloc, c.cmask) == mlt(c)),
    Rule("R-MX-AF", S1, "A := in SCREEN 2 the offset's low byte, before GRPCGP is added (GRPCGP $1804 / $20F8 tell); in "
         "other SCRMOD (Y >> 3) AND 7. F: S, Z and P/V from that A (as an OR leaves them), bits 5 / 3 from CLOC's high "
         "byte (GRPCGP $0000 / $1804, MLTCGP $0B00 / $2800 tell), H, N and C clear -- whatever A and F were on entry "
         "($A7, $00, $FF, $5A). The expected values come from the model, not from the CLOC returned.", ALL,
         lambda c: (c.a, c.f) == want_af(c)),
    Rule("R-MX-REGS", S1, "BC is kept; DE is kept but for D := X's low byte in SCREEN 2 (X 7, Y $0100 gives DE $0700); "
         "HL := the modelled CLOC; IX, IY, the interrupt state, ATRBYT, ASPCT1 / ASPCT2, SCRMOD and GRPCGP / MLTCGP are "
         "kept.", ALL,
         lambda c: (c.bc == c.cbc and c.hl == (grp(c) if not MLT(c) else mlt(c))[0]
                    and c.de == (((c.cbc & 0xFF) << 8 | (c.cde & 0xFF)) if not MLT(c) else c.cde)
                    and G.kept(c, ["ix", "iy", "iff", "atrbyt", "aspct", "scrmod", "cgp"]))),
]
