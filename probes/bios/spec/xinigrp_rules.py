#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/INIGRP.md's EXECUTABLE RULES (docs/spec-method.md §3a): INIGRP ($0072) -- probes/bios/spec/xinig.asm, op 0
(the loader and the model are xinig_rules)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xinig_rules as X  # noqa: E402

PAGE = "docs/bios/INIGRP.md"
OUTPUTS = X.OUTPUTS


def cases():
    return X.load(0)


def writes(c):
    """VRAM: the name table, 768 bytes from GRPNAM ($F3C7), := 0, 1, ... 255 three times; the pattern table, 6144 bytes
    from GRPCGP, := 0; the colour table, 6144 bytes from GRPCOL, := BAKCLR as it is (a byte over 15 too: $25); the 32
    sprite attribute entries from GRPATR get Y $D1, the pattern number (times 4 when RG1SAV's bit 1 is set) and FORCLR,
    X not written -- the sprite patterns are not cleared. Nothing else in VRAM changes."""
    nam, col, cgp, atr, _ = c.cells[10:15]
    w = {}
    for k in range(768):
        w[(nam + k) & 0x3FFF] = k & 0xFF
    for k in range(6144):
        w[(cgp + k) & 0x3FFF] = 0
    for k in range(6144):
        w[(col + k) & 0x3FFF] = c.ba
    X.sprite_writes(c, w, atr)
    return w


def shadows(cells):
    nam, col, cgp, atr, pat = cells
    return ((nam >> 10) & 0xFF, ((col >> 6) | 0x7F) & 0xFF, ((cgp >> 11) | 0x03) & 0xFF, (atr >> 7) & 0xFF,
            (pat >> 11) & 0xFF)


S1 = "1. INIGRP ($0072): set up the high-resolution graphics screen"
RULES = X.screen_rules("IG", S1, 2, writes, lambda v: v | 0x02, lambda v: v & 0xE7, shadows,
                       "On return A = the new RG1SAV, F = $A4, BC = $0001, DE = $7F03, HL = $F3D1; IX and IY are kept -- "
                       "whatever A and F were on entry.", 0x7F03, 0xF3D1, 2)
