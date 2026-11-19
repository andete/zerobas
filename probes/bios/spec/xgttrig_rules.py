#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/GTTRIG.md's EXECUTABLE RULES (docs/spec-method.md §3a): GTTRIG ($00D8) -- probes/bios/spec/xinp1.asm, op 4
(the loader is xinp1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xinp1_model as G  # noqa: E402

PAGE = "docs/bios/GTTRIG.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(4, "XIW")


S1 = "1. GTTRIG ($00D8): read a trigger or the space bar"
ALL = lambda c: True  # noqa: E731
QUIET = ("With interrupts off after the call, the cells the timer interrupt's key scan writes (NEWKEY, OLDKEY, "
         "TRGFLG, the key buffer pointers, PSG R15) are kept; with them on, they are not compared.")


RULES = [
    Rule("R-GT-PORT", S1, "PSG R15 bit 6 (which joystick port the PSG's port A reads) := 0 for an odd A, 1 for an "
         "even one but 0 (A 0, the keyboard, leaves it); its other bits are kept ($CF preset: $8F / $CF).", ALL,
         lambda c: c.r15 == G.r15_port(c)),
    Rule("R-GT-A", S1, "A 0: A := $FF when the space bar (row 8 bit 0) is pressed, 0 when not. A 1-4 (the joystick "
         "triggers, nothing plugged) and 5: 0.", ALL,
         lambda c: c.a == (0xFF if c.ca == 0 and c.keys[8] & 1 else 0)),
    G.keep_rule("GT", S1, "DE, HL, IX, IY, INTFLG, CAPST and R14 are kept; the PPI port C's high nibble is kept. (F and "
                "BC are left holding working values: not compared.)",
                lambda c: (c.de, c.hl) == (c.cde, c.chl) and G.ixiy(c) and G.cells(c) and c.aa & 0xF0 == c.cpc & 0xF0
                and G.quiet(c, r15=G.r15_port(c))),
    Rule("R-GT-EI", S1, "Interrupts are on after the call, whether they were on or off before it.", ALL,
         lambda c: c.iff == 1),
]
