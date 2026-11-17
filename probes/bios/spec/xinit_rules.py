#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/INITXT.md's EXECUTABLE RULES (docs/spec-method.md §3a): INITXT ($006C) and INIT32 ($006F), from
the XINIT matrix -- scratchpad/XINIT_run2.out (run 2: FNKSTR set by the setup; run 1 is kept but not used,
its key rows were the setup's). The case list and the record are documented in xinit_cases.py."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import xinit_cases as X  # noqa: E402
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/INITXT.md"
SP = 32
OUTPUTS = {"XI": ["rg", "scrmod", "oldscr", "linlen", "crtcnt", "csrx", "csry", "cnsdfg", "lt", "namesum",
                  "patsum", "colsum", "keyrow"]}

# the VG-8020's key row with the key line on (key strings "key0".."key9"), per call and width: its
# name-table sum and the last row's first 7 cells (literal reference values; zerobas is compared to them)
KEY_REF = {('INITXT', 0): (15750, [0] * 7), ('INITXT', 1): (30720, [32] * 7),
           ('INITXT', 32): (31975, [32, 32, 32, 32, 107, 101, 121]), ('INITXT', 36): (31975, [32, 32, 107, 101, 121, 48, 32]),
           ('INITXT', 37): (31975, [32, 32, 107, 101, 121, 48, 32]), ('INITXT', 38): (31975, [32, 107, 101, 121, 48, 32, 32]),
           ('INITXT', 39): (31975, [32, 107, 101, 121, 48, 32, 32]), ('INITXT', 40): (31975, [107, 101, 121, 48, 32, 32, 32]),
           ('INITXT', 41): (31975, [107, 101, 121, 48, 32, 32, 32]), ('INITXT', 80): (30720, [32] * 7),
           ('INITXT', 255): (31202, [32] * 7), ('INIT32', 0): (11143, [0] * 7), ('INIT32', 1): (24576, [32] * 7),
           ('INIT32', 28): (25831, [32, 32, 107, 101, 121, 48, 32]), ('INIT32', 29): (25831, [32, 32, 107, 101, 121, 48, 32]),
           ('INIT32', 30): (25831, [32, 107, 101, 121, 48, 32, 32]), ('INIT32', 31): (25831, [32, 107, 101, 121, 48, 32, 32]),
           ('INIT32', 32): (25831, [107, 101, 121, 48, 32, 32, 107]), ('INIT32', 33): (25831, [107, 101, 121, 48, 32, 32, 107]),
           ('INIT32', 255): (24825, [32] * 7)}
FONT_SUM = 31375          # the VG-8020's pattern-table sum after either call: its font


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XINIT_run2.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        b = b + bytes(X.caplen() - len(b))
        cs = X.decode(b)
        for c in cs:
            c.src, c.id = "XI", f"XI {c.idx:02}"
        out[who] = cs
    return out


UNREAD = {f"XI {c_i:02}": (["colsum"], "INITXT's text mode has no colour table: the 32 bytes at RG3's base are "
                                       "the name table's")
          for c_i, c in enumerate(X.CASES) if c.call == X.INITXT}

TXT, T32 = "1. INITXT ($006C): 40-column text (SCREEN 0)", "2. INIT32 ($006F): 32-column text (SCREEN 1)"
B = "3. Both"


def is_txt(c):
    return c.call == X.INITXT


RULES = [
    Rule("R-I-REGS-TXT", TXT, "The VDP registers (their copies RG0SAV..RG7SAV) become 00 F0 00 00 01 00 00, and R7 = "
         "FORCLR·16 + BAKCLR (the border colour is not used); R2 / R4 come from TXTNAM / TXTCGP.",
         lambda c: is_txt(c), lambda c: c.rg == [0, 0xF0, 0, 0, 1, 0, 0, (c.fg << 4) | c.bg]),
    Rule("R-I-REGS-32", T32, "The VDP registers become 00 E0 06 80 00 36 07, and R7 = BDRCLR (the border); R2..R6 come "
         "from T32NAM / T32COL / T32CGP / T32ATR / T32PAT.",
         lambda c: not is_txt(c), lambda c: c.rg == [0, 0xE0, 6, 0x80, 0, 0x36, 7, c.bd]),
    Rule("R-I-COL32", T32, "The colour table's 32 bytes all become FORCLR·16 + BAKCLR.",
         lambda c: not is_txt(c) and not (c.key and c.width == 0), lambda c: c.colsum == 32 * ((c.fg << 4) | c.bg)),
    Rule("R-I-MODE", B, "SCRMOD and OLDSCR become 0 (INITXT) / 1 (INIT32), also from SCREEN 2.",
         lambda c: True, lambda c: (c.scrmod, c.oldscr) == ((0, 0) if is_txt(c) else (1, 1))),
    Rule("R-I-LINLEN", B, "LINLEN becomes LINL40 (INITXT) / LINL32 (INIT32) AS IT IS: 0, 1, 80, 255 included -- no "
         "validation.", lambda c: True, lambda c: c.linlen == c.width),
    Rule("R-I-HOME", B, "CRTCNT becomes 24 and the cursor goes home (CSRX 1, CSRY 1).",
         lambda c: True, lambda c: (c.crtcnt, c.csrx, c.csry) == (24, 1, 1)),
    Rule("R-I-CNSDFG", B, "CNSDFG reads 255 when it was set (non-zero), 0 when it was 0.",
         lambda c: True, lambda c: c.cnsdfg == (255 if c.key else 0)),
    Rule("R-I-LT", B, "LINTTB becomes 24, 23, …, 1 down the rows.", lambda c: True,
         lambda c: c.lt == [24 - r for r in range(24)]),
    Rule("R-I-CLEAR", B, "With the key line off the name table is cleared to spaces (960 / 768 cells).",
         lambda c: not c.key, lambda c: c.namesum == 32 * (960 if is_txt(c) else 768) and c.keyrow == [SP] * 7),
    Rule("R-I-KEYS", B, "With the key line on, the last row shows the FIRST five function keys' labels, placed by "
         "the width (here 'key0' at column 1 for widths 40 / 41 / 32 / 33); the cells are the reference's.",
         lambda c: c.key and c.width not in (0, 1, 80, 255),
         lambda c: (c.namesum, c.keyrow) == KEY_REF[(c.name, c.width)]),
    Rule("R-I-KEYEDGE", B, "Key line on with width 0, 1, 80 or 255: the last row as the reference leaves it (width 1 / "
         "80: blank; width 0: cells 0; width 255: labels outside the first 7 cells).",
         lambda c: c.key and c.width in (0, 1, 80, 255),
         lambda c: (c.namesum, c.keyrow) == KEY_REF[(c.name, c.width)]),
    Rule("R-I-W0-COL", T32, "INIT32 with width 0 and the key line on also writes into the colour table (its sum "
         "1252 on the reference): the key line drawn at width 0 runs past the name table.",
         lambda c: not is_txt(c) and c.key and c.width == 0, lambda c: c.colsum == 1252),
    Rule("R-I-FONT", B, "The pattern table holds the font (the VG-8020's sums to 31375).",
         lambda c: True, lambda c: c.patsum == FONT_SUM),
]
