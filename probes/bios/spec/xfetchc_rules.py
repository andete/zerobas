#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/FETCHC.md's EXECUTABLE RULES (docs/spec-method.md §3a): FETCHC ($0114) -- probes/bios/spec/xgfx1.asm, op 0
(the loader is xgfx1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx1_model as G  # noqa: E402

PAGE = "docs/bios/FETCHC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(0)


S1 = "1. FETCHC ($0114): read the current graphics position"
ALL = lambda c: True  # noqa: E731

RULES = [
    Rule("R-FC-OUT", S1, "HL := CLOC ($F92A) and A := CMASK ($F92C), the current position's address and mask (CLOC "
         "$5A5A / CMASK $A5, and $1234 / $40).", ALL, lambda c: c.hl == c.cclo and c.a == c.ccm),
    G.keep_rule("FC", S1, "F, BC, DE, IX, IY, the interrupt state and the work area recorded (CLOC, CMASK, ATRBYT, "
                "ASPCT1 / ASPCT2, SCRMOD, GRPCGP / MLTCGP) are kept.",
                ["f", "bc", "de", "ix", "iy", "iff", "cloc", "cmask", "atrbyt", "aspct", "scrmod", "cgp"]),
]
