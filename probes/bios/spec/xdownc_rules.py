#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/DOWNC.md's EXECUTABLE RULES (docs/spec-method.md §3a): DOWNC ($0108) -- probes/bios/spec/xgfx2.asm, op 4
(the loader and the model are xgfx2_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xgfx2_model as G  # noqa: E402

PAGE = "docs/bios/DOWNC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(4)


S1 = "1. DOWNC ($0108): move the graphics position one pixel down"

RULES = G.move_rules("DC", S1, "CLOC := CLOC + 1, or CLOC + $F9 when CLOC AND 7 is 7 (the line below is in the "
                     "character row below); CMASK is kept. Both screens alike; no edge is checked.")
