#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/OUTDO.md's EXECUTABLE RULES (docs/spec-method.md §3a): OUTDO ($0018) to the screen and to the printer --
scratchpad/XOUTDO_run2.out (row N) and XOUTDO_run2d.out (row D); probes/bios/spec/xoutdo.asm documents the sections
and the record. docs/bios/ISFLIO.md's rules (xisflio_rules.py) read the same runs: `load()` serves both."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
import xoutdlp_rules as D  # noqa: E402  (OUTDLP's model: the printer path is the same)

PAGE = "docs/bios/OUTDO.md"
RUNS = [("XOUTDO_run2.out", "N"), ("XOUTDO_run2d.out", "D")]
PTRS = [0x0000, 0x0001, 0x0100, 0x8000, 0xFFFF]
SEQ = [0x50, 0x09, 0x5A, 0x01, 0x41, 0x0D, 0x0A]
OUTPUTS = {"XI": ["a", "f", "moved"], "XS": ["y0", "x0", "y1", "x1", "a", "f", "moved"],
           "XO": ["pos", "a", "f", "moved"], "XP": ["prn"], "XV": ["rg2", "tpos", "tcnt", "bpos", "bcnt"]}
SCR = [(5, 3, 0x7E, 0x00), (12, 10, 0x7C, 0xFF)]   # the cursor set by hand (CSRY, CSRX), the character, entry F


def _hex(t, label, key):
    m = re.search(rf"{label} {key}[ \t]*:[ \t]*([0-9a-fA-F]*)", t)
    return bytes.fromhex(m.group(1)) if m else None


def load(which):
    out = {"ref": [], "zb": []}
    for name, row in RUNS:
        t = open(os.path.join(ROOT, "scratchpad", name)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = _hex(t, "CAP", key)
            if b[0] != 0xA5 or len(b) < 70 or b[69] != 0xC3:
                sys.exit(f"FAIL: the {name} block is not complete (no sentinel)")
            if which == "I":
                for i, p in enumerate(PTRS):
                    o = 1 + 3 * i
                    out[who].append(NS(src="XI", id=f"XI {row}{i}", row=row, ptr=p, ef=0xFF if i & 1 else 0,
                                       a=b[o], f=b[o + 1], moved=b[o + 2]))
                continue
            for k, (o, (cy, cx, ch, ef)) in enumerate(zip((16, 55), SCR)):
                out[who].append(NS(src="XS", id=f"XS {row}{k}", row=row, ch=ch, ef=ef, cy=cy, cx=cx, y0=b[o],
                                   x0=b[o + 1], y1=b[o + 2], x1=b[o + 3], a=b[o + 4], f=b[o + 5], moved=b[o + 6]))
            per, prn = D.model(0, 0, SEQ)
            for i, c in enumerate(SEQ + [0x4B]):
                o = 23 + 4 * i
                exp = per[i] if i < len(SEQ) else (per[-1][0] + 1, 0x4B, D.logical(0x4B) | 0x10)
                out[who].append(NS(src="XO", id=f"XO {row}{i}", row=row, c=c, exp=exp, pos=b[o], a=b[o + 1],
                                   f=b[o + 2], moved=b[o + 3]))
            out[who].append(NS(src="XP", id=f"XP {row}", row=row, prn=_hex(t, "PRN", key),
                               expprn=bytes(prn + [0x4B])))
            out[who].append(NS(src="XV", id=f"XV {row}", row=row, rg2=b[62], tpos=b[63] | b[64] << 8, tcnt=b[65],
                               bpos=b[66] | b[67] << 8, bcnt=b[68]))
    return out


def cases():
    return load("O")


S1 = "1. OUTDO ($0018, RST 18h): output a character to the current device"
XS = lambda c: c.src == "XS"  # noqa: E731
XO = lambda c: c.src == "XO"  # noqa: E731

RULES = [
    Rule("R-OU-SCR", S1, "With PRTFLG ($F416) 0 the character goes to the screen and the cursor moves on: from a "
         "cursor set by hand (CSRY 5 / CSRX 3, then 12 / 10) CSRX is one more after the call, CSRY the same.", XS,
         lambda c: (c.y0, c.x0) == (c.cy, c.cx) and (c.y1, c.x1) == (c.cy, c.cx + 1)),
    Rule("R-OU-CELL", S1, "Each character is on the screen once, in the name table (at RG2SAV * $400: $1800, SCREEN 1) "
         "cell (CSRY - 1) * 32 + (CSRX - 1) + 2 of the cursor it was printed at -- $0084 for '~' at 5 / 3, $016B for "
         "'|' at 12 / 10 (read through the VDP's ports; the + 2 is SCREEN 1's left margin as boot left it).",
         lambda c: c.src == "XV",
         lambda c: (c.rg2 == 0x06 and c.tcnt == 1 and c.bcnt == 1
                    and c.tpos == (SCR[0][0] - 1) * 32 + SCR[0][1] - 1 + 2
                    and c.bpos == (SCR[1][0] - 1) * 32 + SCR[1][1] - 1 + 2)),
    Rule("R-OU-KEEP", S1, "A is kept, and BC, DE, HL, IX and IY are kept, to the screen and to the printer.",
         lambda c: c.src in ("XS", "XO"), lambda c: c.a == (c.ch if c.src == "XS" else c.exp[1]) and c.moved == 0),
    Rule("R-OU-SF", S1, "To the screen F is kept ($00, then $FF on entry).", XS, lambda c: c.f == c.ef),
    Rule("R-OU-PRN", S1, "With PRTFLG 1 the character goes to the printer as OUTDLP sends it: the printer receives "
         "'P', the TAB as spaces up to column 8, 'Z', $01 $41 (NTMSXP 0), CR, LF; with PRTFLG $FF, 'K'.",
         lambda c: c.src == "XP",
         lambda c: c.prn == c.expprn),
    Rule("R-OU-POS", S1, "LPTPOS follows the printer's column as OUTDLP keeps it (the graphic character's $01 not "
         "counted).", XO, lambda c: c.pos == c.exp[0]),
    Rule("R-OU-PF", S1, "To the printer F is OUTDLP's: LPTOUT's on the byte sent (an AND's flags), F as on entry "
         "after a TAB ($00 there).", XO, lambda c: c.f == c.exp[2]),
]

