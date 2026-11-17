#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/TOTEXT.md's EXECUTABLE RULES (docs/spec-method.md §3a): TOTEXT ($00D2), from the XTOT matrix --
scratchpad/XTOT_run1.out. The case list, the setup and the record are in xtot_cases.py."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import xtot_cases as X  # noqa: E402
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/TOTEXT.md"
GB = 0x5A
OUTPUTS = {"XT": ["rg", "scrmod", "oldscr", "linlen", "crtcnt", "csrx", "csry", "cnsdfg", "sum40", "sum32", "vsum"]}
# the register copies each mode's call leaves (INITXT / INIT32 / INIGRP / INIMLT, from SCREEN 0's), as the reference
# left them on entry to TOTEXT -- and after it
RG = {0: [0x00, 0xF0, 0x00, 0x00, 0x01, 0x00, 0x00, 0xF4], 1: [0x00, 0xE0, 0x06, 0x80, 0x00, 0x36, 0x07, 0x04],
      3: [0x00, 0xE8, 0x02, 0x00, 0x00, 0x36, 0x07, 0x04]}
# the reference's VRAM sums after a mode change (the font and the boot-time key labels included: literal), per
# (OLDSCR, CNSDFG on entry): (sum of $0000-$03BF, sum of $1800-$1AFF, sum of all 16 KB)
VREF = {(0, 0): (30720, 3584, 20751), (0, 1): (32290, 3584, 22321), (1, 0): (7280, 24576, 35839),
        (1, 1): (7280, 26146, 37409), (0x5A, 0): (65280, 3584, 2224), (0x5A, 1): (65280, 3584, 2224)}


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XTOT_run1.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        cs = X.decode(bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1)))
        for c in cs:
            c.src, c.id = "XT", f"XT {c.idx:02}"
        out[who] = cs
    return out


def grp(c):
    return c.mode >= 2


S1 = "1. TOTEXT ($00D2): back to a text screen"

RULES = [
    Rule("R-T-TEXT", S1, "In SCREEN 0 or 1 TOTEXT does nothing: the register copies, SCRMOD, OLDSCR (0, 1 or "
         "garbage), LINLEN, the cursor, CNSDFG and every VRAM byte stay as found.", lambda c: not grp(c),
         lambda c: (c.rg == RG[c.mode] and (c.scrmod, c.oldscr, c.linlen) == (c.mode, c.old, 40 if c.mode == 0 else 32)
                    and (c.csrx, c.csry, c.cnsdfg) == (7, 5, c.cns)
                    and (c.sum40, c.sum32, c.vsum) == ((GB * 960) & 0xFFFF, (GB * 768) & 0xFFFF,
                                                       (GB * 16384) & 0xFFFF))),
    Rule("R-T-OLD0", S1, "In SCREEN 2 or 3 with OLDSCR 0 it is INITXT (docs/bios/INITXT.md): SCREEN 0, LINLEN := "
         "LINL40 (37), the cursor home, CNSDFG 255 when it was on, INITXT's registers -- every VRAM sum the "
         "reference's.", lambda c: grp(c) and c.old == 0,
         lambda c: (c.rg == RG[0] and (c.scrmod, c.oldscr, c.linlen) == (0, 0, 37)
                    and (c.csrx, c.csry, c.cnsdfg) == (1, 1, 255 if c.cns else 0)
                    and (c.sum40, c.sum32, c.vsum) == VREF[(0, c.cns)])),
    Rule("R-T-OLD1", S1, "With OLDSCR 1 it is INIT32: SCREEN 1, LINLEN := LINL32 (29), the cursor home, CNSDFG 255 "
         "when it was on, INIT32's registers -- every VRAM sum the reference's.", lambda c: grp(c) and c.old == 1,
         lambda c: (c.rg == RG[1] and (c.scrmod, c.oldscr, c.linlen) == (1, 1, 29)
                    and (c.csrx, c.csry, c.cnsdfg) == (1, 1, 255 if c.cns else 0)
                    and (c.sum40, c.sum32, c.vsum) == VREF[(1, c.cns)])),
    Rule("R-T-OLDX", S1, "With a garbage OLDSCR ($5A) the reference sets up SCREEN 3 (the multicolour registers, "
         "SCRMOD 3; OLDSCR, the cursor and CNSDFG left as found), from SCREEN 2 and 3 alike -- not a text screen.",
         lambda c: grp(c) and c.old == 0x5A,
         lambda c: (c.rg == RG[3] and (c.scrmod, c.oldscr) == (3, 0x5A) and (c.csrx, c.csry, c.cnsdfg) == (7, 5, c.cns)
                    and (c.sum40, c.sum32, c.vsum) == VREF[(0x5A, c.cns)])),
    Rule("R-T-CRTCNT", S1, "CRTCNT is never changed (24).", lambda c: True, lambda c: c.crtcnt == 24),
]

UNREAD = {f"XT {i:02}": (["linlen"], "garbage-OLDSCR cases: the reference's SCREEN 3 set-up leaves LINLEN, so its "
                                    "value is the previous case's")
          for i, c in enumerate(X.CASES) if c.mode >= 2 and c.old == 0x5A}
