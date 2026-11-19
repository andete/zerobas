#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/GTPDL.md's EXECUTABLE RULES (docs/spec-method.md §3a): GTPDL ($00DE) -- probes/bios/spec/xinp1.asm, op 9
(the loader is xinp1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xinp1_model as G  # noqa: E402

PAGE = "docs/bios/GTPDL.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(9, "XIW")


S1 = "1. GTPDL ($00DE): read a paddle"
ALL = lambda c: True  # noqa: E731
QUIET = ("With interrupts off after the call, the cells the timer interrupt's key scan writes (NEWKEY, OLDKEY, "
         "TRGFLG, the key buffer pointers, PSG R15) are kept; with them on, they are not compared.")


RULES = [
    Rule("R-PD-A", S1, "Nothing plugged: A := $FF (A 1, 2, 12 measured).", ALL, lambda c: c.a == 0xFF),
    G.keep_rule("PD", S1, "IX, IY, INTFLG, CAPST and R14 are kept; the PPI port C's high nibble is kept. (F, BC, DE and HL "
                "are left holding working values.)", lambda c: G.ixiy(c) and G.cells(c) and c.aa & 0xF0 == 0x50
                and G.quiet(c)),
    Rule("R-PD-EI", S1, "Interrupts are on after the call, whether they were on or off before it.", ALL,
         lambda c: c.iff == 1),
]
