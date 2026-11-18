#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/GSPSIZ.md's EXECUTABLE RULES (docs/spec-method.md §3a): GSPSIZ ($008A) -- the run the sprite table calls share
(probes/bios/spec/xspr.asm, op 2; the loader is xspr_rules)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xspr_rules as P  # noqa: E402

PAGE = "docs/bios/GSPSIZ.md"
OUTPUTS = P.OUTPUTS


def cases():
    return P.load(2)


S1 = "1. GSPSIZ ($008A): the sprite size"
ALL = lambda c: True  # noqa: E731
SIZE = lambda c: 32 if c.crg1 & 2 else 8  # noqa: E731

RULES = [
    Rule("R-GS-A", S1, "A := 8 when RG1SAV's bit 1 is 0 (8 x 8 sprites), 32 when it is 1 (16 x 16), and the carry is "
         "that bit; RG1SAV's other bits play no part (RG1SAV $E0-$E3, $00, $FF, $FD, $02).", ALL,
         lambda c: c.a == SIZE(c) and (c.f & 1) == (c.crg1 >> 1) & 1),
    Rule("R-GS-F", S1, "The rest of F: bit 5 is RG1SAV's bit 7 and bit 3 its bit 5 (as rotating it right twice leaves "
         "them); H and N clear; S, Z and P/V as on entry ($00 or $FF).", ALL,
         lambda c: c.f & 0xFE == ((c.crg1 >> 2) & 0x28) | (c.cf & 0xC4)),
    Rule("R-GS-KEEP", S1, "BC, DE, HL, IX and IY are kept (two sets of values).", ALL,
         lambda c: P.kept(c, ["bc", "de", "hl", "ix", "iy"])),
    P.cells_rule("GS", S1),
]
