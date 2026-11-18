#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/DCOMPR.md's EXECUTABLE RULES (docs/spec-method.md §3a): DCOMPR ($0020) over every combination of H, D, L,
E in {00, 01, 5A, 7F, 80, FE, FF} -- scratchpad/XDCOMPR_run1.out (probes/bios/spec/xdcompr.asm documents the order and
the 3-byte record)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/DCOMPR.md"
OUTPUTS = {"XD": ["a", "f", "kept"]}
V = [0x00, 0x01, 0x5A, 0x7F, 0x80, 0xFE, 0xFF]
EXTRA = [(0x12, 0x12, 0x34, 0x34), (0x12, 0x12, 0x34, 0x35), (0x12, 0x12, 0x35, 0x34), (0x00, 0xFF, 0x00, 0xFF)]


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XDCOMPR_run1.out")).read()
    order = [(h, d, l, e, 0x00) for h in V for d in V for l in V for e in V] + [x + (0xFF,) for x in EXTRA]
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        if b[0] != 0xA5 or len(b) < 2 + 3 * len(order) or b[1 + 3 * len(order)] != 0xC3:
            sys.exit("FAIL: the XDCOMPR block is not complete (no sentinel)")
        out[who] = [NS(src="XD", id=f"XD {i:04}", h=h, d=d, l=l, e=e, ef=ef, a=b[1 + 3 * i], f=b[2 + 3 * i],
                       kept=b[3 + 3 * i]) for i, (h, d, l, e, ef) in enumerate(order)]
    return out


def sub(a, b):
    """A and F after the Z80's SUB b with A = a"""
    r = (a - b) & 0xFF
    f = ((r & 0x80) | (0x40 if r == 0 else 0) | (r & 0x28) | (0x10 if (a & 0x0F) < (b & 0x0F) else 0)
         | (0x04 if (a ^ b) & (a ^ r) & 0x80 else 0) | 0x02 | (0x01 if a < b else 0))
    return r, f


def model(c):
    return sub(c.h, c.d) if c.h != c.d else sub(c.l, c.e)


S1 = "1. DCOMPR ($0020, RST 20h): compare HL with DE"

RULES = [
    Rule("R-D-ZC", S1, "Z is set exactly when HL = DE, and the carry exactly when HL < DE, unsigned.", lambda c: True,
         lambda c: bool(c.f & 0x40) == ((c.h << 8 | c.l) == (c.d << 8 | c.e))
         and bool(c.f & 0x01) == ((c.h << 8 | c.l) < (c.d << 8 | c.e))),
    Rule("R-D-A", S1, "A (not published) is H − D when the high bytes differ, and L − E when they are equal.",
         lambda c: True, lambda c: c.a == model(c)[0]),
    Rule("R-D-F", S1, "The whole F (only Z and C published) is that subtraction's: S and bits 5 / 3 from the result, H "
         "from the low nibbles' borrow, P/V the signed overflow, N set -- whatever F was on entry ($00, and $FF in "
         "the last four cases).", lambda c: True, lambda c: c.f == model(c)[1]),
    Rule("R-D-KEPT", S1, "BC, DE, HL, IX and IY are kept.", lambda c: True, lambda c: c.kept == 0),
]
