#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/ISFLIO.md's EXECUTABLE RULES (docs/spec-method.md §3a): ISFLIO ($014A) for five PTRFIL values -- the
runs docs/bios/OUTDO.md reads (probes/bios/spec/xoutdo.asm section A; the loader is xoutdo_rules.load)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xoutdo_rules as R  # noqa: E402
import xoutdlp_rules as D  # noqa: E402

PAGE = "docs/bios/ISFLIO.md"
OUTPUTS = R.OUTPUTS


def cases():
    return R.load("I")


S1 = "1. ISFLIO ($014A): is the output going to a file?"

RULES = [
    Rule("R-IF-A", S1, "A is PTRFIL ($F864)'s two bytes ORed: non-zero exactly when PTRFIL is (PTRFIL $0000, $0001, "
         "$0100, $8000, $FFFF give $00, $01, $01, $80, $FF), whatever F was on entry ($00 / $FF).", lambda c: True,
         lambda c: c.a == (c.ptr & 0xFF) | (c.ptr >> 8)),
    Rule("R-IF-F", S1, "F is that OR's: Z set exactly when PTRFIL is 0, S, bits 5 / 3 from A, P/V its parity, H, N "
         "and the carry clear.", lambda c: True, lambda c: c.f == D.logical((c.ptr & 0xFF) | (c.ptr >> 8))),
    Rule("R-IF-KEEP", S1, "BC, DE, HL, IX and IY are kept.", lambda c: True, lambda c: c.moved == 0),
]
