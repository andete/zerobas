#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CHGMOD.md's EXECUTABLE RULES (docs/spec-method.md §3a): CHGMOD ($005F) -- probes/bios/spec/xinig.asm, op 2,
each case compared with the same set-up's direct INITXT / INIT32 / INIGRP / INIMLT case (xinig_model.PAIRS)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xinig_model as X  # noqa: E402

PAGE = "docs/bios/CHGMOD.md"
OUTPUTS = X.OUTPUTS


def cases():
    return X.load(2)


S1 = "1. CHGMOD ($005F): change the screen mode"
SAME = [f for f in X.FIELDS if f not in ("ix", "iy")]
NAMES = {12: "INIGRP", 13: "INIMLT", 14: "INITXT", 15: "INIT32", 16: "INIMLT", 17: "INITXT"}


def same(c, who):
    p = X.partner(c, who)
    return all(getattr(c, f) == getattr(p, f) for f in SAME) and X.kept_ixiy(c)


RULES = [
    Rule("R-CM-MODE", S1, "CHGMOD with A = 0 does what INITXT does, 1 what INIT32 does, 2 what INIGRP does, 3 what "
         "INIMLT does: from the same set-up it leaves every recorded output as the direct call does -- the registers "
         "(IX and IY kept), the interrupt state, RG0SAV-RG7SAV, SCRMOD, OLDSCR, PATBAS / ATRBAS, the VDP registers and "
         "VRAM. A = 4 goes as 3 (INIMLT) and A = $FF as 0 (INITXT).", lambda c: True, lambda c: same(c, c.who)),
    Rule("R-CM-TXTBAS", S1, "With A = 0 (INITXT) PATBAS and ATRBAS keep their values ($2222 / $1111 in the probe), as "
         "INITXT leaves them.", lambda c: c.ca == 0, lambda c: (c.patbas, c.atrbas) == (0x2222, 0x1111)),
]

