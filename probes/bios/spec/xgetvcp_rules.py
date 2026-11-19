#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/GETVCP.md's EXECUTABLE RULES (docs/spec-method.md §3a): GETVCP ($0150) -- probes/bios/spec/xsnd1.asm, op 5
(the loader is xsnd1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xsnd1_model as G  # noqa: E402

PAGE = "docs/bios/GETVCP.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(5)


S1 = "1. GETVCP ($0150): get a voice buffer's address"
ALL = lambda c: True  # noqa: E731


def carry(a):
    """the carry out of the last of the A additions of 37"""
    return 1 if a and G.VCBA + 2 + 37 * (a - 1) <= 0xFFFF < G.VCBA + 2 + 37 * a else 0


RULES = [
    Rule("R-GV-HL", S1, "HL := VCBA ($FB41) + 37 x A + 2, 16-bit ($FB43, $FB68, $FB8D; A 3 gives $FBB2, past the third "
         "buffer; A 6 $FC21; A $21 wraps to $0008).", ALL, lambda c: c.hl == (G.VCBA + 37 * c.ca + 2) & 0xFFFF),
    Rule("R-GV-AF", S1, "A := 0; F := $44 for voice 0, $42 for the others -- $43 when the last addition of 37 carries "
         "out of 16 bits (A $21).", ALL,
         lambda c: (c.a, c.f) == (0, 0x44 if c.ca == 0 else 0x42 | carry(c.ca))),
    G.keep_rule("GV", S1, "BC, DE, IX, IY and the interrupt state are kept; the queue cells are kept.",
                lambda c: (c.bc, c.de, c.iff) == (c.cbc, c.cde, c.ei) and G.ixiy(c) and c.psg[:14] == G.PSGPRE
                and G.aa_ok(c) and c.quetab == c.q[:28] and c.cells == c.q[28:32] and G.win_kept(c)),
]
