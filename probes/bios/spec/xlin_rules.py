#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/PINLIN.md's EXECUTABLE RULES (docs/spec-method.md §3a): PINLIN ($00AE), QINLIN ($00B4) and INLIN ($00B1),
from the keyed XLIN probe -- scratchpad/XLIN_run1.out (probes/bios/spec/xlin.asm documents the six calls, the typed
burst and the 29-byte record)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/PINLIN.md"
OUTPUTS = {"XL": ["stage", "hl", "f", "csrx", "csry", "buf", "row"]}
BUFM1 = 0xF55D                  # BUF ($F55E) − 1
# the six calls (xlin.asm): the call, the cursor at entry, the row's pre-written text, the typed keys
CALLS = [("PINLIN", 1, 3, b"", b"AB"), ("QINLIN", 1, 5, b"", b"CD"), ("PINLIN", 4, 7, b"XYZ", b"Q"),
         ("INLIN", 4, 9, b"XYZ", b"Q"), ("PINLIN", 1, 11, b"", b"AC"), ("PINLIN", 1, 13, b"XYZ", b"")]


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XLIN_run1.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        if len(b) < 1 + 29 * 6 + 1 or b[1 + 29 * 6] != 0xC3:
            sys.exit("FAIL: the XLIN block has no sentinel after six records")
        cs = []
        for i, (name, x, y, pre, typed) in enumerate(CALLS):
            r = b[1 + 29 * i: 30 + 29 * i]
            cs.append(NS(src="XL", id=f"XL {i + 1}", name=name, x=x, y=y, pre=pre, typed=typed, stage=b[0],
                         hl=r[0] | (r[1] << 8), f=r[2], csrx=r[3], csry=r[4], buf=list(r[5:17]), row=list(r[17:29])))
        out[who] = cs
    return out


def shown(c):
    """The row's text after the input: the pre-written cells, the prompt, then what was typed from the cursor."""
    if c.name == "QINLIN":
        return b"? " + c.typed
    return (c.pre + b" " * 12)[:c.x - 1] + c.typed if c.typed else c.pre


def buf_of(text):
    """BUF as recorded: the text, its terminating 0, then the spaces the reference leaves after it."""
    return list((text + b"\0" + b" " * 12)[:12])


S1 = "1. PINLIN ($00AE), QINLIN ($00B4), INLIN ($00B1): read a line"

RULES = [
    Rule("R-L-PIN", S1, "PINLIN returns the WHOLE screen line the cursor is on, from column 1 -- text that was on the "
         "line before the call included ('XYZ' + typed 'Q' gives 'XYZQ'; Enter alone over 'XYZ' gives 'XYZ'), with "
         "BS editing applied ('AB' BS 'C' gives 'AC') -- in BUF, terminated by 0.",
         lambda c: c.name == "PINLIN", lambda c: c.buf == buf_of(shown(c))),
    Rule("R-L-INLIN", S1, "INLIN returns only the text from the column the cursor was at when it was called ('XYZ' "
         "before the cursor, typed 'Q': 'Q').", lambda c: c.name == "INLIN", lambda c: c.buf == buf_of(c.typed)),
    Rule("R-L-QIN", S1, "QINLIN first prints '? ' and returns the text typed after it (the prompt not included).",
         lambda c: c.name == "QINLIN", lambda c: c.buf == buf_of(c.typed)),
    Rule("R-L-RET", S1, "All three return HL = BUF − 1 ($F55D) with the carry clear (Enter, not STOP), echo the line "
         "on the screen, and leave the cursor at column 1 of the next row.", lambda c: True,
         lambda c: (c.stage == 6 and c.hl == BUFM1 and c.f & 1 == 0 and (c.csrx, c.csry) == (1, c.y + 1)
                    and c.row == list((shown(c) + b" " * 12)[:12]))),
    Rule("R-L-F", S1, "The whole F on return (only the carry published): 18.", lambda c: True, lambda c: c.f == 0x18),
]
