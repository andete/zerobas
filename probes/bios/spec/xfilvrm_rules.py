#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/FILVRM.md's EXECUTABLE RULES (docs/spec-method.md §3a): FILVRM ($0056) -- the run the VRAM access calls share
(probes/bios/spec/xvram.asm, op 4; the loader and the model are xvram_rules)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xvram_rules as V  # noqa: E402

PAGE = "docs/bios/FILVRM.md"
OUTPUTS = V.OUTPUTS


def cases():
    return V.load(4)


S1 = "1. FILVRM ($0056): fill VRAM with a byte"
ALL = lambda c: True  # noqa: E731

RULES = [
    V.mem_rule("FV", S1, "BC bytes of VRAM from HL AND $3FFF := A, the address wrapping from $3FFF to $0000; the bytes "
               "around keep theirs. BC = 0 fills 65536 bytes: all of VRAM. (HL $1234, $1200, $3FFC, $5234, $2000; BC 1, "
               "4, 8, $100, 0.)"),
    Rule("R-FV-BC", S1, "BC is 0 on return; A, DE, HL, IX and IY are kept.", ALL,
         lambda c: c.bc == 0 and V.keep(c, ["a", "de", "hl", "ix", "iy"])),
    Rule("R-FV-F", S1, "F is kept ($00 and $FF on entry).", ALL, lambda c: c.f == c.cf),
    V.ei_rule("FV", S1),
]
