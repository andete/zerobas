#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/TUPC.md's EXECUTABLE RULES (docs/spec-method.md §3a): TUPC ($0105) -- probes/bios/spec/xgfx2.asm, op 3
(the loader and the model are xgfx2_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xgfx2_model as G  # noqa: E402

PAGE = "docs/bios/TUPC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(3)


S1 = "1. TUPC ($0105): move the graphics position up, checking the edge"

RULES = G.move_rules("TU", S1, "Where it does not stop, as UPC: CLOC := CLOC - 1, or CLOC - $F9 when CLOC AND 7 is 0; "
                     "CMASK is kept.", "It stops -- CLOC and CMASK kept, A = 0, the carry set -- at the top: in "
                     "SCREEN 2 when CLOC AND 7 is 0 and CLOC is below GRPCGP ($F3CB) + $100, both unsigned 16-bit "
                     "(GRPCGP $0000-$2100 measured; with $2001-$2004, CLOC $2100 stops; a CLOC below GRPCGP stops -- "
                     "$0008 with $2000 -- and $8000 / $8100 with $0000 move on); in SCREEN 3 when CLOC AND $FF07 is 0, "
                     "whatever MLTCGP is ($0000, $0800, $1000 measured; $00F8 stops, $2020 and $8020 move on). "
                     "Otherwise the carry is clear.")
