#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/WSLREG.md's EXECUTABLE RULES (docs/spec-method.md §3a): WSLREG ($013B) writing the primary slot register
-- the runs docs/bios/RSLREG.md reads (probes/bios/spec/xrslreg.asm; the loader is xrslreg_rules.load)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xrslreg_rules as R  # noqa: E402

PAGE = "docs/bios/WSLREG.md"
OUTPUTS = R.OUTPUTS


def cases():
    return R.load("W")


S1 = "1. WSLREG ($013B): write the primary slot register"

RULES = [
    Rule("R-WS-W", S1, "The primary slot register ($A8), read by hand after the call, is A: 16 values (pages 1 and 2 "
         "every slot, page 0 slot 0, page 3 slot 3).", lambda c: True, lambda c: c.a8 == c.v),
    Rule("R-WS-KEEP", S1, "A and F are kept ($00 and $FF on entry), and so are BC, DE, HL, IX and IY (two sets of "
         "values) and the interrupt state (off, or on).", lambda c: True,
         lambda c: c.a == c.v and c.f == c.ef and c.moved == 0 and c.iff == c.ei),
]
