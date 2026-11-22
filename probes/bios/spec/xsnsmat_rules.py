#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/SNSMAT.md's EXECUTABLE RULES (docs/spec-method.md §3a): SNSMAT ($0141) -- probes/bios/spec/xinp1.asm, op 0
(the loader is xinp1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xinp1_model as G  # noqa: E402

PAGE = "docs/bios/SNSMAT.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(0, "XIF")


S1 = "1. SNSMAT ($0141): read a row of the key matrix"
ALL = lambda c: True  # noqa: E731
QUIET = ("With interrupts off after the call, the cells the timer interrupt's key scan writes (NEWKEY, OLDKEY, "
         "TRGFLG, the key buffer pointers, PSG R15) are kept; with them on, they are not compared.")


RULES = [
    Rule("R-SM-A", S1, "A := key-matrix row A as the PPI reads it (bit 0 = pressed; rows 0-10 measured, one key or none "
         "or four; rows 3 and 4 too); the row is A AND $0F (A $12 reads row 2), and rows 11-15 give $FF.", ALL,
         lambda c: c.a == G.matrix(c, c.ca & 0x0F)),
    Rule("R-SM-C", S1, "C := the row number (A on entry).", ALL, lambda c: c.bc & 0xFF == c.ca),
    Rule("R-SM-PORT", S1, "The PPI's port C := (port C AND $F0) + A, an 8-bit ADD of the whole A: $50 + 8 is $58, $5A "
         "+ 8 is $58 too, $D0 + 2 is $D2, $50 + $12 is $62, $50 + $FF is $4F.", ALL,
         lambda c: c.aa == ((c.cpc & 0xF0) + c.ca) & 0xFF),
    G.keep_rule("SM", S1, "B, DE, HL, IX, IY, INTFLG, CAPST and R14 are kept. " + "(F is left holding a working value: "
                "not compared, the group `XIF`.)",
                lambda c: (c.bc >> 8, c.de, c.hl) == (c.cbc >> 8, c.cde, c.chl) and G.ixiy(c) and G.cells(c)
                and G.quiet(c)),
    Rule("R-SM-EI", S1, "Interrupts are on after the call, whether they were on or off before it.", ALL,
         lambda c: c.iff == 1),
]
