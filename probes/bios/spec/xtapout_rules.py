#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/TAPOUT.md's EXECUTABLE RULES (docs/spec-method.md §3a): TAPOUT ($00ED) -- probes/bios/spec/xtap1.asm (the loader is
xtap1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xtap1_model as G  # noqa: E402

PAGE = "docs/bios/TAPOUT.md"
OUTPUTS = G.OUTPUTS


def cases():
    return G.load("TAPOUT", "XTO")


S1 = "1. TAPOUT ($00ED): write a byte to the tape"
ALL = lambda c: True  # noqa: E731


RULES = [
    Rule("R-TU-OK", S1, "The carry is clear (no CTRL+STOP) after each byte, set on entry or not. (A is left holding a working value: what "
         "the byte became is TAPIN's to show; the group `XTO`.)", ALL, lambda c: c.f & 1 == 0),
]
