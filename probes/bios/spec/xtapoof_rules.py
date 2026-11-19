#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/TAPOOF.md's EXECUTABLE RULES (docs/spec-method.md §3a): TAPOOF ($00F0) -- probes/bios/spec/xtap1.asm (the loader is
xtap1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xtap1_model as G  # noqa: E402

PAGE = "docs/bios/TAPOOF.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load("TAPOOF", "XT")


S1 = "1. TAPOOF ($00F0): stop writing the tape"
ALL = lambda c: True  # noqa: E731


RULES = [
    Rule("R-TO-MOTOR", S1, "The motor stops (port C bit 4 := 1); bits 5-7 are kept.", ALL,
         lambda c: c.aa & 0xF0 == (c.cpc & 0xE0) | 0x10),
    Rule("R-TO-KEEP", S1, "A, F, BC, DE and HL are kept, whatever they were.", ALL, G.regs_kept),
    Rule("R-TO-EI", S1, "Interrupts are on after the call, whether they were on or off before it.", ALL,
         lambda c: c.iff == 1),
]
