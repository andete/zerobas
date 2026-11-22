#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/CALBAS.md's EXECUTABLE RULES (docs/spec-method.md §3a): CALBAS ($0159) calling the published RSLREG
($0138) in the main ROM -- the runs docs/bios/CALSLT.md reads (probes/bios/spec/xcalslt.asm; the loader is
xcalslt_rules.load)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xcalslt_rules as R  # noqa: E402

PAGE = "docs/bios/CALBAS.md"
OUTPUTS = R.OUTPUTS


def cases():
    return R.load(2)


S1 = "1. CALBAS ($0159): call the address in IX in the main ROM"

RULES = [
    Rule("R-CB-CALL", S1, "The routine at IX runs and its results come back -- measured with RSLREG, in page 0, which "
         "is the main ROM before the call (nothing to switch): its A is the slot register during the call, as set "
         "before it (page 1 set to RAM by hand: $FC); F, BC, DE and HL come back as the caller set them (RSLREG "
         "keeps them).", lambda c: True,
         lambda c: c.af == (c.a8pre << 8 | c.ef) and (c.bc, c.de, c.hl) == (R.IN["bc"], R.IN["de"], R.IN["hl"])),
    Rule("R-CB-REGS", S1, "IX is $0138 after the call (RSLREG does not change it: whether the call restores it is "
         "open); IY comes back $0000 (it was $8765; the main ROM is slot 0 on every machine here).", lambda c: True, lambda c: c.ix == 0x0138 and c.iy == 0x0000),
    Rule("R-CB-SLOT", S1, "The slot register after the call is as before it, and interrupts are off, whether they "
         "were on or off on entry.", lambda c: True, lambda c: c.a8 == c.a8pre and c.iff == 0),
]

INTARGET = ["a8in", "iffin", "secin", "sp", "afin", "bcin", "dein", "hlin", "ixin", "iyin", "ran", "sec"]
# the target is RSLREG: the probe's own in-target record stays as the probe cleared it; and slot 3's secondary
# selection after is 3-0 (0) around a call that switches nothing
UNREAD = {f"XC {row}{i:02}": (INTARGET, "the in-target fields, which only the probe's own target writes (0 here); "
                              "and slot 3's secondary selection after, "
                              + ("recorded as 0 by the probe where slot 3 is not expanded" if row in "ND" else
                                 "3-0 before and after a call that switches nothing, so it separates nothing"))
          for row in "NDC" for i, cs in enumerate(R.CASES) if cs[0] == 2}
