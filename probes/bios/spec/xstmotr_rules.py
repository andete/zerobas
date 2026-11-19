#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/STMOTR.md's EXECUTABLE RULES (docs/spec-method.md §3a): STMOTR ($00F3) -- probes/bios/spec/xtap1.asm (the loader is
xtap1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xtap1_model as G  # noqa: E402

PAGE = "docs/bios/STMOTR.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load("STMOTR", "XT")


S1 = "1. STMOTR ($00F3): switch the cassette motor"
ALL = lambda c: True  # noqa: E731


def after(c):
    on = 1 if c.cpc & 0x10 else 0                      # 1 = it was stopped (bit 4 set)
    if c.ca == 0:
        return 1
    if c.ca == 0xFF:
        return 0 if on else 1
    return 0


RULES = [
    Rule("R-SM-MOTOR", S1, "The motor relay (port C bit 4, 0 = running): A 0 stops it, $FF toggles it, any other A ($01, "
         "$02, $7F, $80, $81, $FE) starts it. Port C's other bits are kept.", ALL,
         lambda c: c.aa == (c.cpc & ~0x10) | (after(c) << 4)),
    Rule("R-SM-AF", S1, "A := the PPI bit command left behind: $09 (bit 4 set: stopped) or $08 (reset: running). F, "
         "whatever it was: $54 stopping; starting, $10 -- but $38 for A $7F (A $01, $02, $80, $81, $FE and the "
         "toggle measured).", ALL,
         lambda c: (c.a, c.f) == ((0x09, 0x54) if after(c) else (0x08, 0x38 if c.ca == 0x7F else 0x10))),
    Rule("R-SM-KEEP", S1, "BC, DE, HL and the interrupt state are kept.", ALL,
         lambda c: (c.bc, c.de, c.hl, c.iff) == (0x1357, 0x9BDF, 0x2468, c.ei)),
]
