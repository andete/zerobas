#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/WRTPSG.md's EXECUTABLE RULES (docs/spec-method.md §3a): WRTPSG ($0093) -- probes/bios/spec/xsnd1.asm, op 0
(the loader is xsnd1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xsnd1_model as G  # noqa: E402

PAGE = "docs/bios/WRTPSG.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(0)


S1 = "1. WRTPSG ($0093): write a PSG register"
ALL = lambda c: True  # noqa: E731


def psg_after(c):
    r = list(G.PSGPRE)
    if c.ca < 14:
        r[c.ca] = c.cde & 0xFF
    return tuple(r)


RULES = [
    Rule("R-WP-REG", S1, "PSG register A := E for A 0-13; the other registers R0-R13 are "
         "kept (R0, R1, R2, R7, R8, R13 measured; R7 $BF and $3F, so written whole). A 14 (port A, an input), 15, 16 and $40 "
         "change none of R0-R13. (R14 / R15 after the call are not "
         "compared: interrupts are on after it, and the timer interrupt itself selects through R15.)", ALL,
         lambda c: c.psg[:14] == psg_after(c)),
    G.keep_rule("WP", S1, "A, F, BC, DE, HL, IX and IY are kept; the PPI port C's high nibble (bit 7 the 1-bit sound) "
                "and the queue cells are kept. (Its low nibble, the keyboard row, is the timer interrupt's.)",
                lambda c: (c.a, c.f, c.bc, c.de, c.hl) == (c.ca, c.cf, c.cbc, c.cde, c.chl) and G.ixiy(c)
                and c.aa & 0xF0 == G.aa_in(c) & 0xF0 and c.quetab == c.q[:28] and c.cells == c.q[28:32] and G.win_kept(c)),
    Rule("R-WP-EI", S1, "Interrupts are on after the call, whether they were on or off before it.", ALL,
         lambda c: c.iff == 1),
]
