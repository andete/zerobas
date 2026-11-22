#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/WRTVRM.md's EXECUTABLE RULES (docs/spec-method.md §3a): WRTVRM ($004D) -- the run the VRAM access calls share
(probes/bios/spec/xvram.asm, op 1; the loader and the model are xvram_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xvram_model as V  # noqa: E402

PAGE = "docs/bios/WRTVRM.md"
OUTPUTS = V.OUTPUTS


def cases():
    return V.load(1)


S1 = "1. WRTVRM ($004D): write a VRAM byte"
ALL = lambda c: True  # noqa: E731

RULES = [
    V.mem_rule("WV", S1, "The VRAM byte at HL AND $3FFF := A; its neighbours keep their bytes (HL $1234, $3FFF, $2034, $0812, and "
               "$4123 / $C125 / $FFFF, which write $0123 / $0125 / $3FFF; A $00, $FF, $5A, $A5, $3C, $C3)."),
    Rule("R-WV-KEEP", S1, "A, F, BC, DE, HL, IX and IY are kept (F $00, $FF, $A5 and $5A on entry).", ALL,
         lambda c: V.keep(c, ["a", "f", "bc", "de", "hl", "ix", "iy"])),
    V.land_rule("WV", S1, "The VDP is left writing at the next address: a byte the probe then writes to port $98 lands "
                "at (HL + 1) AND $3FFF."),
    V.ei_rule("WV", S1),
]

UNREAD = V.unread(1)
