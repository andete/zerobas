#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/LFTQ.md's EXECUTABLE RULES (docs/spec-method.md §3a): LFTQ ($00F6) -- probes/bios/spec/xsnd1.asm, op 3
(the loader is xsnd1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xsnd1_model as G  # noqa: E402

PAGE = "docs/bios/LFTQ.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(3)


S1 = "1. LFTQ ($00F6): room left in a queue"
ALL = lambda c: True  # noqa: E731


def entry(c):
    return c.q[6 * c.ca:6 * c.ca + 6]


def room(c):
    put, get, bak, size = entry(c)[:4]
    return (get - ((put + 1) & size)) & size


RULES = [
    Rule("R-LQ-HL", S1, "For queue A (0-3; QUETAB $F959, 6 bytes each: put, get, back flag, size, address): HL := (get - "
         "((put + 1) AND size)) AND size, the bytes free -- with a size of 2^n - 1 that is (get - put - 1) mod 2^n; "
         "with $7E, put 2 and get $50 it gives $4E; the back flag is not used. A := L, F its flags as an AND leaves them (H "
         "set).", ALL,
         lambda c: (c.hl, c.a, c.f) == (room(c), room(c), G.logical(room(c)) | 0x10)),
    Rule("R-LQ-BC", S1, "B := (put + 1) AND size, C := get.", ALL,
         lambda c: c.bc == (((entry(c)[0] + 1) & entry(c)[3]) << 8 | entry(c)[1])),
    G.keep_rule("LQ", S1, "DE, IX, IY and the interrupt state are kept; QUETAB, the queue cells and the buffers are "
                "kept (the window recorded: queue 0, 1, 2 or 3's first 16 bytes); the PSG registers R0-R13 and the PPI port C "
                "are kept.", lambda c: (c.de, c.iff) == (c.cde, c.ei) and G.ixiy(c) and c.psg[:14] == G.PSGPRE and G.aa_ok(c)
                and c.quetab == c.q[:28] and c.cells == c.q[28:32] and G.win_kept(c)),
]
