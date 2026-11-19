#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/GTPAD.md's EXECUTABLE RULES (docs/spec-method.md §3a): GTPAD ($00DB) -- probes/bios/spec/xinp1.asm, op 8
(the loader is xinp1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xinp1_model as G  # noqa: E402

PAGE = "docs/bios/GTPAD.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(8, "XIP")


S1 = "1. GTPAD ($00DB): read a touch pad"
ALL = lambda c: True  # noqa: E731
QUIET = ("With interrupts off after the call, the cells the timer interrupt's key scan writes (NEWKEY, OLDKEY, "
         "TRGFLG, the key buffer pointers, PSG R15) are kept; with them on, they are not compared.")


RULES = [
    Rule("R-GP-A", S1, "Nothing plugged: A := 0 for A 0-4 and 7.", ALL, lambda c: c.a == 0),
    G.keep_rule("GP", S1, "IX, IY, INTFLG, CAPST and R14 are kept; the PPI port C is kept. (F, BC, DE and HL "
                "and PSG R15 -- bit-banged by the pad protocol -- are left holding working values: not compared, the group `XIP`.)",
                lambda c: G.ixiy(c) and G.cells(c) and c.aa == c.cpc and G.quiet(c, r15=None)),
    Rule("R-GP-EI", S1, "Interrupts are on after the call -- except for A 1 and 2 (the touch pad's X / Y), which keep "
         "the interrupt state.", ALL, lambda c: c.iff == (c.ei if c.ca in (1, 2) else 1)),
]
