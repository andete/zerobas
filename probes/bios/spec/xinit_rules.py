#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/INITXT.md's EXECUTABLE RULES (docs/spec-method.md §3a): INITXT ($006C) and INIT32 ($006F), from
the XINIT matrix round 2 -- scratchpad/XINIT_run4.out (a SEPARATING setup: the other width cell 77, CRTCNT 13,
the register copies $A5, CNSDFG 2 / $80 / $FF, colours above 15, moved screen-table cells, a display-off
entry; the record ends in a sentinel). Runs 1 / 2 used round 1's setup (kept, not read here; run 2 is cited
in prose for CRTCNT 24). The case list and the record are in xinit_cases.py."""
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
SP, GB = 32, 0x5A            # a space; the probe's VRAM garbage
OUTPUTS = {"XI": ["rg", "scrmod", "oldscr", "linlen", "crtcnt", "csrx", "csry", "cnsdfg", "lt", "namesum",
                  "patsum", "colsum", "tailsum", "atrsum", "lastrow", "row13"]}
# the screen-table cells TXTNAM .. T32PAT the setup writes (xinit.asm `tables` / `tables2`)
TABLES = ([0x0000, 0x0000, 0x0800, 0x0000, 0x0000, 0x1800, 0x2000, 0x0000, 0x1B00, 0x3800],
          [0x1000, 0x1234, 0x2800, 0x3456, 0x3A00, 0x1C00, 0x2FC0, 0x3000, 0x1F80, 0x0800])
FONT_SUM = 31375             # the VG-8020's pattern-table sum after either call: its font
CRT = 13                     # the setup's CRTCNT

# The reference's values with the key line on, LITERAL (generated from run 4's reference half; the cases that
# share a key -- entered from SCREEN 2, display off, CNSDFG 1 / 2 / $80 / $FF -- all gave the same values).
KEY_REF = {   # (call, width, moved tables, FORCLR) -> (namesum, colsum, tailsum, atrsum, row 13, last row)
    ('INITXT', 0, 0, 15): (582, 0, 8160, 0, '0000000000000000000000000000000000000000ffff0000ffff0000ffff0000ffff0000ffff0000', '0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff'),
    ('INITXT', 1, 0, 15): (30720, 1024, 5760, 4096, '20202020202020202020202020202020202020202020202020202020202020202020202020202020', '20202020202020202020202020202020202020202020202020202020202020202020202020202020'),
    ('INITXT', 32, 0, 15): (31975, 1024, 5760, 4096, '202020206b65793020206b65793120206b65793220206b65793320206b6579342020202020202020', '20202020202020202020202020202020202020202020202020202020202020202020202020202020'),
    ('INITXT', 36, 0, 15): (31975, 1024, 5760, 4096, '20206b6579302020206b6579312020206b6579322020206b6579332020206b657934202020202020', '20202020202020202020202020202020202020202020202020202020202020202020202020202020'),
    ('INITXT', 37, 0, 15): (31975, 1024, 5760, 4096, '20206b6579302020206b6579312020206b6579322020206b6579332020206b657934202020202020', '20202020202020202020202020202020202020202020202020202020202020202020202020202020'),
    ('INITXT', 38, 0, 15): (31975, 1024, 5760, 4096, '206b6579302020206b6579312020206b6579322020206b6579332020206b65793420202020202020', '20202020202020202020202020202020202020202020202020202020202020202020202020202020'),
    ('INITXT', 39, 0, 15): (31975, 1024, 5760, 4096, '206b657930202020206b657931202020206b657932202020206b657933202020206b657934202020', '20202020202020202020202020202020202020202020202020202020202020202020202020202020'),
    ('INITXT', 40, 0, 15): (31975, 1024, 5760, 4096, '6b657930202020206b657931202020206b657932202020206b657933202020206b65793420202020', '20202020202020202020202020202020202020202020202020202020202020202020202020202020'),
    ('INITXT', 41, 0, 15): (31943, 1024, 5760, 4096, '6b657930202020206b657931202020206b657932202020206b657933202020206b65793420202020', '20202020202020202020202020202020202020202020202020202020202020202020202020202020'),
    ('INITXT', 80, 0, 15): (30951, 1024, 5760, 4096, '20202020202020202020202020202020202020202020202020202020202020202020202020202020', '20202020202020202020202020202020202020202020202020202020202020202020202020202020'),
    ('INITXT', 255, 0, 15): (30467, 1024, 5760, 4096, '2020202020202020202020202020202020202020206b6579302020202020202020202020206b6579', '20202020202020202020202020202020202020202020202020202020202020202020202020202020'),
    ('INIT32', 0, 0, 15): (54388, 1375, 24494, 8174, '00000000000000000000000000000000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000', '0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffffd100000fd100010f'),
    ('INIT32', 1, 0, 15): (24576, 7808, 22064, 10544, '20202020202020202020202020202020202020202020202020202020202020202020202020202020', '2020202020202020202020202020202020202020202020202020202020202020d15a000fd15a010f'),
    ('INIT32', 28, 0, 15): (25831, 7808, 22064, 10544, '20206b657930206b657931206b657932206b657933206b6579342020202020202020202020202020', '2020202020202020202020202020202020202020202020202020202020202020d15a000fd15a010f'),
    ('INIT32', 29, 0, 15): (25831, 7808, 22064, 10544, '20206b65793020206b65793120206b65793220206b65793320206b65793420202020202020202020', '2020202020202020202020202020202020202020202020202020202020202020d15a000fd15a010f'),
    ('INIT32', 30, 0, 15): (25831, 7808, 22064, 10544, '206b65793020206b65793120206b65793220206b65793320206b6579342020202020202020202020', '2020202020202020202020202020202020202020202020202020202020202020d15a000fd15a010f'),
    ('INIT32', 31, 0, 15): (25831, 7808, 22064, 10544, '206b65793020206b65793120206b65793220206b65793320206b6579342020202020202020202020', '2020202020202020202020202020202020202020202020202020202020202020d15a000fd15a010f'),
    ('INIT32', 32, 0, 15): (25831, 7808, 22064, 10544, '6b65793020206b65793120206b65793220206b65793320206b657934202020202020202020202020', '2020202020202020202020202020202020202020202020202020202020202020d15a000fd15a010f'),
    ('INIT32', 33, 0, 15): (25831, 7808, 22064, 10544, '6b65793020206b65793120206b65793220206b65793320206b657934202020202020202020202020', '2020202020202020202020202020202020202020202020202020202020202020d15a000fd15a010f'),
    ('INIT32', 255, 0, 15): (24325, 7808, 22064, 10544, '20202020202020202020202020202020206b6579302020202020202020202020206b657931202020', '2020202020202020202020202020202020202020202020202020202020202020d15a000fd15a010f'),
    ('INITXT', 40, 0, 58): (31975, 1024, 5760, 4096, '6b657930202020206b657931202020206b657932202020206b657933202020206b65793420202020', '20202020202020202020202020202020202020202020202020202020202020202020202020202020'),
    ('INITXT', 40, 1, 15): (31975, 1277, 5760, 11520, '6b657930202020206b657931202020206b657932202020206b657933202020206b65793420202020', '20202020202020202020202020202020202020202020202020202020202020202020202020202020'),
    ('INIT32', 32, 0, 58): (25831, 7328, 23440, 11920, '6b65793020206b65793120206b65793220206b65793320206b657934202020202020202020202020', '2020202020202020202020202020202020202020202020202020202020202020d15a003ad15a013a'),
    ('INIT32', 32, 1, 15): (25831, 7808, 22064, 10544, '6b65793020206b65793120206b65793220206b65793320206b657934202020202020202020202020', '20202020202020202020202020202020202020202020202020202020202020205a5a5a5a5a5a5a5a'),
}


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XINIT_run4.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        cs = X.decode(bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1)))
        for c in cs:
            c.src, c.id = "XI", f"XI {c.idx:02}"
        out[who] = cs
    return out


def is_txt(c):
    return c.call == X.INITXT


def cols(c):
    return 40 if is_txt(c) else 32


def w0key(c):
    return c.key and c.width == 0


def key_ref(c):
    n, col, tl, atr, r13, last = KEY_REF[(c.name, c.width, c.tbl, c.fg)]
    return n, col, tl, atr, list(bytes.fromhex(r13)), list(bytes.fromhex(last))


UNREAD = {f"XI {i:02}": ((["colsum", "atrsum"] if not c.tbl else ["colsum"]),
                             "INITXT has no colour table and no sprites: with the key line off the bytes at R3's / "
                             "R5's base are name-table cells (already in namesum) or, moved, left as found")
          for i, c in enumerate(X.CASES) if c.call == X.INITXT and not c.key}

TXT, T32 = "1. INITXT ($006C): 40-column text (SCREEN 0)", "2. INIT32 ($006F): 32-column text (SCREEN 1)"
B = "3. Both"


def regs(c, t):
    return [t[0] >> 10, t[1] >> 6, t[2] >> 11, t[3] >> 7, t[4] >> 11]


RULES = [
    Rule("R-I-REGS-TXT", TXT, "R1..R7 (their copies RG1SAV..RG7SAV) are computed, never left as found: R1 = $F0 + the "
         "copy's low 3 bits (sprite size / magnify / bit 2 kept; here $A5 gives F5); R2 / R3 / R4 / R5 / R6 from "
         "TXTNAM / TXTCOL / TXTCGP / TXTATR / TXTPAT (moved: 04 48 05 68 07); R7 = FORCLR·16 + BAKCLR in 8 bits "
         "($3A, $C5 gives E5; the border colour is not used).",
         lambda c: is_txt(c),
         lambda c: c.rg[1:] == [0xF0 | (0xA5 & 7)] + regs(c, TABLES[c.tbl][0:5]) + [((c.fg << 4) | c.bg) & 0xFF]),
    Rule("R-I-TAIL-TXT", TXT, "The 64 bytes after the 960 name cells are left as found, at every width (41, 80, 255 "
         "included).", lambda c: is_txt(c) and not w0key(c), lambda c: c.tailsum == 64 * GB),
    Rule("R-I-ATR-TXT", TXT, "No sprite attribute table is written: moved (TXTATR $3456), the 128 bytes at R5's "
         "base are left as found.", lambda c: is_txt(c) and c.tbl, lambda c: c.atrsum == 128 * GB),
    Rule("R-I-REGS-32", T32, "R1 = $E0 + the copy's low 3 bits (E5); R2..R6 from T32NAM / T32COL / T32CGP / T32ATR "
         "/ T32PAT (moved: 07 BF 06 3F 01); R7 = BDRCLR as it is ($F9 stays F9).",
         lambda c: not is_txt(c),
         lambda c: c.rg[1:] == [0xE0 | (0xA5 & 7)] + regs(c, TABLES[c.tbl][5:10]) + [c.bd]),
    Rule("R-I-COL32", T32, "The colour table's 32 bytes all become FORCLR·16 + BAKCLR in 8 bits.",
         lambda c: not is_txt(c) and not w0key(c), lambda c: c.colsum == 32 * (((c.fg << 4) | c.bg) & 0xFF)),
    Rule("R-I-SPR32", T32, "The sprite attribute table (32 entries at T32ATR) is written: each entry Y = 209 ($D1, "
         "the sprite is off screen), X left as found, the pattern = the sprite's number, the colour = FORCLR as it is "
         "($3A stays 3A). Read byte for byte in entries 0 and 1 (the 8 cells after the name table, default tables) "
         "and as the sum for all 32; the rest of the 1 KB name block is left as found.",
         lambda c: not is_txt(c) and not w0key(c),
         lambda c: (c.atrsum == 32 * (209 + GB + c.fg) + sum(range(32)) and c.tailsum == 128 * GB + c.atrsum
                    and c.lastrow[32:] == ([GB] * 8 if c.tbl else [209, GB, 0, c.fg, 209, GB, 1, c.fg]))),
    Rule("R-I-R0", B, "R0 (RG0SAV) keeps only bit 0 (external video) of the copy: $A5 gives 01, also from SCREEN 2 "
         "and with M3 set in the VDP.", lambda c: True, lambda c: c.rg[0] == 0xA5 & 1),
    Rule("R-I-MODE", B, "SCRMOD and OLDSCR become 0 (INITXT) / 1 (INIT32), also from SCREEN 2.",
         lambda c: True, lambda c: (c.scrmod, c.oldscr) == ((0, 0) if is_txt(c) else (1, 1))),
    Rule("R-I-LINLEN", B, "LINLEN becomes LINL40 (INITXT) / LINL32 (INIT32) AS IT IS: 0, 1, 80, 255 included -- no "
         "validation; the other call's cell (77) is not used.", lambda c: True, lambda c: c.linlen == c.width),
    Rule("R-I-HOME", B, "The cursor goes home: CSRX 1, CSRY 1.", lambda c: True, lambda c: (c.csrx, c.csry) == (1, 1)),
    Rule("R-I-CRTCNT", B, "CRTCNT is NOT written: the setup's 13 stays 13, key line on or off.",
         lambda c: True, lambda c: c.crtcnt == CRT),
    Rule("R-I-CNSDFG", B, "CNSDFG becomes 255 when it was non-zero (1, 2, $80, $FF), 0 when it was 0.",
         lambda c: True, lambda c: c.cnsdfg == (255 if c.key else 0)),
    Rule("R-I-LT", B, "LINTTB becomes 24, 23, …, 1 down the rows.", lambda c: True,
         lambda c: c.lt == [24 - r for r in range(24)]),
    Rule("R-I-CLEAR", B, "With the key line off the name table is cleared to spaces (960 / 768 cells): row 13 and "
         "the last row read blank.", lambda c: not c.key,
         lambda c: (c.namesum == SP * (960 if is_txt(c) else 768) and c.lastrow[:cols(c)] == [SP] * cols(c)
                    and c.row13 == [SP] * 40)),
    Rule("R-I-KEYS", B, "With the key line on, the key line is drawn on row CRTCNT -- row 13 here, NOT the last row "
         "(which stays blank) -- and shows the FIRST five function keys' labels, placed by the width ('key0' at "
         "column 1 for widths 40 / 41 / 32 / 33, the labels 8 / 6 cells apart). Run 2 (CRTCNT 24 as found) drew it on "
         "the last row. Entering from SCREEN 2, with the display off, or with CNSDFG 2 / $80 / $FF gives the same "
         "cells. Every cell and sum as the reference's.",
         lambda c: c.key and c.width not in (0, 1, 80, 255),
         lambda c: (c.namesum, c.colsum, c.tailsum, c.atrsum, c.row13, c.lastrow) == key_ref(c)),
    Rule("R-I-KEYEDGE", B, "Key line on with width 0, 1, 80 or 255: as the reference leaves it. Width 1 / 80: row 13 "
         "blank (80: labels elsewhere, the name sum 30951); width 255: labels from column 22 of row 13; width 0: "
         "the name table is NOT cleared to spaces but mostly to 0 with $FF pairs, INIT32 also over its colour and "
         "sprite tables.",
         lambda c: c.key and c.width in (0, 1, 80, 255),
         lambda c: (c.namesum, c.colsum, c.tailsum, c.atrsum, c.row13, c.lastrow) == key_ref(c)),
    Rule("R-I-FONT", B, "The pattern table holds the font (the VG-8020's sums to 31375).",
         lambda c: True, lambda c: c.patsum == FONT_SUM),
]
