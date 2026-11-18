#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/SCALXY.md's EXECUTABLE RULES (docs/spec-method.md §3a): SCALXY ($010E) -- probes/bios/spec/xgfx4.asm, op 0
(the loader is xgfx4_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx4_model as G  # noqa: E402

PAGE = "docs/bios/SCALXY.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(0)


S1 = "1. SCALXY ($010E): clip a graphics coordinate"
ALL = lambda c: True  # noqa: E731


def clip(v, top):
    return 0 if v & 0x8000 else min(v, top)


def out(c):
    """(BC, DE, in range) after the call"""
    x, y = clip(c.cbc, 255), clip(c.cde, 191)
    inside = (x, y) == (c.cbc, c.cde)
    if c.cscr != 2:
        x, y = x >> 2, y >> 2
    return x, y, inside


def szp(v):
    return (v & 0x80) | (0x40 if v == 0 else 0) | (0x04 if bin(v).count("1") % 2 == 0 else 0)


RULES = [
    Rule("R-SX-CLIP", S1, "BC (X) and DE (Y) are clipped as signed 16-bit numbers: below 0 ($8000-$FFFF) gives 0, "
         "above 255 (X) / 191 (Y) gives 255 / 191 ($0100, $012C, $01FF, $7FFF measured). Then, when SCRMOD is not 2 "
         "(SCREEN 3, and 0 and 1 measured), both are divided by 4, the remainder dropped -- block numbers: 255 gives "
         "$3F, 191 $2F, 100 $19.", ALL, lambda c: (c.bc, c.de) == out(c)[:2]),
    Rule("R-SX-AF", S1, "The carry is set when neither coordinate was clipped, clear when either was. A := $80 when "
         "neither was, $00 when either was. The other flags: in SCREEN 2, Z set and the rest clear ($41 / $40); with "
         "any other SCRMOD, S, Z and P/V from the new E, H, N and bits 3 / 5 clear ($05 for E $0C in range, $44 for "
         "E 0 clipped) -- whatever A and F were on entry.", ALL,
         lambda c: c.a == (0x80 if out(c)[2] else 0) and c.f == ((0x40 if c.cscr == 2 else szp(out(c)[1] & 0xFF))
                                                                  | (1 if out(c)[2] else 0))),
    G.keep_rule("SX", S1, "HL, IX, IY, the interrupt state and the work area recorded (CLOC, CMASK, ATRBYT, ASPCT1 / "
                "ASPCT2, SCRMOD, GRPCGP, MLTCGP) are kept.",
                ["hl", "ix", "iy", "iff", "cloc", "cmask", "atrbyt", "aspct", "scrmod", "cgp"]),
]
