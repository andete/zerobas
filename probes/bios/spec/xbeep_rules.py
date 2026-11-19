#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/BEEP.md's EXECUTABLE RULES (docs/spec-method.md §3a): BEEP ($00C0) -- probes/bios/spec/xsnd1.asm, op 9
(the loader is xsnd1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xsnd1_model as G  # noqa: E402

PAGE = "docs/bios/BEEP.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(9)


S1 = "1. BEEP ($00C0): sound the beep"
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


def after(c):
    psg = list(reset(c)[0])
    psg[0], psg[1] = 0x55, 0x00
    return tuple(psg)


RULES = [
    Rule("R-BP-PSG", S1, "After the beep: PSG R0 / R1 := $55 / $00 (channel A's tone), R7 := $B8, R8-R10 := 0; the other "
         "registers kept.", ALL, lambda c: c.psg[:14] == after(c)),
    Rule("R-BP-RESET", S1, "It ends with GICINI's reset: queues 0-2, MUSICF / PLYCNT and the voice buffers as "
         "docs/bios/GICINI.md gives them.", ALL,
         lambda c: (c.quetab, c.cells, c.win) == reset(c)[1:4]),
    Rule("R-BP-REGS", S1, "A := 0, F := $44, BC := 0, E := 7 -- whatever they were; D, HL, IX and IY are kept.", ALL,
         lambda c: (c.a, c.f, c.bc, c.de & 0xFF, c.de >> 8, c.hl) == (0, 0x44, 0, 7, c.cde >> 8, c.chl) and G.ixiy(c)),
    G.keep_rule("BP", S1, "The PPI port C's high nibble is kept (its low nibble is the timer interrupt's).",
                lambda c: c.aa & 0xF0 == G.aa_in(c) & 0xF0),
    Rule("R-BP-EI", S1, "Interrupts are on after the call, whether they were on or off before it.", ALL,
         lambda c: c.iff == 1),
]
