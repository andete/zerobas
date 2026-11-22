#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
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
         "VRAM. Other A go by A - 1 as a signed byte: negative (A = 0, and $81-$FF) as INITXT -- measured $81, $FE, "
         "$FF; A = 1 as INIT32, 2 as INIGRP, any other (A - 1 from 3 to $7F) as INIMLT -- measured 4, $7F, $80. Each case is compared with "
         "the same machine's direct call from the same set-up; IX and IY are left out of the comparison and checked "
         "kept on their own (cases 12, 31 and 40 have the other marker set from their partners).", lambda c: True, lambda c: same(c, c.who)),
    Rule("R-CM-TXTBAS", S1, "Where CHGMOD goes as INITXT (A = 0, $81, $FE, $FF) PATBAS and ATRBAS keep their values "
         "($2222 / $1111 in the probe) -- an absolute check, beside R-CM-MODE's comparison with the same machine. (A "
         "CHGMOD that does nothing for A above 3 also passes cases 17, 33, 34; case 14 is the one that tests INITXT.)",
         lambda c: c.ca == 0 or c.ca >= 0x81, lambda c: (c.patbas, c.atrbas) == (0x2222, 0x1111)),
]

