#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/LDIRMV.md's EXECUTABLE RULES (docs/spec-method.md §3a): LDIRMV ($0059) -- the run the VRAM access calls share
(probes/bios/spec/xvram.asm, op 5; the loader and the model are xvram_rules)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xvram_rules as V  # noqa: E402

PAGE = "docs/bios/LDIRMV.md"
OUTPUTS = V.OUTPUTS


def cases():
    return V.load(5)


S1 = "1. LDIRMV ($0059): copy VRAM to RAM"
ALL = lambda c: True  # noqa: E731

RULES = [
    V.mem_rule("MV", S1, "BC bytes are copied from VRAM at HL AND $3FFF (wrapping from $3FFF to $0000) to RAM at DE; "
               "the RAM bytes around keep theirs. (HL $1234, $3FFC, $1200, and $5234 / $D234 / $9234, which "
               "read from $1234; DE $E980; BC 1, 4, 8, $100, $108.) The source VRAM is not changed."),
    Rule("R-MV-REGS", S1, "On return A = 0, F = $44 (Z and P/V), BC = 0 and DE = DE + BC; HL, IX and IY are kept -- "
         "whatever A and F were on entry (A $A7, $00, $5A; F $00, $FF, $A5, $5A).", ALL,
         lambda c: (c.a, c.f, c.bc, c.de) == (0, 0x44, 0, c.cde + c.cbc) and V.keep(c, ["hl", "ix", "iy"])),
    V.port_rule("MV", S1, "The VDP is left reading the byte after the last one copied: the next read of port $98 "
                "returns the VRAM byte at (HL + BC) AND $3FFF."),
    V.ei_rule("MV", S1),
]

UNREAD = V.unread(5)
