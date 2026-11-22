#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/KILBUF.md's EXECUTABLE RULES (docs/spec-method.md §3a): KILBUF ($0156) -- probes/bios/spec/xinp1.asm, op 1
(the loader is xinp1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xinp1_model as G  # noqa: E402

PAGE = "docs/bios/KILBUF.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(1, "XI")


S1 = "1. KILBUF ($0156): empty the key buffer"
ALL = lambda c: True  # noqa: E731
QUIET = ("With interrupts off after the call, the cells the timer interrupt's key scan writes (NEWKEY, OLDKEY, "
         "TRGFLG, the key buffer pointers, PSG R15) are kept; with them on, they are not compared.")


RULES = [
    Rule("R-KB-BUF", S1, "GETPNT ($F3FA) := PUTPNT ($F3F8): the buffer is empty, the put pointer kept. HL := that "
         "pointer.", ALL, lambda c: (c.putpnt, c.getpnt, c.hl) == (G.PUT0, G.PUT0, G.PUT0)),
    G.keep_rule("KB", S1, "A, F, BC, DE, IX, IY, the PPI port C, INTFLG, CAPST, R14 and the key scan's cells are kept.",
                lambda c: (c.a, c.f, c.bc, c.de) == (c.ca, c.cf, c.cbc, c.cde) and G.ixiy(c) and c.aa == c.cpc and G.cells(c) and G.quiet(c, put=G.PUT0, get=G.PUT0)),
    Rule("R-KB-EI", S1, "The interrupt state is kept.", ALL, lambda c: c.iff == c.ei),
]
