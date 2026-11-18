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
                     "7 (CLOC's own low bits, whatever GRPCGP is: $2007 with $2004 moves to $2100); CMASK is kept.", "It stops -- CLOC and CMASK kept, A = 0, the carry set -- at the bottom: in "
                     "SCREEN 2 when CLOC AND 7 is 7 and CLOC is GRPCGP + $1700 or more, both unsigned 16-bit (GRPCGP "
                     "$0000-$2100 measured; $36FF and, with $2008, $3707 move on; with $2005-$2007, $3707 stops; $8007, "
                     "$96FF, $9707 with $0000 stop; $0F07 with $2000 -- below GRPCGP -- moves on); in SCREEN 3 when "
                     "CLOC AND 7 is 7 and CLOC's high byte is 5 or more, unsigned ($85 stops, $04FF moves on), whatever "
                     "MLTCGP is ($0000, $0800, $1000 measured: with MLTCGP $1000 every block row 7 stops). Otherwise "
                     "the carry is clear.")
