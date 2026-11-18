#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/SETWRT.md's EXECUTABLE RULES (docs/spec-method.md §3a): SETWRT ($0053) -- the run the VRAM access calls share
(probes/bios/spec/xvram.asm, op 3; the loader and the model are xvram_rules)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xvram_rules as V  # noqa: E402

PAGE = "docs/bios/SETWRT.md"
OUTPUTS = V.OUTPUTS


def cases():
    return V.load(3)


S1 = "1. SETWRT ($0053): set the VDP address for writing"
ALL = lambda c: True  # noqa: E731

RULES = [
    V.mem_rule("SW", S1, "The VDP is left writing to HL AND $3FFF: two bytes the probe then writes to port $98 ($C7, "
               "$C8) land at that address and the next one, wrapping from $3FFF to $0000; the other bytes keep theirs."),
    Rule("R-SW-AF", S1, "A := (H AND $3F) OR $40, and F is its flags as an OR leaves them (S, Z, bits 5 / 3, P/V the even "
         "parity; H, N and C clear) -- whatever A and F were on entry (A $A7, $00, $5A; F $00, $FF, $A5, $5A); HL $1234, $3FFF, $4123, "
         "$FFFF, $0812, $2034, $0000.", ALL,
         lambda c: c.a == ((c.chl >> 8) & 0x3F) | 0x40 and c.f == V.logical(c.a)),
    Rule("R-SW-KEEP", S1, "BC, DE, HL, IX and IY are kept.", ALL, lambda c: V.keep(c, ["bc", "de", "hl", "ix", "iy"])),
    V.ei_rule("SW", S1),
]

UNREAD = V.unread(3)
