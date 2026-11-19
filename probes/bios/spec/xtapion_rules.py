#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/TAPION.md's EXECUTABLE RULES (docs/spec-method.md §3a): TAPION ($00E1) -- probes/bios/spec/xtap1.asm (the loader is
xtap1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xtap1_model as G  # noqa: E402

PAGE = "docs/bios/TAPION.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load("TAPION", "XTW")


S1 = "1. TAPION ($00E1): start reading the tape"
ALL = lambda c: True  # noqa: E731


RULES = [
    Rule("R-TA-OK", S1, "On the leader TAPOON wrote, the carry is clear -- set on entry too: the reader locked on. (A, BC, DE and HL are "
         "left holding working values, the group `XTW`.)", ALL, lambda c: c.f & 1 == 0),
    Rule("R-TA-MOTOR", S1, "The motor runs (port C bit 4 := 0); interrupts are off after the call.", ALL,
         lambda c: G.motor(c) == 0 and c.iff == 0),
    Rule("R-TA-PORT", S1, "Port C: bits 5-7 kept, bit 4 := 0 (the motor on), the low nibble (the keyboard row "
         "select) := 7 -- $50 gives $47, $F8 $E7. (Unlike TAPOON, bit 5 -- the cassette output -- is kept.)", ALL,
         lambda c: c.aa == (c.cpc & 0xE0) | 0x07),
]
