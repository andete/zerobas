#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/SETRD.md's EXECUTABLE RULES (docs/spec-method.md §3a): SETRD ($0050) -- the run the VRAM access calls share
(probes/bios/spec/xvram.asm, op 2; the loader and the model are xvram_rules)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xvram_rules as V  # noqa: E402

PAGE = "docs/bios/SETRD.md"
OUTPUTS = V.OUTPUTS


def cases():
    return V.load(2)


S1 = "1. SETRD ($0050): set the VDP address for reading"
ALL = lambda c: True  # noqa: E731

RULES = [
    Rule("R-SR-READ", S1, "The VDP is left reading from HL AND $3FFF: the next two reads of port $98 return the bytes at "
         "that address and the next one, wrapping from $3FFF to $0000.", ALL,
         lambda c: (c.p0, c.p1) == (V.model(c)[0][c.chl & 0x3FFF], V.model(c)[0][(c.chl + 1) & 0x3FFF])),
    Rule("R-SR-AF", S1, "A := H AND $3F, and F is its flags as an AND leaves them (H set, P/V the even parity, N and C "
         "clear) -- whatever A and F were on entry (A $A7, $00, $5A; F $00, $FF, $A5, $5A). H AND $3F = 0 "
         "(HL $0000, $C0AB) gives Z and P/V set ($54).", ALL,
         lambda c: c.a == (c.chl >> 8) & 0x3F and c.f == V.logical(c.a) | 0x10),
    Rule("R-SR-KEEP", S1, "BC, DE, HL, IX and IY are kept.", ALL, lambda c: V.keep(c, ["bc", "de", "hl", "ix", "iy"])),
    V.mem_rule("SR", S1, "VRAM is not changed: the probe's VRAM windows read back as it set them."),
    V.ei_rule("SR", S1),
]

UNREAD = V.unread(2)
