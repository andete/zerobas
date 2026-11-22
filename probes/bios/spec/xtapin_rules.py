#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/TAPIN.md's EXECUTABLE RULES (docs/spec-method.md §3a): TAPIN ($00E4) -- probes/bios/spec/xtap1.asm (the loader is
xtap1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xtap1_model as G  # noqa: E402

PAGE = "docs/bios/TAPIN.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load("TAPIN", "XTL")


S1 = "1. TAPIN ($00E4): read a byte from the tape"
ALL = lambda c: True  # noqa: E731


RULES = [
    Rule("R-TP-A", S1, "A := the next byte written, in order ($00, $55, $AA, $FF, $01, $80, $7F, $FE), the carry clear (set on entry or "
         "not) -- when the calls come back to back (see the evidence).", ALL,
         lambda c: (c.a, c.f & 1) == (G.WRITTEN[c.ca], 0)),
]
