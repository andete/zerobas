#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CHGSND.md's EXECUTABLE RULES (docs/spec-method.md §3a): CHGSND ($0135) -- probes/bios/spec/xsnd1.asm, op 2
(the loader is xsnd1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xsnd1_model as G  # noqa: E402

PAGE = "docs/bios/CHGSND.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(2)


S1 = "1. CHGSND ($0135): switch the 1-bit sound port"
ALL = lambda c: True  # noqa: E731


RULES = [
    Rule("R-CS-BIT", S1, "The PPI's port C bit 7 (the 1-bit sound) := 0 when A is 0, 1 for any other A ($01, $02, $80, "
         "$FF measured); its other bits are kept ($50 / $2F preset; with interrupts on only the high nibble is compared: the "
         "timer interrupt sets the keyboard row).", ALL,
         lambda c: c.aa & (0xF0 if c.ei else 0xFF) == ((G.aa_in(c) & 0x7F) | (0x80 if c.ca else 0)) & (0xF0 if c.ei else 0xFF)),
    Rule("R-CS-AF", S1, "A := $0E when A was 0, $0F otherwise (the PPI bit set / reset command for bit 7); F := $54 / "
         "$08 -- whatever F was on entry.", ALL,
         lambda c: (c.a, c.f) == ((0x0E, 0x54) if c.ca == 0 else (0x0F, 0x08))),
    G.keep_rule("CS", S1, "BC, DE, HL, IX, IY and the interrupt state are kept; the PSG registers and the queue cells "
                "are kept.",
                lambda c: (c.bc, c.de, c.hl, c.iff) == (c.cbc, c.cde, c.chl, c.ei) and G.ixiy(c)
                and c.psg[:14] == G.PSGPRE and c.quetab == c.q[:28] and c.cells == c.q[28:32] and G.win_kept(c)),
]
