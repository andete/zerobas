#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/INIMLT.md's EXECUTABLE RULES (docs/spec-method.md §3a): INIMLT ($0075) -- probes/bios/spec/xinig.asm, op 1
(the loader and the model are xinig_rules)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xinig_rules as X  # noqa: E402

PAGE = "docs/bios/INIMLT.md"
OUTPUTS = X.OUTPUTS


def cases():
    return X.load(1)


def writes(c):
    """VRAM: the name table, 768 bytes from MLTNAM ($F3D1), := for row r and column c (32 a row) (r / 4) x 32 + c -- each
    group of four rows the same 32 numbers; the pattern table, 1536 bytes from MLTCGP, := BAKCLR x 16 OR BAKCLR as a byte
    (BAKCLR $25 gives $75); the 32 sprite attribute entries from MLTATR get Y $D1, the pattern number (times 4 when
    RG1SAV's bit 1 is set) and FORCLR, X not written -- the sprite patterns are not cleared. Nothing else in VRAM
    changes."""
    nam, _, cgp, atr, _ = c.cells[15:20]
    w = {}
    for k in range(768):
        w[(nam + k) & 0x3FFF] = (k // 128) * 32 + k % 32
    for k in range(1536):
        w[(cgp + k) & 0x3FFF] = ((c.ba << 4) | c.ba) & 0xFF
    X.sprite_writes(c, w, atr)
    return w


def shadows(cells):
    nam, col, cgp, atr, pat = cells
    return ((nam >> 10) & 0xFF, (col >> 6) & 0xFF, (cgp >> 11) & 0xFF, (atr >> 7) & 0xFF, (pat >> 11) & 0xFF)


S1 = "1. INIMLT ($0075): set up the multicolour screen"
RULES = X.screen_rules("IM", S1, 3, writes, lambda v: v & 0x01, lambda v: (v & 0xE7) | 0x08, shadows,
                       "On return A = the new RG1SAV, F = $A4, BC = $0001, DE = $0000, HL = $F3DB; IX and IY are kept -- "
                       "whatever A and F were on entry.", 0x0000, 0xF3DB, 3)
