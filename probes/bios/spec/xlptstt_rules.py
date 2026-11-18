#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/LPTSTT.md's EXECUTABLE RULES (docs/spec-method.md §3a): LPTSTT ($00A8) with the printer logger plugged
-- the runs docs/bios/LPTOUT.md reads (probes/bios/spec/xlpt.asm; the loader is xlptout_rules.load); and with nothing
plugged in -- scratchpad/XLPT2_run1.out (row N), XLPT2_run1d.out (row D) (probes/bios/spec/xlpt2.asm)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xlptout_rules as R  # noqa: E402
import re  # noqa: E402
from types import SimpleNamespace as NS  # noqa: E402

PAGE = "docs/bios/LPTSTT.md"
OUTPUTS = dict(R.OUTPUTS, XN=["a", "f", "moved"])


def cases():
    out = R.load("S")
    for name, row in (("XLPT2_run1.out", "N"), ("XLPT2_run1d.out", "D")):
        t = open(os.path.join(ROOT, "scratchpad", name)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}[ \t]*:[ \t]*([0-9a-fA-F]+)", t).group(1))
            if b[0] != 0xA5 or b[7] != 0xC3:
                sys.exit(f"FAIL: the {name} block is not complete (no sentinel)")
            for k, (ea, ef) in enumerate(((0x5A, 0xFF), (0xA5, 0x00))):
                o = 1 + 3 * k
                out[who].append(NS(src="XN", id=f"XN {row}{k}", row=row, ea=ea, ef=ef, a=b[o], f=b[o + 1],
                                   moved=b[o + 2]))
    return out


S1 = "1. LPTSTT ($00A8): the printer's status"

RULES = [
    Rule("R-LS-READY", S1, "With a printer ready (the emulator's logger plugged), A is $FF and F $BB -- Z clear -- "
         "whatever A and F were on entry ($5A / $FF, $A5 / $00), before and after 256 bytes sent.",
         lambda c: c.src == "XS",
         lambda c: c.a == 0xFF and c.f == 0xBB),
    Rule("R-LS-NONE", S1, "With nothing plugged into the printer port, A is $00 and F $42 -- Z set -- whatever A and "
         "F were on entry ($5A / $FF, $A5 / $00).", lambda c: c.src == "XN",
         lambda c: c.a == 0x00 and c.f == 0x42),
    Rule("R-LS-KEEP", S1, "BC, DE, HL, IX and IY are kept, ready or not.", lambda c: True, lambda c: c.moved == 0),
]
