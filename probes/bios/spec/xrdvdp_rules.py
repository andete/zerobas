#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/RDVDP.md's EXECUTABLE RULES (docs/spec-method.md §3a): RDVDP ($013E) -- the run docs/bios/WRTVDP.md
reads (probes/bios/spec/xvdpreg.asm, op 3; the loader is xwrtvdp_rules.load)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xwrtvdp_rules as W  # noqa: E402

PAGE = "docs/bios/RDVDP.md"
OUTPUTS = W.OUTPUTS


def cases():
    return W.load(3)


S1 = "1. RDVDP ($013E): read the VDP status"
ALL = lambda c: True  # noqa: E731

RULES = [
    Rule("R-RV-FRAME", S1, "A is the VDP status: with no sprite on the screen (sprite 0's Y $D0) it is $80 after a wait "
         "of more than a frame since the status was last read (B = 1), and $00 without one (B = 0) -- bit 7, the frame "
         "flag, set by the VDP once a frame.", lambda c: c.bb in (0, 1), lambda c: c.a == (0x80 if c.bb == 1 else 0x00)),
    Rule("R-RV-CLEAR", S1, "The read clears the frame flag: after the same wait (which gives $80 in the B = 1 cases), an "
         "RDVDP of the probe's own and then the recorded one, the second returns $00 (B = 3).", lambda c: c.bb == 3, lambda c: c.a == 0x00),
    Rule("R-RV-SPR", S1, "With five sprites on one line at the same place, read a little over a frame after the frame "
         "flag was seen (B = 2), A = $E4: the frame flag, the fifth-sprite flag (bit 6) with that sprite's number (4) "
         "in bits 4-0, and the coincidence flag (bit 5).", lambda c: c.bb == 2, lambda c: c.a == 0xE4),
    Rule("R-RV-KEEP", S1, "F, B, C, DE, HL, IX and IY are kept, and so is the interrupt state (off, or on). RG0SAV-RG7SAV "
         "and $F3E7-$F3EE (STATFL among them) keep their bytes, and the VDP registers keep theirs.", ALL,
         lambda c: (c.f == c.ef and c.b == c.bb and c.c == c.cc and c.moved == 0 and c.iff == c.ei
                    and (c.sav, c.e7) == (tuple(W.presav(c)[:8]), tuple(W.presav(c)[8:]))
                    and c.vdp == W.VPRE)),
]
