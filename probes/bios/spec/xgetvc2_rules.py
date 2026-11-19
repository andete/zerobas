#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/GETVC2.md's EXECUTABLE RULES (docs/spec-method.md §3a): GETVC2 ($0153) -- probes/bios/spec/xsnd1.asm, op 6
(the loader is xsnd1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xsnd1_model as G  # noqa: E402

PAGE = "docs/bios/GETVC2.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(6)


S1 = "1. GETVC2 ($0153): get an address in the current voice buffer"
ALL = lambda c: True  # noqa: E731


RULES = [
    Rule("R-G2-HL", S1, "HL := VCBA ($FB41) + 37 x VOICEN ($FB38) + L (VOICEN 0, 1, 2; L 0, 5, 7, 36 measured); H on "
         "entry is not used.", ALL, lambda c: c.hl == G.VCBA + 37 * c.q[29] + (c.chl & 0xFF)),
    Rule("R-G2-AF", S1, "A := 0; F := $44 for voice 0, $42 for the others.", ALL,
         lambda c: (c.a, c.f) == (0, 0x44 if c.q[29] == 0 else 0x42)),
    G.keep_rule("G2", S1, "BC, DE, IX, IY and the interrupt state are kept; the queue cells are kept.",
                lambda c: (c.bc, c.de, c.iff) == (c.cbc, c.cde, c.ei) and G.ixiy(c) and c.psg[:14] == G.PSGPRE
                and G.aa_ok(c) and c.quetab == c.q[:28] and c.cells == c.q[28:32] and G.win_kept(c)),
]
