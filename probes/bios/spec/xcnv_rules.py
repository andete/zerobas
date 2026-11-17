#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CNVCHR.md's EXECUTABLE RULES (docs/spec-method.md §3a): CNVCHR ($00AB), exhaustively -- every A x GRPHED
in {0, 1, $5A} x the entry flags {$00, $FF} -- from scratchpad/XCNV_run1.out (probes/bios/spec/xcnv.asm documents the
order and the 3-byte record)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/CNVCHR.md"
OUTPUTS = {"XV": ["a_out", "f", "grphed"]}
N = 1536


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XCNV_run1.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        if b[1] != 0xA5 or len(b) < 2 + 3 * N + 1 or b[2 + 3 * N] != 0xC3:
            sys.exit("FAIL: the XCNV block is not complete (no sentinel)")
        cs = []
        for i in range(N):
            r = b[2 + 3 * i: 5 + 3 * i]
            cs.append(NS(src="XV", id=f"XV {i:04}", ef=(0x00, 0xFF)[i // 768], g=(0, 1, 0x5A)[(i // 256) % 3],
                         a=i % 256, a_out=r[0], f=r[1], grphed=r[2]))
        out[who] = cs
    return out


C, Z = 0x01, 0x40


def head(c):
    return c.g == 0 and c.a == 1


def conv(c):
    return c.g != 0 and 0x40 <= c.a <= 0x5F


S1 = "1. CNVCHR ($00AB): the graphic-character header"

RULES = [
    Rule("R-V-HEAD", S1, "With GRPHED 0, A = $01 (the graphic header) sets GRPHED to 1 and returns A as it was with the "
         "carry CLEAR (and Z set).", head,
         lambda c: c.a_out == 1 and c.grphed == 1 and c.f & (C | Z) == Z),
    Rule("R-V-CONV", S1, "With GRPHED set -- 1 or any non-zero value ($5A) -- A from $40 to $5F becomes A − $40 (the "
         "graphic character) with the carry SET and Z CLEAR, and GRPHED becomes 0.", conv,
         lambda c: c.a_out == c.a - 0x40 and c.grphed == 0 and c.f & (C | Z) == C),
    Rule("R-V-PASS", S1, "Every other A comes back unchanged with the carry SET and Z SET, and GRPHED becomes 0: the "
         "rest of the 256 values after the header, a second $01 after the header included, and every value but $01 "
         "with GRPHED 0.", lambda c: not head(c) and not conv(c),
         lambda c: c.a_out == c.a and c.grphed == 0 and c.f & (C | Z) == C | Z),
    Rule("R-V-F", S1, "The whole F on return (only C and Z published): 42 after the header, A3 after a conversion, "
         "41 OR (A AND $28) -- A's bits 5 and 3 copied -- otherwise; the flags on entry ($00 / $FF) never matter.",
         lambda c: True,
         lambda c: c.f == (0x42 if head(c) else 0xA3 if conv(c) else 0x41 | (c.a & 0x28))),
]
