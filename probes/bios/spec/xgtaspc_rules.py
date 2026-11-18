#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/GTASPC.md's EXECUTABLE RULES (docs/spec-method.md §3a): GTASPC ($0126) -- probes/bios/spec/xgfx1.asm, op 3
(the loader is xgfx1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx1_model as G  # noqa: E402

PAGE = "docs/bios/GTASPC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(3)


S1 = "1. GTASPC ($0126): get the aspect ratio"
ALL = lambda c: True  # noqa: E731

RULES = [
    Rule("R-GA-OUT", S1, "DE := ASPCT1 ($F40B) and HL := ASPCT2 ($F40D) ($1234 / $5678, and $0100 / $00C0).", ALL,
         lambda c: (c.de, c.hl) == G.aspct_in(c)),
    G.keep_rule("GA", S1, "A, F, BC, IX, IY, the interrupt state and the work area recorded are kept.",
                ["a", "f", "bc", "ix", "iy", "iff", "cloc", "cmask", "atrbyt", "aspct", "scrmod", "cgp"]),
]
