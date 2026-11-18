#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/UPC.md's EXECUTABLE RULES (docs/spec-method.md §3a): UPC ($0102) -- probes/bios/spec/xgfx2.asm, op 2
(the loader and the model are xgfx2_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xgfx2_model as G  # noqa: E402

PAGE = "docs/bios/UPC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(2)


S1 = "1. UPC ($0102): move the graphics position one pixel up"

RULES = G.move_rules("UC", S1, "CLOC := CLOC - 1, or CLOC - $F9 when CLOC AND 7 is 0 (the line above is in the "
                     "character row above: 256 bytes back, line 7); CMASK is kept. Both screens alike; no edge is "
                     "checked.")
