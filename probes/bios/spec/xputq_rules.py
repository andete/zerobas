#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/PUTQ.md's EXECUTABLE RULES (docs/spec-method.md §3a): PUTQ ($00F9) -- probes/bios/spec/xsnd1.asm, op 4
(the loader is xsnd1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xsnd1_model as G  # noqa: E402

PAGE = "docs/bios/PUTQ.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(4)


S1 = "1. PUTQ ($00F9): put a byte in a queue"
ALL = lambda c: True  # noqa: E731


def put(c):
    """(QUETAB after, window writes, A, F, BC, HL)"""
    e = 6 * c.ca
    q = list(c.q[:28])
    p, g, size = q[e], q[e + 1], q[e + 3]
    adr = q[e + 4] | q[e + 5] << 8
    new = (p + 1) & size
    if new == g:
        return tuple(q), {}, new, 0x42 | (new & 0x28), p << 8 | new, 0xF959 + e + 3
    q[e] = new
    return tuple(q), {adr + new: c.cde & 0xFF}, adr & 0xFF, 0x28, new, 0xF959 + e


RULES = [
    Rule("R-PQ-PUT", S1, "Queue A's put pointer goes to (put + 1) AND size; if that equals get the queue is full: "
         "nothing is written and put is kept. Otherwise put := it and E is stored at the queue's address + the new "
         "put (the first byte stored goes at address + 1). Nothing else in QUETAB changes.", ALL,
         lambda c: c.quetab == put(c)[0] and G.win_kept(c, put(c)[1]) and c.cells == c.q[28:32]),
    Rule("R-PQ-AF", S1, "Full: A := the new put, F := $42 OR (A AND $28) (Z set). Stored: A := the queue address's low "
         "byte, F := $28 (Z clear).", ALL, lambda c: (c.a, c.f) == put(c)[2:4]),
    Rule("R-PQ-REGS", S1, "Full: B := the old put, C := the new put, HL := the queue's QUETAB entry + 3. Stored: B := "
         "0, C := the new put, HL := the entry.", ALL, lambda c: (c.bc, c.hl) == put(c)[4:6]),
    G.keep_rule("PQ", S1, "DE, IX, IY and the interrupt state are kept.",
                lambda c: (c.de, c.iff) == (c.cde, c.ei) and G.ixiy(c) and c.psg[:14] == G.PSGPRE
                and c.aa == G.aa_in(c)),
]
