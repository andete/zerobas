#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/LDIRVM.md's EXECUTABLE RULES (docs/spec-method.md §3a): LDIRVM ($005C) -- the run the VRAM access calls share
(probes/bios/spec/xvram.asm, op 6; the loader and the model are xvram_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xvram_model as V  # noqa: E402

PAGE = "docs/bios/LDIRVM.md"
OUTPUTS = V.OUTPUTS


def cases():
    return V.load(6)


S1 = "1. LDIRVM ($005C): copy RAM to VRAM"
ALL = lambda c: True  # noqa: E731

RULES = [
    V.mem_rule("VM", S1, "BC bytes are copied from RAM at HL to VRAM at DE AND $3FFF (wrapping from $3FFF to $0000); "
               "the VRAM bytes around keep theirs. (HL $E9A0; DE $1234, $3FFC, $1200, and $5234 / $D234 / $9234, "
               "which write from $1234; BC 1, 4, 8, $100, $108.) The source RAM is not changed."),
    Rule("R-VM-REGS", S1, "On return A = 0, F = $44 (Z and P/V) and BC = 0; HL holds the entry DE and DE the entry HL + "
         "BC (the two exchanged); IX and IY are kept -- whatever A and F were on "
         "entry (A $A7, $5A, $00; F $00, $FF, $A5, $5A).", ALL,
         lambda c: ((c.a, c.f, c.bc, c.hl, c.de) == (0, 0x44, 0, c.cde, c.chl + c.cbc)
                    and V.keep(c, ["ix", "iy"]))),
    V.land_rule("VM", S1, "The VDP is left writing after the copied span: a byte the probe then writes to port $98 "
                "lands at (DE + BC) AND $3FFF."),
    V.ei_rule("VM", S1),
]

UNREAD = V.unread(6)
