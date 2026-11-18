#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/LEFTC.md's EXECUTABLE RULES (docs/spec-method.md §3a): LEFTC ($00FF) -- probes/bios/spec/xgfx2.asm, op 1
(the loader and the model are xgfx2_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xgfx2_model as G  # noqa: E402

PAGE = "docs/bios/LEFTC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(1)


S1 = "1. LEFTC ($00FF): move the graphics position one pixel left"

RULES = G.move_rules("LC", S1, "SCREEN 2: CMASK shifts left one bit; from $80 it becomes $01 and CLOC := CLOC - 8. "
                     "SCREEN 3: CMASK $0F becomes $F0; $F0 becomes $0F and CLOC := CLOC - 8. No edge is checked.")
