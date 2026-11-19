#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/STRTMS.md's EXECUTABLE RULES (docs/spec-method.md §3a): STRTMS ($0099) -- probes/bios/spec/xsnd1.asm, op 8
(the loader is xsnd1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xsnd1_model as G  # noqa: E402

PAGE = "docs/bios/STRTMS.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(8)


S1 = "1. STRTMS ($0099): start the background music"
ALL = lambda c: True  # noqa: E731


def start(c):
    """(A, F, HL, cells, the window's writes)"""
    qn, vn, mf, pc = c.q[28:32]
    if mf:
        return mf, G.logical(mf), c.chl, (qn, vn, mf, pc), {}
    if pc == 0:
        return 0, 0x44, 0xFB40, (qn, vn, mf, pc), {}
    r = pc - 1
    f = (r & 0xA8) | (0x40 if r == 0 else 0) | (0x10 if pc & 0x0F == 0 else 0) | (0x04 if pc == 0x80 else 0) | 0x02
    return 7, f, 0x0001, (qn, vn, 7, r), {0xFB41: 1, 0xFB42: 0, 0xFB66: 1, 0xFB67: 0, 0xFB8B: 1, 0xFB8C: 0}


RULES = [
    Rule("R-ST-PLAY", S1, "MUSICF ($FB3F) not 0 (music playing): nothing changes. MUSICF 0 and PLYCNT ($FB40) 0: nothing "
         "changes. MUSICF 0 and PLYCNT not 0: PLYCNT := PLYCNT - 1 (3, 1 measured), MUSICF := 7 (all three voices) "
         "and each voice's first word ($FB41, $FB66, $FB8B) := 1. Queues, QUEUEN and VOICEN are kept.", ALL,
         lambda c: c.cells == start(c)[3] and c.quetab == c.q[:28] and G.win_kept(c, start(c)[4])),
    Rule("R-ST-REGS", S1, "Playing: A := MUSICF, F its OR flags, HL kept. Nothing to play: A := 0, F := $44, HL := $FB40. "
         "Started: A := 7, F := the flags DEC leaves on PLYCNT ($02 for 3, $42 for 1), HL := 1.", ALL, lambda c: (c.a, c.f, c.hl) == start(c)[:3]),
    G.keep_rule("ST", S1, "BC, DE, IX, IY and the interrupt state are kept; the PSG and the PPI port C are kept.",
                lambda c: (c.bc, c.de, c.iff) == (c.cbc, c.cde, c.ei) and G.ixiy(c) and c.psg[:14] == G.PSGPRE
                and G.aa_ok(c)),
]
