#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/NSETCX.md's EXECUTABLE RULES (docs/spec-method.md §3a): NSETCX ($0123) -- probes/bios/spec/xgfx3.asm, op 2
(the loader and the VRAM model are xgfx3_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx3_model as G  # noqa: E402

PAGE = "docs/bios/NSETCX.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(2)


S1 = "1. NSETCX ($0123): set pixels to the right"
ALL = lambda c: True  # noqa: E731


def pixels(c):
    """the pixels set, as (address, mask) runs, and CLOC / CMASK after (SCREEN 3)"""
    n = c.chl or 1
    cl, cm, out = c.cclo, c.ccm, []
    for _ in range(n):
        out.append((cl & 0x3FFF, cm))
        if c.cscr == 2:
            cl, cm = (cl + 8, 0x80) if cm == 0x01 else (cl, cm >> 1)
        else:
            cl, cm = (cl + 8, 0xF0) if cm == 0x0F else (cl, 0x0F)
    return out, cl & 0xFFFF, cm


def writes(c):
    """VRAM: HL pixels from the current position rightwards, from cell to cell (into the next row's cells past the
    right edge). SCREEN 2: a pattern byte with some of its 8 pixels set gets those bits set and its colour byte (GRPCOL
    + address - GRPCGP) ATRBYT in the foreground nibble, the background kept; a pattern byte with all 8 pixels set
    becomes $00 and its colour byte ATRBYT -- the same pixels, drawn in the background colour. SCREEN 3: each pixel's
    nibble becomes ATRBYT's. HL = 0 sets one pixel (measured once). Nothing else changes."""
    w = {}
    px, _, _ = pixels(c)
    if c.cscr == 2:
        byaddr = {}
        for a, m in px:
            byaddr[a] = byaddr.get(a, 0) | m
        for a, bits in byaddr.items():
            ca = G.colour_addr(c, a)
            if bits == 0xFF:
                w[a], w[ca] = 0x00, c.catr
            else:
                w[a] = G.fill(a) | bits
                w[ca] = ((c.catr << 4) & 0xF0) | (G.fill(ca) & 0x0F)
        return w
    for a, m in px:
        old = w.get(a, G.fill(a))
        w[a] = (old & 0xF0) | (c.catr & 0x0F) if m == 0x0F else (old & 0x0F) | ((c.catr << 4) & 0xF0)
    return w


RULES = [
    G.vram_rule("NX", S1, " ".join(writes.__doc__.split()), writes),
    Rule("R-NX-POS", S1, "CLOC and CMASK: kept in SCREEN 2; in SCREEN 3 moved to the pixel after the last one set. "
         "ATRBYT is kept.", ALL,
         lambda c: (c.cloc, c.cmask) == ((c.cclo, c.ccm) if c.cscr == 2 else pixels(c)[1:]) and c.atrbyt == c.catr),
    Rule("R-NX-KEEP", S1, "IX and IY are kept. (A, F, BC, DE and HL are left holding working values: not compared, the "
         "group `XN`.)", ALL, lambda c: (c.ix, c.iy) == (G.marker(c, 0x4321), G.marker(c, 0x8765))),
    G.ei_rule("NX", S1),
]
