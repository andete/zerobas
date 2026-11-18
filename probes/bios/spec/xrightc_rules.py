#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/RIGHTC.md's EXECUTABLE RULES (docs/spec-method.md §3a): RIGHTC ($00FC) -- probes/bios/spec/xgfx2.asm, op 0
(the loader and the model are xgfx2_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xgfx2_model as G  # noqa: E402

PAGE = "docs/bios/RIGHTC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(0)


S1 = "1. RIGHTC ($00FC): move the graphics position one pixel right"

RULES = G.move_rules("RC", S1, "SCREEN 2: CMASK shifts right one bit; from $01 it becomes $80 and CLOC := CLOC + 8 (the "
                     "next 8-pixel cell). SCREEN 3: CMASK $0F becomes $F0 and CLOC := CLOC + 8; any other CMASK becomes $0F ($F0, and $F1, CLOC kept). No "
                     "edge is checked: from the right edge CLOC goes on into the next row's cells.")
