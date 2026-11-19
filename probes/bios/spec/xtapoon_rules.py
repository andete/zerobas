#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/TAPOON.md's EXECUTABLE RULES (docs/spec-method.md §3a): TAPOON ($00EA) -- probes/bios/spec/xtap1.asm (the loader is
xtap1_model)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xtap1_model as G  # noqa: E402

PAGE = "docs/bios/TAPOON.md"
OUTPUTS = dict(G.OUTPUTS, XTW=["f", "de", "iff", "aa"])


def cases():
    return G.load("TAPOON", "XTW")


S1 = "1. TAPOON ($00EA): start writing the tape"
ALL = lambda c: True  # noqa: E731


RULES = [
    Rule("R-TN-OK", S1, "With a recorder ready, the carry is clear (no CTRL+STOP): the leader is written. (A, BC and HL "
         "are left holding working values: not compared, the group `XTW`.)", ALL, lambda c: c.f & 1 == 0),
    Rule("R-TN-MOTOR", S1, "The motor runs (port C bit 4 := 0); interrupts are off after the call.", ALL,
         lambda c: G.motor(c) == 0 and c.iff == 0),
    Rule("R-TN-DE", S1, "DE is kept ($1234 measured).", ALL, lambda c: c.de == c.cde),
]
