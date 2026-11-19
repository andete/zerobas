#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CHGCAP.md's EXECUTABLE RULES (docs/spec-method.md §3a): CHGCAP ($0132) -- probes/bios/spec/xinp1.asm, op 2
(the loader is xinp1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xinp1_model as G  # noqa: E402

PAGE = "docs/bios/CHGCAP.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(2, "XI")


S1 = "1. CHGCAP ($0132): switch the CAPS lamp"
ALL = lambda c: True  # noqa: E731
QUIET = ("With interrupts off after the call, the cells the timer interrupt's key scan writes (NEWKEY, OLDKEY, "
         "TRGFLG, the key buffer pointers, PSG R15) are kept; with them on, they are not compared.")


RULES = [
    Rule("R-CC-BIT", S1, "The PPI's port C bit 6 (the CAPS lamp, lit at 0) := 0 when A is 0, 1 for any other A ($01, "
         "$80, $FF measured); its other bits are kept (with interrupts on only the high nibble is compared).", ALL,
         lambda c: c.aa & (0xF0 if c.iff else 0xFF) == ((0x50 & ~0x40) | (0x40 if c.ca else 0)) & (0xF0 if c.iff else 0xFF)),
    Rule("R-CC-AF", S1, "A := $0C when A was 0, $0D otherwise (the PPI bit reset / set command for bit 6); F := $54 / "
         "$08 -- whatever F was on entry.", ALL, lambda c: (c.a, c.f) == ((0x0C, 0x54) if c.ca == 0 else (0x0D, 0x08))),
    G.keep_rule("CC", S1, "BC, DE, HL, IX, IY, INTFLG, CAPST (not changed: only the lamp) and R14 are kept. " + "",
                lambda c: (c.bc, c.de, c.hl) == (c.cbc, c.cde, c.chl) and G.ixiy(c) and G.cells(c) and G.quiet(c)),
    Rule("R-CC-EI", S1, "The interrupt state is kept.", ALL, lambda c: c.iff == c.ei),
]
