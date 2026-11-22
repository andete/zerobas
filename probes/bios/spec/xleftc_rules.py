#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
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

RULES = G.move_rules("LC", S1, "SCREEN 2: CMASK rotates left one bit -- the bit rotated out comes back in at bit 0 "
                     "($C0 gives $81, $81 gives $03) -- and when that bit was set CLOC := CLOC - 8 ($03 gives $06, "
                     "CLOC kept). SCREEN 3: with CMASK's bit 7 set ($F0, $80, $F1, $8F, $FF) CMASK := $0F and CLOC := CLOC - 8; "
                     "with it clear ($0F, $1F, $4F, $70) CMASK := $F0, CLOC kept. No edge is checked: from $0000 CLOC "
                     "wraps to $FFF8.")
