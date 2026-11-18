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
                     "CMASK is kept.", "It stops -- CLOC and CMASK kept, the carry set -- at the top: in SCREEN 2 when "
                     "CLOC AND 7 is 0 and CLOC's high byte is GRPCGP's ($F3CB; GRPCGP $0000, $1800, $2000 measured); in "
                     "SCREEN 3 when CLOC AND $FF07 is 0, whatever MLTCGP is ($0000, $0800, $1000 measured). Otherwise "
                     "the carry is clear.")
