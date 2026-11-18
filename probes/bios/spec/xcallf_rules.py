#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CALLF.md's EXECUTABLE RULES (docs/spec-method.md §3a): CALLF ($0030, RST 30h + the slot ID + the address)
-- the runs docs/bios/CALSLT.md reads (probes/bios/spec/xcalslt.asm; the loader is xcalslt_rules.load)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xcalslt_rules as R  # noqa: E402

PAGE = "docs/bios/CALLF.md"
OUTPUTS = R.OUTPUTS


def cases():
    return R.load(1)


S1 = "1. CALLF ($0030, RST 30h): call the address and slot that follow the RST"
CF = lambda c: c.op == 1  # noqa: E731

RULES = R.core("CF", S1, CF) + [
    Rule("R-CF-IY", S1, "In the target IY holds the slot ID in its high byte and the entry F in its low byte ($00, "
         "$5A, $FF; IY was $8765), for a slot that is not expanded; for the expanded RAM slot 3-0 (the cf3300 row) "
         "$0314.", lambda c: CF(c) and c.src in ("XC", "XCP"),
         lambda c: c.iyin == ((0x0314) if c.exp else (c.sid << 8 | c.ef))),
    Rule("R-CF-SP", S1, "The target runs 6 bytes below the caller's SP (its RST frame included) for a slot that is not "
         "expanded, 14 for the expanded RAM slot 3-0 (the cf3300 row).", lambda c: CF(c) and c.src in ("XC", "XCP"),
         lambda c: c.sp == (14 if c.exp else 6)),
]

UNREAD = R.unread(1)
