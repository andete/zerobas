#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CALATR.md's EXECUTABLE RULES (docs/spec-method.md §3a): CALATR ($0087) -- the run the sprite table calls share
(probes/bios/spec/xspr.asm, op 1; the loader is xspr_rules)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xspr_rules as P  # noqa: E402

PAGE = "docs/bios/CALATR.md"
OUTPUTS = P.OUTPUTS


def cases():
    return P.load(1)


S1 = "1. CALATR ($0087): the address of a sprite attribute entry"
ALL = lambda c: True  # noqa: E731
SIZE = lambda c: 32 if c.crg1 & 2 else 8  # noqa: E731

RULES = [
    Rule("R-CA-HL", S1, "HL := ATRBAS ($F928) + 4 x A, wrapping at 16 bits, whatever RG1SAV holds ($E0, $E2, $E3, $00, "
         "$02, $FD, $FF). A 0-$FF; ATRBAS $1B00, $FFFE, $ABCD, $1234, $0F00, $3F00.", ALL, lambda c: c.hl == (c.catr + 4 * c.ca) & 0xFFFF),
    Rule("R-CA-DE", S1, "DE := 4 x A, the offset added; A is kept.", ALL, lambda c: c.de == 4 * c.ca and c.a == c.ca),
    Rule("R-CA-F", S1, "F: H, C and bits 5 / 3 as ADD HL,DE leaves them (H the carry out of bit 11, C out of bit 15, bits "
         "5 / 3 from the sum's high byte), N clear; S, Z and P/V as on entry, each on its own ($00, $FF, $04, $A5, $5A).", ALL,
         lambda c: c.f == P.add_flags(c.catr, 4 * c.ca) | (c.cf & 0xC4)),
    Rule("R-CA-KEEP", S1, "BC, IX and IY are kept (two sets of values).", ALL, lambda c: P.kept(c, ["bc", "ix", "iy"])),
    P.cells_rule("CA", S1),
]
