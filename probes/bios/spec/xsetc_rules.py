#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/SETC.md's EXECUTABLE RULES (docs/spec-method.md §3a): SETC ($0120) -- probes/bios/spec/xgfx3.asm, op 1
(the loader and the VRAM model are xgfx3_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx3_model as G  # noqa: E402

PAGE = "docs/bios/SETC.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load(1)


S1 = "1. SETC ($0120): set the current pixel"
ALL = lambda c: True  # noqa: E731


def writes(c):
    """VRAM, SCREEN 2: the pattern byte at CLOC and its colour byte at CLOC XOR $2000 (GRPCOL and GRPCGP are not
    used), by the first that applies -- ATRBYT equal to the colour byte's background nibble: CMASK's bit cleared;
    ATRBYT's low nibble equal to the foreground nibble: the bit set; the pattern byte OR CMASK = $FF (no other bit
    of the byte clear): the bit cleared and colour byte := (colour AND $F0) OR ATRBYT -- ATRBYT ORed in whole, so
    $1A over $E_ gives $FA; otherwise the bit set
    and (ATRBYT x 16) AND $F0 into the foreground nibble ($1A gives $A0). The background test takes the whole
    ATRBYT ($1A is not $A), the foreground test its low nibble ($1A is $A).
    SCREEN 3: CMASK $0F -- byte := (byte AND $F0) OR ATRBYT (whole: $1A over $A4 gives $BA); CMASK $F0 -- byte :=
    (byte AND $0F) OR ((ATRBYT x 16) AND $F0). Nothing
    else changes."""
    a = c.cclo & 0x3FFF
    if c.cscr == 2:
        return G.pixel_byte(c, a, c.ccm)[0]
    old = G.fill(a)
    new = (old & 0xF0) | c.catr if c.ccm == 0x0F else (old & 0x0F) | ((c.catr << 4) & 0xF0)
    return {a: new}


def af(c):
    """A and F after: the colour byte and its OR flags when the colour byte is written, the pattern byte and its S /
    Z / P flags (bits 3, 5 clear) when only the pattern byte is; in SCREEN 3 the pixel byte and its OR flags"""
    if c.cscr == 2:
        w, v = G.pixel_byte(c, c.cclo & 0x3FFF, c.ccm)
        return v, (G.logical(v) if len(w) == 2 else G.pattern_flags(v))
    v = writes(c)[c.cclo & 0x3FFF]
    return v, G.logical(v)


RULES = [
    G.vram_rule("SC", S1, " ".join(writes.__doc__.split()), writes),
    Rule("R-SC-AF", S1, "A := the byte written last, whatever A and F were on entry: in SCREEN 2 the colour byte when "
         "it is written, F its flags as an OR leaves them; when only the pattern byte is written, the pattern byte, F "
         "its S, Z and P/V flags with H, N, C and bits 3 / 5 clear ($FF gives $84, $00 $44). In SCREEN 3 the pixel "
         "byte, F its OR flags.", ALL, lambda c: (c.a, c.f) == af(c)),
    Rule("R-SC-KEEP", S1, "BC, DE, HL, IX and IY are kept; CLOC, CMASK and ATRBYT are kept.", ALL,
         lambda c: ((c.bc, c.de, c.hl, c.ix, c.iy) == tuple(G.marker(c, v) for v in (0x1357, 0x9BDF))
                    + (c.chl, G.marker(c, 0x4321), G.marker(c, 0x8765))
                    and (c.cloc, c.cmask, c.atrbyt) == (c.cclo, c.ccm, c.catr))),
    G.regs_rule("SC", S1),
    G.ei_rule("SC", S1),
]
