#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/DSPFNK.md's EXECUTABLE RULES (docs/spec-method.md §3a): DSPFNK ($00CF), ERAFNK ($00CC) and FNKSB ($00C9),
from the XKEY matrix -- scratchpad/XKEY_run1.out. The case list, the separating setup and the record are in
xkey_cases.py."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import xkey_cases as X  # noqa: E402
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/DSPFNK.md"
SP, GB = 32, 0x5A                       # a space; the probe's name-table garbage
OUTPUTS = {"XK": ["cnsdfg", "crtcnt", "csrx", "csry", "linlen", "scrmod", "namesum", "row24", "rowc", "rowc1"]}
SPR = [0xD1, 0, 0, 0x0F, 0xD1, 0, 1, 0x0F]  # the sprite attribute table's first 8 bytes, as INIT32 left them

# the label sets the setup writes (xkey.asm `keys` / `keys2`), as byte strings up to their terminating 0
LABELS = ([b"key%d" % k for k in range(10)],
          [b"abcdefghijklmno", b"\x01Ab", b"a\rb", b"", b"\x7f\x1bY"] + [b"k%d" % k for k in range(5, 10)])


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XKEY_run1.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        cs = X.decode(bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1)))
        for c in cs:
            c.src, c.id = "XK", f"XK {c.idx:02}"
        out[who] = cs
    return out


def cols(c):
    return 40 if c.mode == 0 else 32


def cells(lab):
    """A label as the key line shows it: a $01 prefix makes the next character a graphic one (minus $40), a
    control character below $20 shows as a space, anything else as itself."""
    out, i = [], 0
    while i < len(lab):
        b = lab[i]
        if b == 1 and i + 1 < len(lab):
            out.append(lab[i + 1] - 0x40)
            i += 2
            continue
        out.append(SP if b < 0x20 else b)
        i += 1
    return out


def key_line(c, show):
    """The key line's row as the reference draws (show) or erases it: the width's span (LINLEN cells from the left
    margin (columns - width + 1) // 2) becomes spaces, then each of the FIRST five labels from column
    margin + k x slot, slot = (width + 1) // 5, cut to slot - 1 cells. Cells outside the span: left as found."""
    n = cols(c)
    m = (n - c.width + 1) // 2
    row = [GB] * n
    for i in range(m, min(n, m + c.width)):
        row[i] = SP
    if show:
        slot = (c.width + 1) // 5
        for k in range(5):
            for j, ch in enumerate(cells(LABELS[c.lab][k])[:slot - 1]):
                row[m + k * slot + j] = ch
    return row


def shows(c):
    return c.name == "DSPFNK" or (c.name == "FNKSB" and c.cns)


def screen_ok(c):
    """The key line on row CRTCNT, as key_line; every other cell of the name table as found. The 40 cells read
    from a 32-column row run on into the next row (garbage) or, after row 24, the sprite attribute table."""
    n = cols(c)
    row = key_line(c, shows(c))
    total = 960 if n == 40 else 768
    past = (SPR if c.crt == 24 else [GB] * 8) if n == 32 else []
    ok = c.rowc == row + past and c.namesum == (GB * (total - n) + sum(row)) & 0xFFFF
    if c.crt == 24:
        return ok and c.row24 == c.rowc and c.rowc1 == [GB] * n + row[:40 - n]
    return ok and c.row24 == [GB] * 40 and c.rowc1 == [GB] * 40


def untouched(c):
    n = cols(c)
    total = 960 if n == 40 else 768
    past = (SPR if c.crt == 24 else [GB] * 8) if n == 32 else []
    return (c.namesum == (GB * total) & 0xFFFF and c.rowc == [GB] * n + past and c.rowc1 == [GB] * 40
            and c.row24 == [GB] * n + (SPR if n == 32 else []))


S1, S2, S3, S4 = ("1. DSPFNK ($00CF): show the key line", "2. ERAFNK ($00CC): erase the key line",
                  "3. FNKSB ($00C9): show it if it is on", "4. All three")

RULES = [
    Rule("R-K-DSP", S1, "DSPFNK sets CNSDFG to 255 (from 0, 1 or $80) and draws the key line on row CRTCNT (24 or "
         "13; NOT row 24 when CRTCNT is 13). Within the width's span (LINLEN cells from the left margin "
         "(columns − width + 1) ÷ 2, the cells outside it left as found): spaces, then the FIRST five labels from "
         "column margin + k × slot, slot = (width + 1) ÷ 5 (8 at 40, 7 at 37, 6 at 32 / 29), each cut to slot − 1 "
         "cells. Every other cell of the name table is left as found.",
         lambda c: c.name == "DSPFNK" and c.mode != 2 and not c.lab,
         lambda c: c.cnsdfg == 255 and screen_ok(c)),
    Rule("R-K-LABELS", S1, "A label shows as its bytes, with a $01 prefix making the next character a graphic one "
         "(its code − $40: `$01 'A'` shows cell 01), a control character below $20 (CR, ESC) as a space, DEL as "
         "itself, and the label cut to slot − 1 cells ('abcdefghijklmno' shows 'abcdefg' at width 40, 'abcde' at "
         "32); an empty label leaves its slot blank.",
         lambda c: c.name == "DSPFNK" and c.lab, lambda c: c.cnsdfg == 255 and screen_ok(c)),
    Rule("R-K-ERA", S2, "ERAFNK sets CNSDFG to 0 and clears the key line's row (row CRTCNT) to spaces WITHIN the "
         "width's span only -- at width 37 / 39 / 29 the margin cells are left as found. Every other cell is left "
         "as found.", lambda c: c.name == "ERAFNK" and c.mode != 2, lambda c: c.cnsdfg == 0 and screen_ok(c)),
    Rule("R-K-SB-ON", S3, "FNKSB with CNSDFG non-zero (1, $80) is DSPFNK: CNSDFG 255 and the key line drawn.",
         lambda c: c.name == "FNKSB" and c.cns and c.mode != 2, lambda c: c.cnsdfg == 255 and screen_ok(c)),
    Rule("R-K-SB-OFF", S3, "FNKSB with CNSDFG 0 does NOTHING: it does not erase; the name table keeps its garbage "
         "and CNSDFG stays 0.", lambda c: c.name == "FNKSB" and not c.cns and c.mode != 2,
         lambda c: c.cnsdfg == 0 and untouched(c)),
    Rule("R-K-FNKFLG", S3, "FNKFLG (the ten function-key trap flags, 1 or $FF) makes no difference to FNKSB.",
         lambda c: c.name == "FNKSB" and c.flg, lambda c: c.cnsdfg == (255 if c.cns else 0)
         and (screen_ok(c) if c.cns else untouched(c))),
    Rule("R-K-GRP", S4, "In SCREEN 2 all three only set CNSDFG (DSPFNK 255, ERAFNK 0, FNKSB 255 if it was non-zero) "
         "and leave the name table as found.", lambda c: c.mode == 2,
         lambda c: c.cnsdfg == (255 if shows(c) else 0) and untouched(c)),
    Rule("R-K-STATE", S4, "None of them moves the cursor (CSRX 7, CSRY 5 stay), or changes CRTCNT, LINLEN or SCRMOD.",
         lambda c: True, lambda c: (c.csrx, c.csry, c.crtcnt, c.scrmod) == (7, 5, c.crt, c.mode)
         and (c.mode == 2 or c.linlen == c.width)),
]

UNREAD = {f"XK {i:02}": (["linlen"], "SCREEN 2 cases: the setup does not set LINLEN there (INIGRP does not), so "
                                    "its value is the previous case's")
          for i, c in enumerate(X.CASES) if c.mode == 2}
