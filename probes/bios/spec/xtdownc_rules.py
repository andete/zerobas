#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/TDOWNC.md's EXECUTABLE RULES (docs/spec-method.md §3a): TDOWNC ($010B) -- probes/bios/spec/xgfx2.asm, op 5
(the loader and the model are xgfx2_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xgfx2_model as G  # noqa: E402

PAGE = "docs/bios/TDOWNC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(5)


S1 = "1. TDOWNC ($010B): move the graphics position down, checking the edge"

RULES = G.move_rules("TD", S1, "Where it does not stop, as DOWNC: CLOC := CLOC + 1, or CLOC + $F9 when CLOC AND 7 is "
                     "7; CMASK is kept.", "It stops -- CLOC and CMASK kept, A = 0, the carry set -- at the bottom: in "
                     "SCREEN 2 when CLOC AND 7 is 7 and CLOC - GRPCGP, 16-bit, is $1700 or more (GRPCGP $0000, $1800, "
                     "$2000, $2100, $2004 measured; with $2004, $3707, $370F and $380F stop; character rows 7 and 15 "
                     "move on); in SCREEN 3 when CLOC AND 7 is 7 and CLOC's high byte is 5 or more, unsigned ($85 "
                     "stops), whatever MLTCGP is ($0000, $0800, $1000 measured: with MLTCGP $1000 every block row 7 "
                     "stops). Otherwise the carry is clear.")
