#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/GTSTCK.md's EXECUTABLE RULES (docs/spec-method.md §3a): GTSTCK ($00D5) -- probes/bios/spec/xinp1.asm, op 3
(the loader is xinp1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xinp1_model as G  # noqa: E402

PAGE = "docs/bios/GTSTCK.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(3, "XIW")


S1 = "1. GTSTCK ($00D5): read a joystick or the cursor keys"
ALL = lambda c: True  # noqa: E731
QUIET = ("With interrupts off after the call, the cells the timer interrupt's key scan writes (NEWKEY, OLDKEY, "
         "TRGFLG, the key buffer pointers, PSG R15) are kept; with them on, they are not compared.")


def direction(c):
    if c.ca != 0:
        return 0                                         # nothing is plugged into the joystick ports
    k = c.keys[8]
    left, up, down, right = (k >> 4) & 1, (k >> 5) & 1, (k >> 6) & 1, (k >> 7) & 1
    v, h = up - down, right - left
    return {(1, 0): 1, (1, 1): 2, (0, 1): 3, (-1, 1): 4, (-1, 0): 5, (-1, -1): 6, (0, -1): 7, (1, -1): 8}.get((v, h), 0)


RULES = [
    Rule("R-GS-PORT", S1, "PSG R15 bit 6 (which joystick port the PSG's port A reads) := 0 for an odd A, 1 for an "
         "even one but 0 (A 0, the keyboard, leaves it); its other bits are kept ($CF preset: $8F / $CF).", ALL,
         lambda c: c.r15 == G.r15_port(c)),
    Rule("R-GS-A", S1, "A 0: the cursor keys (row 8: bit 4 left, 5 up, 6 down, 7 right) give A := 1 up, 2 up-right, 3 "
         "right, 4 down-right, 5 down, 6 down-left, 7 left, 8 up-left, 0 none; opposite keys cancel (up + down, left + "
         "right, all four: 0; left + up + down: 7). A 1 / 2 (the joystick ports, nothing plugged) and 3: 0.", ALL,
         lambda c: c.a == direction(c)),
    G.keep_rule("GS", S1, "IX, IY, INTFLG, CAPST and R14 are kept; the PPI port C is kept -- its low nibble 8 (row 8 selected) for A 0. (F, BC, DE and "
                "HL are left holding working values: not compared, the group `XIW`.)",
                lambda c: G.ixiy(c) and G.cells(c) and c.aa == ((c.cpc & 0xF0) | 8 if c.ca == 0 else c.cpc) and G.quiet(c, r15=G.r15_port(c))),
    Rule("R-GS-EI", S1, "Interrupts are on after the call, whether they were on or off before it.", ALL,
         lambda c: c.iff == 1),
]
