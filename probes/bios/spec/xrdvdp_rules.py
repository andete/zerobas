#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/RDVDP.md's EXECUTABLE RULES (docs/spec-method.md §3a): RDVDP ($013E) -- the run docs/bios/WRTVDP.md
reads (probes/bios/spec/xvdpreg.asm, op 3; the loader is xwrtvdp_rules.load). The two sprite cases are the group
`XVS`: there only A's bits 7 and 5 are outputs (`afc`) -- see the page."""
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
PLAIN = lambda c: c.src == "XV"  # noqa: E731
SPR = lambda c: c.src == "XVS"  # noqa: E731
ALL = lambda c: True  # noqa: E731

RULES = [
    Rule("R-RV-FRAME", S1, "A is the VDP status: with no sprite on the screen (sprite 0's Y $D0) it is $80 after a wait "
         "of more than a frame since the probe last read the status, and $00 without one -- bit 7, the frame flag, "
         "set by the VDP once a frame and cleared by the read.", PLAIN,
         lambda c: c.a == (0x80 if c.bb == 1 else 0x00)),
    Rule("R-RV-SPR", S1, "With five sprites on one line at the same place, after the wait, bits 7 and 5 are both set: "
         "the frame flag, and the coincidence flag (two sprites' pixels overlap).", SPR,
         lambda c: c.afc == 0xA0),
    Rule("R-RV-KEEP", S1, "F, B, C, DE, HL, IX and IY are kept, and so is the interrupt state (off, or on). RG0SAV-RG7SAV "
         "and $F3E7-$F3EE (STATFL among them) keep their bytes, and the VDP registers keep theirs.", ALL,
         lambda c: (c.f == c.ef and c.b == c.bb and c.c == c.cc and c.moved == 0 and c.iff == c.ei
                    and (c.sav, c.e7) == (tuple(W.presav(c)[:8]), tuple(W.presav(c)[8:]))
                    and c.vdp == W.VPRE)),
]
