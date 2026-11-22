#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/SCANR.md's EXECUTABLE RULES (docs/spec-method.md §3a): SCANR ($012C) -- probes/bios/spec/xgfx6.asm, op 1
(the loader and the pixel model are xgfx6_model), and probes/bios/spec/xscank.asm (scratchpad/XSCANK_run3.out, the
group XK: where SCREEN 2 keeps the run for SCANL)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx6_model as G  # noqa: E402

PAGE = "docs/bios/SCANR.md"
OUTPUTS = dict(G.OUTPUTS)
OUTPUTS["XK"] = ["hl", "k"]
XK_RUNS = (8, 2, 5)                     # the border pixel's X in xscank.asm's three cases
XK_REC = 3203


def cases():
    out = G.load(1)
    t = open(os.path.join(ROOT, "scratchpad", "XSCANK_run3.out")).read()
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        b += bytes(max(0, XK_REC * len(XK_RUNS) - len(b)))
        for i, x in enumerate(XK_RUNS):
            r = b[XK_REC * i: XK_REC * (i + 1)]
            if r[XK_REC - 1] != 0xC3:
                sys.exit("FAIL: an XSCANK record has no sentinel")
            k = 2 + 0xF867 - 0xF380
            out[who].append(NS(src="XK", id=f"XK {i + 1}", x=x, hl=r[0] | (r[1] << 8), k=r[k] | (r[k + 1] << 8)))
    return out


S1 = "1. SCANR ($012C): scan right for the PAINT border"
ALL = lambda c: True  # noqa: E731


def scan(c):
    """(VRAM writes, HL, DE, CLOC / CMASK, the run's start CLOC / CMASK)"""
    return G.scanr(c)


RULES = [
    Rule("R-SR-SCAN", S1, "From the pixel at CLOC / CMASK (SCREEN 3: the block), first a skip: while the pixel is "
         "BDRATR's colour, count DE down; when that makes it 0 the call ends there -- CLOC / CMASK on that pixel, HL 0, "
         "nothing painted or saved (DE 1 stops on the first border pixel, DE 2 on the second) -- otherwise step right "
         "(from DE 0 it goes on below 0: 4 border pixels give $FFFC). Then the run: count the pixels that are not BDRATR's, rightwards, to the first that is or to the row's last "
         "(X 255 / block 63). HL := that count; DE := the counted-down skip; CLOC / CMASK := the stopping pixel (the "
         "row's last if none stopped it).", ALL,
         lambda c: (c.hl, c.de, (c.cloc, c.cmask)) == scan(c)[1:4]),
    Rule("R-SR-PAINT", S1, "The run is painted in ATRBYT -- in SCREEN 2 when B is not 0, as NSETCX sets pixels (a whole "
         "byte to pattern $00, colour ATRBYT); in SCREEN 3 whatever B is. Nothing else in VRAM changes.", ALL,
         lambda c: G.vram_after(c, scan(c)[0]) == (c.sums, (c.w1, c.w2))),
    Rule("R-SR-SAVE", S1, "CSAVEA / CSAVEM ($F942 / $F944) := the run's first pixel (kept when the skip ended the "
         "call); the rest of the work area recorded "
         "($F92D-$F933, $F945-$F954), ATRBYT and BDRATR are kept.", ALL,
         lambda c: c.gwork == (G.gwork_kept() if scan(c)[4] is None else G.gwork_kept()[0:7] + (
             lambda p: (p[0] & 0xFF, p[0] >> 8, p[1]))(scan(c)[4]) + G.gwork_kept()[10:])
         and (c.atrbyt, c.bdratr) == (c.catr, c.cbdr)),
    Rule("R-SR-K", S1, "In SCREEN 2 it keeps the run's length -- HL, 16-bit -- at FILNAM+1 ($F867-$F868), the K that "
         "SCANL paints on top of its own count (docs/bios/SCANL.md); runs of 8, 2 and 5 pixels measured.",
         lambda c: c.src == "XK", lambda c: (c.hl, c.k) == (c.x, c.x)),
    Rule("R-SR-KEEP", S1, "IX and IY are kept; RG0SAV-RG7SAV, SCRMOD and the VDP registers are kept; interrupts are on "
         "after. (A, F and BC are left holding working values: not compared, the group `XR`.)", ALL,
         lambda c: (c.ix, c.iy, c.iff) == (G.marker(c, 0x4321), G.marker(c, 0x8765), 1)
         and c.regs == (0xA5,) * 8 + (c.cscr,) + G.VPRE),
]


for _r in RULES:
    if _r.id != "R-SR-K":
        _r.select = (lambda s: (lambda c: c.src != "XK" and s(c)))(_r.select)
