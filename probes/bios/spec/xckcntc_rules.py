#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CKCNTC.md's EXECUTABLE RULES (docs/spec-method.md §3a): CKCNTC ($00BD) -- probes/bios/spec/xinp1.asm, op 7
(the loader is xinp1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xinp1_model as G  # noqa: E402

PAGE = "docs/bios/CKCNTC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(7, "XI")


S1 = "1. CKCNTC ($00BD): check CTRL+STOP for the interpreter"
ALL = lambda c: True  # noqa: E731
QUIET = ("With interrupts off after the call, the cells the timer interrupt's key scan writes (NEWKEY, OLDKEY, "
         "TRGFLG, the key buffer pointers, PSG R15) are kept; with them on, they are not compared.")


RULES = [
    Rule("R-CK-AF", S1, "With INTFLG ($FC9B) 0 (no break pending): A := 0, F := $54 -- as ISCNTC.", ALL,
         lambda c: (c.a, c.f) == (0, 0x54)),
    G.keep_rule("CK", S1, "BC, DE, HL, IX, IY, INTFLG, CAPST and R14 are kept; the PPI port C's high nibble is kept.",
                lambda c: (c.bc, c.de, c.hl) == (c.cbc, c.cde, c.chl) and G.ixiy(c) and G.cells(c)
                and c.aa & 0xF0 == c.cpc & 0xF0 and G.quiet(c)),
    Rule("R-CK-EI", S1, "Interrupts are on after the call, whether they were on or off before it.", ALL,
         lambda c: c.iff == 1),
]
