#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/STOREC.md's EXECUTABLE RULES (docs/spec-method.md §3a): STOREC ($0117) -- probes/bios/spec/xgfx1.asm, op 1
(the loader is xgfx1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx1_model as G  # noqa: E402

PAGE = "docs/bios/STOREC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(1)


S1 = "1. STOREC ($0117): set the current graphics position"
ALL = lambda c: True  # noqa: E731

RULES = [
    Rule("R-SC-IN", S1, "CLOC ($F92A) := HL and CMASK ($F92C) := A (HL $2345, $0000, $FFFF; A $10, $00, $FF).", ALL,
         lambda c: c.cloc == c.chl and c.cmask == c.ca),
    G.keep_rule("SC", S1, "A, F, BC, DE, HL, IX, IY, the interrupt state, ATRBYT, ASPCT1 / ASPCT2 and SCRMOD are kept.",
                ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "atrbyt", "aspct", "scrmod"]),
]
