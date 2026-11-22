#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/CALPAT.md's EXECUTABLE RULES (docs/spec-method.md §3a): CALPAT ($0084) -- the run the sprite table calls share
(probes/bios/spec/xspr.asm, op 0; the loader is xspr_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xspr_model as P  # noqa: E402

PAGE = "docs/bios/CALPAT.md"
OUTPUTS = P.OUTPUTS


def cases():
    return P.load(0)


S1 = "1. CALPAT ($0084): the address of a sprite pattern"
ALL = lambda c: True  # noqa: E731
SIZE = lambda c: 32 if c.crg1 & 2 else 8  # noqa: E731

RULES = [
    Rule("R-CP-HL", S1, "HL := PATBAS ($F926) + A x the pattern size: 8 bytes when RG1SAV's bit 1 is 0 (8 x 8 sprites), 32 "
         "when it is 1 (16 x 16); the sum wraps at 16 bits. RG1SAV's other bits play no part (RG1SAV $E0-$E3, $00, $02, $FD, "
         "$FF, $1E, $82, $22). A 0-$FF; PATBAS $3800, $1234, $FFF8, $FFF0, $8000, $7FF8, $F000.", ALL, lambda c: c.hl == (c.cpat + c.ca * SIZE(c)) & 0xFFFF),
    Rule("R-CP-ADE", S1, "A := the pattern size (8 or 32) and DE := A x that size, the offset added.", ALL,
         lambda c: c.a == SIZE(c) and c.de == c.ca * SIZE(c)),
    Rule("R-CP-F", S1, "F: H, C and bits 5 / 3 as ADD HL,DE leaves them (H the carry out of bit 11, C out of bit 15, bits "
         "5 / 3 from the sum's high byte), N clear; Z set exactly when the sprites are 8 x 8; S and P/V clear, also for a sum with bit 15 set or a signed "
         "overflow; Z clear for a 16 x 16 sum that wraps to $0000 -- whatever F was on entry ($00, $FF, $80, $40).", ALL,
         lambda c: c.f == P.add_flags(c.cpat, c.ca * SIZE(c)) | (0x40 if SIZE(c) == 8 else 0)),
    Rule("R-CP-KEEP", S1, "BC, IX and IY are kept (two sets of values).", ALL, lambda c: P.kept(c, ["bc", "ix", "iy"])),
    P.cells_rule("CP", S1),
]
