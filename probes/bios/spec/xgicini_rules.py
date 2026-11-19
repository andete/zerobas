#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/GICINI.md's EXECUTABLE RULES (docs/spec-method.md §3a): GICINI ($0090) -- probes/bios/spec/xsnd1.asm, op 7
(the loader is xsnd1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xsnd1_model as G  # noqa: E402

PAGE = "docs/bios/GICINI.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(7)


S1 = "1. GICINI ($0090): initialise the PSG and the PLAY queues"
ALL = lambda c: True  # noqa: E731


VINIT = {15: 0x04, 16: 0x04, 17: 0x78, 18: 0x88, 19: 0xFF}   # a voice buffer's bytes after the reset; the rest 0


def reset(c):
    """GICINI's state: (PSG R0-R13, QUETAB + QUEBAK, cells, the window's 16 bytes)"""
    psg = list(G.PSGPRE)
    psg[7], psg[8], psg[9], psg[10] = 0xB8, 0, 0, 0
    q = list(c.q[:28])
    for k, adr in enumerate((0xF975, 0xF9F5, 0xFA75)):          # VOICAQ, VOICBQ, VOICCQ
        q[6 * k:6 * k + 6] = [0, 0, 0, 0x7F, adr & 0xFF, adr >> 8]
    cells = (c.q[28], c.q[29], 0, 0)
    win = []
    for a in range(c.cwin, c.cwin + 16):
        if 0xFB41 <= a < 0xFB41 + 111:
            win.append(VINIT.get((a - 0xFB41) % 37, 0))
        elif a == 0xFB38:
            win.append(c.q[29])
        elif a in (0xFB3E,):
            win.append(c.q[28])
        elif a in (0xFB3F, 0xFB40):                     # MUSICF, PLYCNT
            win.append(0)
        elif c.second and (0xFB35 <= a <= 0xFB37 or 0xFB39 <= a <= 0xFB3D):    # XSND1B presets these: kept
            win.append(G.fill(a))
        elif 0xFB30 <= a < 0xFB41:                      # not preset by the probe (XSND1): not compared
            win.append(c.win[a - c.cwin])
        elif a >= 0xFB41 + 111:                         # not preset by the probe: not compared
            win.append(c.win[a - c.cwin])
        else:
            win.append(G.fill(a))
    return tuple(psg), tuple(q), cells, tuple(win)


RULES = [
    Rule("R-GI-PSG", S1, "PSG R7 := $B8 (tones on, noise off, port A in, port B out: from $BF too), R8-R10 (the volumes) "
         ":= 0; R0-R6 and R11-R13 are kept.", ALL, lambda c: c.psg[:14] == reset(c)[0]),
    Rule("R-GI-QUE", S1, "Queues 0-2 in QUETAB: put, get and the back flag := 0, size := $7F, the address := VOICAQ / VOICBQ / "
         "VOICCQ ($F975 / $F9F5 / $FA75; from $F9F0 and size $7E too); queue 3 "
         "and QUEBAK are kept. MUSICF ($FB3F) and PLYCNT ($FB40) := 0; QUEUEN and VOICEN are kept.", ALL,
         lambda c: (c.quetab, c.cells) == reset(c)[1:3]),
    Rule("R-GI-VCB", S1, "The three 37-byte voice buffers from VCBA ($FB41) := 0, except bytes 15-19 of each := $04 $04 "
         "$78 $88 $FF. The queue buffers are not cleared; $FB35-$FB37 and $FB39-$FB3D (PRSCNT, SAVSP, SAVVOL, MCLLEN, "
         "MCLPTR) are kept (XSND1B presets them).", ALL, lambda c: c.win == reset(c)[3]),
    G.keep_rule("GI", S1, "A, F, BC, DE, HL, IX and IY are kept; the PPI port C's high nibble is kept (its low nibble is "
                "the timer interrupt's).", lambda c: (c.a, c.f, c.bc, c.de, c.hl) == (c.ca, c.cf, c.cbc, c.cde, c.chl)
                and G.ixiy(c) and c.aa & 0xF0 == G.aa_in(c) & 0xF0),
    Rule("R-GI-EI", S1, "Interrupts are on after the call, whether they were on or off before it.", ALL,
         lambda c: c.iff == 1),
]
