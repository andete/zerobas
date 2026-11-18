#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/RSLREG.md's EXECUTABLE RULES (docs/spec-method.md §3a): RSLREG ($0138) right after WSLREG ($013B) wrote
the primary slot register -- scratchpad/XRSLREG_run2.out (row N), XRSLREG_run2d.out (row D), XRSLREG_run2c.out (row
C); probes/bios/spec/xrslreg.asm documents the passes and the 10-byte record. docs/bios/WSLREG.md's rules
(xwslreg_rules.py) read the same runs: `load()` serves both."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/RSLREG.md"
RUNS = [("XRSLREG_run2.out", "N"), ("XRSLREG_run2d.out", "D"), ("XRSLREG_run2c.out", "C")]
PASSES = [dict(ef=0x00, ei=0, ra=0xA5), dict(ef=0xFF, ei=1, ra=0x5A)]   # entry F, interrupts, RSLREG's entry A
OUTPUTS = {"XS": ["a", "f", "moved", "iff"], "XW": ["a", "f", "moved", "iff", "a8"]}


def load(which):
    out = {"ref": [], "zb": []}
    for name, row in RUNS:
        t = open(os.path.join(ROOT, "scratchpad", name)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            if b[0] != 0xA5 or len(b) < 3 + 10 * 32 or b[2 + 10 * 32] != 0xC3:
                sys.exit(f"FAIL: the {name} block is not complete (no sentinel)")
            a8b = b[1]
            for i in range(32):
                r = b[2 + 10 * i:12 + 10 * i]
                p = PASSES[i >> 4]
                # page 3's field is the boot one: slot 3 ($C0) on every row, reference and zerobas alike
                v = (a8b & 0xC0) | ((i & 15) << 2)
                base = dict(id=f"XS {row}{i:02}", row=row, v=v, u=v ^ 0x3C, a8b=a8b, **p)
                if which == "W":
                    out[who].append(NS(src="XW", a=r[0], f=r[1], moved=r[2], iff=r[3], a8=r[4], **base))
                else:
                    out[who].append(NS(src="XS", a=r[5], f=r[6], moved=r[7], iff=r[8], **base))
    return out


def cases():
    return load("R")


S1 = "1. RSLREG ($0138): read the primary slot register"

RULES = [
    Rule("R-RS-A", S1, "A is the primary slot register ($A8) as the port holds it: the probe writes it by hand just "
         "before the call, with pages 1 and 2 set otherwise than WSLREG just set them -- 16 values (pages 1 and 2 "
         "every slot, page 0 slot 0, page 3 slot 3), whatever A was on entry ($A5 / $5A).",
         lambda c: True, lambda c: c.a == c.u),
    Rule("R-RS-KEEP", S1, "F is kept ($00 and $FF on entry), and so are BC, DE, HL, IX and IY (two sets of values) and "
         "the interrupt state (off, or on).", lambda c: True,
         lambda c: c.f == c.ef and c.moved == 0 and c.iff == c.ei),
]
