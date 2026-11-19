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
    return 7, 0x02, 0x0001, (qn, vn, 7, pc - 1), {0xFB41: 0x01, 0xFB42: 0x00}


RULES = [
    Rule("R-ST-PLAY", S1, "MUSICF ($FB3F) not 0 (music playing): nothing changes. MUSICF 0 and PLYCNT ($FB40) 0: nothing "
         "changes. MUSICF 0 and PLYCNT not 0: PLYCNT := PLYCNT - 1, MUSICF := 7 (all three voices) and voice A's "
         "first word (VCBA, $FB41) := 1. Queues, QUEUEN and VOICEN are kept.", ALL,
         lambda c: c.cells == start(c)[3] and c.quetab == c.q[:28] and G.win_kept(c, start(c)[4])),
    Rule("R-ST-REGS", S1, "Playing: A := MUSICF, F its OR flags, HL kept. Nothing to play: A := 0, F := $44, HL := $FB40. "
         "Started: A := 7, F := $02, HL := 1.", ALL, lambda c: (c.a, c.f, c.hl) == start(c)[:3]),
    G.keep_rule("ST", S1, "BC, DE, IX, IY and the interrupt state are kept; the PSG and the PPI port C are kept.",
                lambda c: (c.bc, c.de, c.iff) == (c.cbc, c.cde, c.ei) and G.ixiy(c) and c.psg[:14] == G.PSGPRE
                and c.aa == G.aa_in(c)),
]
