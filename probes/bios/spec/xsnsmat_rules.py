#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
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
         "or four); A of 11 and up: $FF.", ALL, lambda c: c.a == G.matrix(c, c.ca)),
    Rule("R-SM-C", S1, "C := the row number (A on entry).", ALL, lambda c: c.bc & 0xFF == c.ca),
    Rule("R-SM-PORT", S1, "The PPI's port C high nibble := (port C AND $F0) + the row number, an ADD: $50 stays $5x for "
         "rows 0-11, and row $FF gives $4x. (The low nibble selects the row; the timer interrupt's scan sets it again.)",
         ALL, lambda c: c.aa & 0xF0 == ((0x50 + c.ca) & 0xF0)),
    G.keep_rule("SM", S1, "B, DE, HL, IX, IY, INTFLG, CAPST and R14 are kept. " + "(F is left holding a working value: "
                "not compared, the group `XIF`.)",
                lambda c: (c.bc >> 8, c.de, c.hl) == (c.cbc >> 8, c.cde, c.chl) and G.ixiy(c) and G.cells(c)
                and G.quiet(c)),
    Rule("R-SM-EI", S1, "Interrupts are on after the call, whether they were on or off before it.", ALL,
         lambda c: c.iff == 1),
]
