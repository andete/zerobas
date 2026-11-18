#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/GRPPRT.md's EXECUTABLE RULES (docs/spec-method.md §3a): GRPPRT ($008D) -- probes/bios/spec/xgfx5.asm
(the loader and the drawing model are xgfx5_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xgfx5_model as G  # noqa: E402

PAGE = "docs/bios/GRPPRT.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load()


S1 = "1. GRPPRT ($008D): draw a character at the graphics accumulator"
ALL = lambda c: True  # noqa: E731
STEP = {2: 8, 3: 32}


def acc(c):
    """GRPACX / GRPACY after"""
    st = STEP[c.cscr]
    if c.ch < 0x20:
        if c.ch != 0x0D:
            return c.cx, c.cy
        return 0, (c.cy + st if c.cy + st <= 191 else 0)
    if not G.drawn(c):
        return c.cx, c.cy
    if c.cx + st > 255:
        return 0, (c.cy + st if c.cy + st <= 191 else 0)
    return c.cx + st, c.cy


def vram(c):
    return G.draw(c)[0] if G.drawn(c) else {}


def pos(c):
    return G.draw(c)[1:] if G.drawn(c) else (0x5A5A, 0xA5)


RULES = [
    Rule("R-GP-VRAM", S1, "A character code $20-$FF at GRPACX / GRPACY ($FCB7 / $FCB9) within the screen (X 0-255, Y 0-191; "
         "outside, nothing is drawn) is drawn from the font at CGPNT ($F91F slot, $F920 address -- the probe's own RAM "
         "font): its 8 lines, each 8 pixels from bit 7, in FORCLR ($F3E9). SCREEN 2: from the position MAPXYC gives "
         "(GRPCGP-based), each line's bits shifted right by X AND 7 into the pattern byte and the rest into the next "
         "cell's (none past X 255: no wrap); each pattern byte with bits m, colour byte at its address XOR $2000: m = 0 "
         "-- nothing written; FORCLR (whole) = the background nibble -- the bits cleared; FORCLR's low nibble = the "
         "foreground nibble -- the bits set; otherwise the bits set and (FORCLR x 16) AND $F0 into the foreground "
         "nibble (no whole-byte or last-clear-bit step: a line $FF sets pattern $FF). SCREEN 3: each glyph pixel is "
         "one block (X / 4, Y / 4 the first), its nibble := FORCLR's as SETC writes it, none past block column 63. "
         "After each line the position moves down as TDOWNC does, and drawing stops where TDOWNC stops (in SCREEN 2 "
         "at the bottom; in SCREEN 3 at a block row's line 7 with CLOC's high byte 5 or more). LOGOPR is not used. "
         "Control codes $00-$1F draw nothing.", ALL, lambda c: G.vram_after(c, vram(c)) == (c.sums, (c.w1, c.w2, c.w3))),
    Rule("R-GP-POS", S1, "CLOC / CMASK ($F92A / $F92C): for a drawn character, the first column's pixel on the line "
         "after the last drawn (where TDOWNC left it); otherwise kept.", ALL, lambda c: (c.cloc, c.cmask) == pos(c)),
    Rule("R-GP-ACC", S1, "GRPACX / GRPACY: a drawn character adds 8 to GRPACX in SCREEN 2, 32 in SCREEN 3; past 255 "
         "GRPACX := 0 and GRPACY goes on by the same step, to 0 past 191. CR ($0D) does that line feed whatever X is "
         "(GRPACX := 0). Other control codes and positions outside the screen keep both.", ALL,
         lambda c: c.grpac == acc(c)),
    Rule("R-GP-ATR", S1, "ATRBYT := FORCLR, except for a control code (kept: $77 preset). FORCLR and LOGOPR are kept.",
         ALL, lambda c: c.atrbyt == (c.catr if c.ch < 0x20 else c.cfor) and (c.forclr, c.logopr) == (c.cfor, c.clog)),
    Rule("R-GP-KEEP", S1, "A, F, BC, DE, HL, IX and IY are kept; RG0SAV-RG7SAV, SCRMOD and the VDP registers are "
         "kept.", ALL,
         lambda c: ((c.a, c.f, c.bc, c.de, c.hl, c.ix, c.iy) == (c.ch, c.cf) + tuple(
             G.marker(c, v) for v in (0x1357, 0x9BDF)) + (0x2468, G.marker(c, 0x4321), G.marker(c, 0x8765))
             and c.regs == (0xA5,) * 8 + (c.cscr,) + G.VPRE)),
    Rule("R-GP-EI", S1, "Interrupts are on after a printable code (drawn or outside the screen); after a control code "
         "they are as they were.", ALL, lambda c: c.iff == (c.ei if c.ch < 0x20 else 1)),
]
