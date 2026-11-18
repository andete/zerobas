#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/SETATR.md's EXECUTABLE RULES (docs/spec-method.md §3a): SETATR ($011A) -- probes/bios/spec/xgfx1.asm, op 2
(the loader is xgfx1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx1_model as G  # noqa: E402

PAGE = "docs/bios/SETATR.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(2)


S1 = "1. SETATR ($011A): set the graphics colour"
ALL = lambda c: True  # noqa: E731


def cp_ccf(a):
    """F as CP $10 then CCF leave it: S / Z / P/V of A - $10, CP's bits 5 / 3 replaced by CCF's (from A), N clear,
    H := CP's carry, C := not CP's carry"""
    r = (a - 0x10) & 0xFF
    borrow = 1 if a < 0x10 else 0
    ov = 0x04 if (a ^ 0x10) & (a ^ r) & 0x80 else 0
    f = (r & 0x80) | (0x40 if r == 0 else 0) | ov | (a & 0x28)
    return f | (0x10 if borrow else 0) | (0 if borrow else 1)


RULES = [
    Rule("R-SA-ATR", S1, "A colour 0-15 is stored: ATRBYT ($F3F2) := A; A of 16 or more is refused: ATRBYT is kept "
         "and the carry set (A $00, $05, $0F, $10, $80, $FF).", ALL,
         lambda c: c.atrbyt == (c.ca if c.ca < 16 else 0x77) and (c.f & 1) == (1 if c.ca >= 16 else 0)),
    Rule("R-SA-F", S1, "The whole F is what CP $10 followed by CCF leaves: S, Z and P/V from A - $10, bits 5 / 3 "
         "from A, N clear, H set and the carry clear for A below 16, H clear and the carry set from 16 -- whatever F "
         "was on entry.", ALL, lambda c: c.f == cp_ccf(c.ca)),
    G.keep_rule("SA", S1, "A, BC, DE, HL, IX, IY, the interrupt state, CLOC, CMASK, ASPCT1 / ASPCT2 and SCRMOD are "
                "kept.", ["a", "bc", "de", "hl", "ix", "iy", "iff", "cloc", "cmask", "aspct", "scrmod"]),
]
