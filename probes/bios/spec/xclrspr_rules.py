#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/CLRSPR.md's EXECUTABLE RULES (docs/spec-method.md §3a): CLRSPR ($0069) -- probes/bios/spec/xclr.asm, op 0
(the loader and the VRAM model are xclr_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xclr_model as X  # noqa: E402

PAGE = "docs/bios/CLRSPR.md"
OUTPUTS = X.OUTPUTS


def cases():
    return X.load(0)


S1 = "1. CLRSPR ($0069): clear all sprites"
ALL = lambda c: True  # noqa: E731
BIG = lambda c: c.crg1 & 2  # noqa: E731


def writes(c):
    w = {(c.cpat + i) & 0x3FFF: 0 for i in range(2048)}
    for k in range(32):
        a = c.catr + 4 * k
        w[a & 0x3FFF] = 0xD1
        w[(a + 2) & 0x3FFF] = (4 * k if BIG(c) else k) & 0xFF
        w[(a + 3) & 0x3FFF] = c.fo
    return w


RULES = [
    X.vram_rule("CS", S1, "With RG1SAV's bit 7 set (16 KB addressing): the sprite pattern table -- 2048 bytes from PATBAS ($F926) -- := 0. In the attribute table from "
                "ATRBAS ($F928), sprite k's entry gets Y := $D1 (209), its pattern number := k, or 4 x k when RG1SAV's "
                "bit 1 is set (16 x 16 sprites -- bit 0, magnification, plays no part: RG1SAV $E1), and its colour := FORCLR as it is (a byte over 15 too: $FF); its X is "
                "not written. The pattern table is cleared first and the attributes written after it: where the two "
                "overlap, the attributes stay. The bases are taken AND $3FFF (ATRBAS $5B00, $9B00 and PATBAS $B800 "
                "write where $1B00 and $3800 would) and the addresses wrap from $3FFF to $0000. Nothing else in VRAM changes. Whatever "
                "SCRMOD holds (0, 1, 2, 3, $77 with either sprite size; 4, $81); ATRBAS / PATBAS, not the screen-table cells, give the places in every "
                "mode measured.", writes),
    Rule("R-CS-R1", S1, "VDP register R#1 := RG1SAV, as the VDP holds it (bit 2 reads 0: RG1SAV $A4; bits 7-5 as they are: "
         "$82, $A4, $88; bit 7 clear: $60); the other registers keep their "
         "values, and RG0SAV-RG7SAV, SCRMOD and FORCLR / BAKCLR / BDRCLR are not changed.", ALL,
         lambda c: (c.vdp == tuple((c.crg1 & 0xFB) if k == 1 else v for k, v in enumerate(X.VPRE))
                    and c.sav == (0xA5, c.crg1) + (0xA5,) * 6 and c.scrmod == c.cscr
                    and c.colours == (c.fo, c.ba, c.bd))),
    Rule("R-CS-REGS", S1, "On return A = FORCLR, E = FORCLR, D kept; BC = $0020 (8 x 8) or $0080 (16 x 16); HL = ATRBAS + "
         "$80, just past the table; F: for 16 x 16 sprites $95, one value; for 8 x 8 bits 5 and 3 are RG1SAV's bits 7 "
         "and 5 (as GSPSIZ leaves them: $E0 gives $28, $88 $20) and the rest clear -- whatever F was on entry. IX and "
         "IY are kept.", ALL,
         lambda c: (c.a == c.fo and c.de == (marker_d(c) | c.fo) and c.bc == (0x80 if BIG(c) else 0x20)
                    and c.hl == (c.catr + 0x80) & 0xFFFF and c.f == (0x95 if BIG(c) else (c.crg1 >> 2) & 0x28)
                    and (c.ix, c.iy) == (X.marker(c, 0x4321), X.marker(c, 0x8765)))),
    Rule("R-CS-EI", S1, "Interrupts are on after the call, whether they were on or off before it.", ALL,
         lambda c: c.iff == 1),
]


def marker_d(c):
    return X.marker(c, 0x9BDF) & 0xFF00
