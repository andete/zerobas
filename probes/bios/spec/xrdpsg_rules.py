#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/RDPSG.md's EXECUTABLE RULES (docs/spec-method.md §3a): RDPSG ($0096) -- probes/bios/spec/xsnd1.asm, op 1
(the loader is xsnd1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xsnd1_model as G  # noqa: E402

PAGE = "docs/bios/RDPSG.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(1)


S1 = "1. RDPSG ($0096): read a PSG register"
ALL = lambda c: True  # noqa: E731


RULES = [
    Rule("R-RP-A", S1, "A := PSG register A as its port reads it, for A 0-15 (R0-R13 the preset, R14 port A's input "
         "$BF, R15 $CF); A := $FF for A 16 and $40.", ALL,
         lambda c: c.a == (c.psg[c.ca] if c.ca < 16 else 0xFF)),
    G.keep_rule("RP", S1, "F, BC, DE, HL, IX, IY and the interrupt state are kept; the PSG registers (R0-R13 the preset, "
                "R15 $CF), the PPI port C (its high nibble only when interrupts are on: the timer interrupt sets the keyboard "
                "row) and the queue cells are kept.",
                lambda c: (c.f, c.bc, c.de, c.hl, c.iff) == (c.cf, c.cbc, c.cde, c.chl, c.ei) and G.ixiy(c)
                and c.psg[:14] == G.PSGPRE and (c.ei or c.psg[15] == 0xCF)
                and (c.aa if not c.ei else c.aa & 0xF0) == (G.aa_in(c) if not c.ei else G.aa_in(c) & 0xF0) and c.quetab == c.q[:28] and c.cells == c.q[28:32] and G.win_kept(c)),
]
