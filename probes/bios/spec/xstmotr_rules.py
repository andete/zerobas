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
    """the motor after the call: 1 = stopped"""
    stopped = 1 if c.cpc & 0x10 else 0
    if c.ca == 0:
        return 1
    if c.ca & 0x80:
        return 1 - stopped
    return 0


def and_flags(a):
    """the flags AND A leaves: S, Z, H (always), the copies of bits 5 and 3, P (even parity)"""
    return ((a & 0xA8) | (0x40 if a == 0 else 0) | 0x10 | (0 if bin(a).count("1") & 1 else 4))


def want_f(c):
    if after(c):
        return 0x54
    return 0x10 if c.ca & 0x80 else and_flags(c.ca)


RULES = [
    Rule("R-SM-MOTOR", S1, "The motor relay (port C bit 4, 0 = running): A 0 stops it; an A with bit 7 set toggles it "
         "($80, $81, $FE, $FF measured, from both states); any other A ($01, $02, $03, $28, $40, $7F, from both "
         "states) starts it. Port C's other bits are kept (bits 5-7 and the low nibble varied; the low nibble is not "
         "compared where interrupts are on after the call: the timer interrupt selects its key row).", ALL,
         lambda c: (c.aa ^ ((c.cpc & ~0x10) | (after(c) << 4))) & (0xF0 if c.iff else 0xFF) == 0),
    Rule("R-SM-AF", S1, "A := the PPI bit command left behind: $09 (bit 4 set: stopped) or $08 (reset: running). F, "
         "whatever it was: $54 when the motor ends stopped; when it ends running, $10 for an A with bit 7 set, otherwise "
         "the flags AND A gives on A ($10 for $01 / $02 / $40, $14 for $03, $3C for $28, $38 for $7F).", ALL,
         lambda c: (c.a, c.f) == ((0x09 if after(c) else 0x08), want_f(c))),
    Rule("R-SM-KEEP", S1, "BC, DE, HL and the interrupt state are kept.", ALL,
         lambda c: (c.bc, c.de, c.hl, c.iff) == (0x1357, 0x9BDF, 0x2468, c.ei)),
]
