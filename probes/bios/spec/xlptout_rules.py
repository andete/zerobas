#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/LPTOUT.md's EXECUTABLE RULES (docs/spec-method.md §3a): LPTOUT ($00A5) for every byte value, the printer
logger plugged -- scratchpad/XLPT_run2.out (row N) and XLPT_run2d.out (row D); probes/bios/spec/xlpt.asm documents
the order and the record. docs/bios/LPTSTT.md's rules (xlptstt_rules.py) read the same runs: `load()` serves both.
The abort: scratchpad/XLPT3_run1.out (row N), XLPT3_run1d.out (row D) (probes/bios/spec/xlpt3.asm: nothing plugged in,
CTRL + STOP held)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/LPTOUT.md"
RUNS = [("XLPT_run2.out", "N"), ("XLPT_run2d.out", "D")]
OUTPUTS = {"XL": ["a", "f", "moved"], "XP": ["prn"], "XS": ["a", "f", "moved"], "XA": ["a", "f", "moved"]}


def load(which):
    out = {"ref": [], "zb": []}
    for name, row in RUNS:
        t = open(os.path.join(ROOT, "scratchpad", name)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}[ \t]*:[ \t]*([0-9a-fA-F]+)", t).group(1))
            if b[0] != 0xA5 or len(b) < 776 or b[775] != 0xC3:
                sys.exit(f"FAIL: the {name} block is not complete (no sentinel)")
            if which == "S":
                for k, (off, ea, ef) in enumerate(((1, 0x5A, 0xFF), (772, 0xA5, 0x00))):
                    out[who].append(NS(src="XS", id=f"XS {row}{k}", row=row, ea=ea, ef=ef, a=b[off], f=b[off + 1],
                                       moved=b[off + 2]))
                continue
            prn = bytes.fromhex(re.search(rf"PRN {key}[ \t]*:[ \t]*([0-9a-fA-F]*)", t).group(1))
            for i in range(256):
                o = 4 + 3 * i
                out[who].append(NS(src="XL", id=f"XL {row}{i:02X}", row=row, c=i, ef=0xFF if i & 1 else 0,
                                   a=b[o], f=b[o + 1], moved=b[o + 2]))
            out[who].append(NS(src="XP", id=f"XP {row}", row=row, prn=prn))
    return out


def cases():
    out = load("O")
    for name, row in (("XLPT3_run1.out", "N"), ("XLPT3_run1d.out", "D")):
        t = open(os.path.join(ROOT, "scratchpad", name)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}[ \t]*:[ \t]*([0-9a-fA-F]+)", t).group(1))
            if b[0] != 0xA5 or b[4] != 0xC3:
                sys.exit(f"FAIL: the {name} block is not complete (LPTOUT never returned)")
            out[who].append(NS(src="XA", id=f"XA {row}", row=row, a=b[1], f=b[2], moved=b[3]))
    return out


def logical(a):
    return (a & 0x80) | (0x40 if a == 0 else 0) | (a & 0x28) | (0x04 if bin(a).count("1") % 2 == 0 else 0)


S1 = "1. LPTOUT ($00A5): send A to the printer"
XL = lambda c: c.src == "XL"  # noqa: E731

RULES = [
    Rule("R-LO-OUT", S1, "The printer receives every byte as sent, 0 to 255 in order, nothing added or converted.",
         lambda c: c.src == "XP", lambda c: c.prn == bytes(range(256))),
    Rule("R-LO-KEEP", S1, "A is kept, and so are BC, DE, HL, IX and IY.", XL,
         lambda c: c.a == c.c and c.moved == 0),
    Rule("R-LO-ABORT", S1, "With no printer ready, LPTOUT waits; CTRL + STOP held ends the wait: it returns with the "
         "carry set (aborted), A kept ($41) and BC, DE, HL, IX, IY kept.", lambda c: c.src == "XA",
         lambda c: (c.f & 1) == 1 and c.a == 0x41 and c.moved == 0),
    Rule("R-LO-ABORTF", S1, "The rest of F after the abort is clear: F is $01.", lambda c: c.src == "XA",
         lambda c: c.f == 0x01),
    Rule("R-LO-F", S1, "F is an AND's on A: S, Z, bits 5 / 3 from A, H set, P/V A's parity, N clear, and the carry "
         "clear (the byte went out, not aborted) -- whatever F was on entry ($00 / $FF).", XL,
         lambda c: c.f == logical(c.c) | 0x10),
]
