#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CHGCLR.md's EXECUTABLE RULES (docs/spec-method.md §3a): CHGCLR ($0062) -- probes/bios/spec/xclr.asm, op 1
(the loader and the VRAM model are xclr_rules)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xclr_rules as X  # noqa: E402

PAGE = "docs/bios/CHGCLR.md"
OUTPUTS = X.OUTPUTS


def cases():
    return X.load(1)


S1 = "1. CHGCLR ($0062): set the screen colours"
ALL = lambda c: True  # noqa: E731


def fb(c):
    return ((c.fo << 4) | c.ba) & 0xFF


def text(c):
    """the SCREEN 0 path: SCRMOD - 1 negative as a signed byte (measured: SCRMOD 0 and $FF)"""
    return ((c.cscr - 1) & 0xFF) >= 0x80


def r7(c):
    return fb(c) if text(c) else c.bd


def writes(c):
    return {(c.t32col + i) & 0x3FFF: fb(c) for i in range(32)} if c.cscr == 1 else {}


RULES = [
    Rule("R-CC-R7", S1, "VDP register R#7 and RG7SAV := (FORCLR x 16) OR BAKCLR, as a byte, when SCRMOD - 1 is negative as a "
         "signed byte -- SCRMOD 0, $81, $FF; BDRCLR otherwise -- SCRMOD 1, 2, 3, 4, $10, $77, $80. Colours over 15 are used as "
         "they are (FORCLR $10, BAKCLR $25 give $25, not $05; FORCLR $1F, BAKCLR 0 give $F0 -- a shift, not a rotate; BDRCLR $3C). The other registers, RG0SAV-RG6SAV, SCRMOD "
         "and the colour cells are not changed.", ALL,
         lambda c: (c.vdp == X.VPRE[:7] + (r7(c),) and c.sav == (0xA5, c.crg1) + (0xA5,) * 5 + (r7(c),)
                    and c.scrmod == c.cscr and c.colours == (c.fo, c.ba, c.bd))),
    X.vram_rule("CC", S1, "In SCREEN 1 (SCRMOD 1) the 32-byte colour table at T32COL ($F3BF) := (FORCLR x 16) OR "
                "BAKCLR, T32COL taken AND $3FFF and the 32 bytes wrapping from $3FFF to $0000 (T32COL $FFFF); in the other "
                "modes VRAM is not written. T32COL, not RG3SAV, gives the place.", writes),
    Rule("R-CC-REGS", S1, "On return, on the SCREEN 0 path: A = R#7's new value, F = $A4 (whatever the colour byte: $F4, "
         "$A5, $FF, $25, $12), BC = $0007, HL = $F3EA, DE kept; in SCREEN 1: A = the colour byte, F its flags as an OR "
         "leaves them, BC = 0, HL = T32COL, DE kept; in the other modes A = SCRMOD - 1 with F as DEC A leaves it (the "
         "half-borrow at $10, the overflow at $80) and the entry carry kept, BC = $0007, DE and HL kept. IX and IY are kept.", ALL,
         lambda c: regs(c)),
    Rule("R-CC-EI", S1, "Interrupts are on after the call, whether they were on or off before it.", ALL,
         lambda c: c.iff == 1),
]


def logical(v):
    f = (v & 0xA8) | (0x40 if v == 0 else 0)
    return f | (0x04 if bin(v).count("1") % 2 == 0 else 0)


def regs(c):
    kept_ix = (c.ix, c.iy) == (X.marker(c, 0x4321), X.marker(c, 0x8765))
    de = X.marker(c, 0x9BDF)
    hl = X.marker(c, 0x2468)
    if text(c):
        want = (r7(c), 0xA4, 0x0007, de, 0xF3EA)
    elif c.cscr == 1:
        want = (fb(c), logical(fb(c)), 0, de, c.t32col)
    else:
        r = (c.cscr - 1) & 0xFF
        f = (r & 0xA8) | (0x40 if r == 0 else 0) | (0x10 if c.cscr & 0x0F == 0 else 0) | \
            (0x04 if c.cscr == 0x80 else 0) | 0x02 | (c.cf & 0x01)
        want = (r, f, 0x0007, de, hl)
    return kept_ix and (c.a, c.f, c.bc, c.de, c.hl) == want
