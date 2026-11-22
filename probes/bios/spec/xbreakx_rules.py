#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/BREAKX.md's EXECUTABLE RULES (docs/spec-method.md §3a): BREAKX ($00B7) -- probes/bios/spec/xinp1.asm, op 5
(the loader is xinp1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xinp1_model as G  # noqa: E402

PAGE = "docs/bios/BREAKX.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(5, "XIA")


S1 = "1. BREAKX ($00B7): check CTRL+STOP directly"
ALL = lambda c: True  # noqa: E731
QUIET = ("With interrupts off after the call, the cells the timer interrupt's key scan writes (NEWKEY, OLDKEY, "
         "TRGFLG, the key buffer pointers, PSG R15) are kept; with them on, they are not compared.")


def both(c):
    return bool(c.keys[6] & 0x02 and c.keys[7] & 0x10)


RULES = [
    Rule("R-BX-C", S1, "The carry := CTRL (row 6 bit 1) and STOP (row 7 bit 4) both pressed, read from the key matrix "
         "directly (CTRL alone, STOP alone, none: clear). (Only the carry of F is compared; A is left holding a working "
         "value, the group `XIA`.)", ALL, lambda c: c.f & 1 == (1 if both(c) else 0)),
    Rule("R-BX-BUF", S1, "With CTRL+STOP: the key buffer is emptied (GETPNT := PUTPNT) and OLDKEY's row 7 := $EF (STOP "
         "pressed). Otherwise both are kept.", ALL,
         lambda c: (c.getpnt, c.oldkey[7]) == ((G.PUT0, 0xEF) if both(c) else (G.GET0, 0xFF)) and c.putpnt == G.PUT0),
    G.keep_rule("BX", S1, "BC, DE, HL, IX, IY, INTFLG, CAPST, R14, NEWKEY, the other OLDKEY rows and TRGFLG are kept; "
                "the PPI port C's high nibble is kept, its low nibble left at the last row read: 7, or 6 when STOP is pressed.",
                lambda c: (c.bc, c.de, c.hl) == (c.cbc, c.cde, c.chl) and G.ixiy(c) and G.cells(c)
                and c.aa == (c.cpc & 0xF0) | (6 if c.keys[7] & 0x10 else 7) and c.newkey == (0xFF,) * 11 and c.trgflg == 0xF1 and c.r15 == 0xCF
                and c.oldkey[:7] + c.oldkey[8:] == (0xFF,) * 10),
    Rule("R-BX-EI", S1, "The interrupt state is kept.", ALL, lambda c: c.iff == c.ei),
]
