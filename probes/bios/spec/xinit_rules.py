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
import xinit3_cases as X3  # noqa: E402
import xinit4_cases as X4  # noqa: E402
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/INITXT.md"
SP, GB = 32, 0x5A            # a space; the probe's VRAM garbage
OUTPUTS = {"XI": ["rg", "scrmod", "oldscr", "linlen", "crtcnt", "csrx", "csry", "cnsdfg", "lt", "namesum",
                  "patsum", "colsum", "tailsum", "atrsum", "lastrow", "row13"]}
OUTPUTS["XJ"] = OUTPUTS["XI"] + ["rowc", "linl40", "linl32", "colours", "tables", "fnksum", "vsum", "col"]
OUTPUTS["XJ4"] = OUTPUTS["XJ"]
# the screen-table cells TXTNAM .. T32PAT the setup writes (xinit.asm `tables` / `tables2`)
TABLES = ([0x0000, 0x0000, 0x0800, 0x0000, 0x0000, 0x1800, 0x2000, 0x0000, 0x1B00, 0x3800],
          [0x1000, 0x1234, 0x2800, 0x3456, 0x3A00, 0x1C00, 0x2FC0, 0x3000, 0x1F80, 0x0800],
          [0x1000, 0x2000, 0x2800, 0x1800, 0x3A00, 0x1C00, 0x2FC0, 0x3000, 0x1F80, 0x0800])
LABELS = [b"key%d" % k for k in range(10)]  # the setup's FNKSTR
LABELS7 = [b"ABCDEF%d" % k for k in range(10)]   # XINIT4's 7-character labels (lab 1)
FNK_SUM = sum(sum(lab) for lab in LABELS)
FNK_SUM7 = sum(sum(lab) for lab in LABELS7)


EDGE4COL = {   # the same cases' 32 bytes at R3's base, the reference's
    16: '0000000000000000000000000000000000000000000000000000000000000000',
    17: '2020202020202020202020202020202020202020202020202020202020202020',
    18: '2020202020202020202020202020202020202020202020202020202020202020',
    19: '000000001800200000001b0038e70e0f51202020202020202020202020202020',
    20: 'f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4',
}


def g(c):
    """The case's VRAM garbage byte ($5A, or XINIT4's `fill`)."""
    return getattr(c, "fill", 0x5A)


def labels(c):
    return LABELS7 if getattr(c, "lab", 0) else LABELS


# XJ4 edge widths (0 / 80 / 255, key line on): index -> (namesum, colsum, tailsum, atrsum, vsum, row13, lastrow,
# rowc), the reference's -- literal, like KEY_REF
EDGE4 = {
    16: (582, 0, 8160, 0, 43982,
         '0000000000000000000000000000000000000000ffff0000ffff0000ffff0000ffff0000ffff0000',
         '0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff',
         '0000000000000000000000000000000000000000ffff0000ffff0000ffff0000ffff0000ffff0000'),
    17: (30951, 1024, 5760, 4096, 20982,
         '20202020202020202020202020202020202020202020202020202020202020202020202020202020',
         '20202020202020202020202020202020202020202020202020202020202020202020202020202020',
         '20202020202020202020202020202020202020202020202020202020202020202020202020202020'),
    18: (30467, 1024, 5760, 4096, 20498,
         '2020202020202020202020202020202020202020206b6579302020202020202020202020206b6579',
         '20202020202020202020202020202020202020202020202020202020202020202020202020202020',
         '2020202020202020202020202020202020202020206b6579302020202020202020202020206b6579'),
    19: (54388, 960, 24494, 8174, 19914,
         '00000000000000000000000000000000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000',
         '0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000ffffd100000fd100010f',
         '00000000000000000000000000000000ffff0000ffff0000ffff0000ffff0000ffff0000ffff0000'),
    20: (24325, 7808, 22064, 10544, 35588,
         '20202020202020202020202020202020206b6579302020202020202020202020206b657931202020',
         '2020202020202020202020202020202020202020202020202020202020202020d15a000fd15a010f',
         '20202020202020202020202020202020206b6579302020202020202020202020206b657931202020'),
}

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
    """Two groups: XI = XINIT run 4 (register copies $A5 and CRTCNT 13 in every case), XJ = XINIT3 run 1 (those
    varied, plus widths, read-backs and the whole VRAM)."""
    t = open(os.path.join(ROOT, "scratchpad", "XINIT_run4.out")).read()
    t3 = open(os.path.join(ROOT, "scratchpad", "XINIT3_run1.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        cs = X.decode(bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1)))
        for c in cs:
            c.src, c.id, c.rgg, c.crt = "XI", f"XI {c.idx:02}", 0xA5, CRT
        cs3 = X3.decode(bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t3).group(1)))
        for c in cs3:
            c.src, c.id = "XJ", f"XJ {c.idx:02}"
        t4 = open(os.path.join(ROOT, "scratchpad", "XINIT4_run1.out")).read()
        cs4 = X4.decode(bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t4).group(1)))
        for c in cs4:
            c.src, c.id = "XJ4", f"XJ4 {c.idx:02}"
        out[who] = cs + cs3 + cs4
    return out


def xj(c):
    return c.src in ("XJ", "XJ4")


def edge4(c):
    return c.src == "XJ4" and c.width in (0, 80, 255)


def ncols(c):
    return 40 if is_txt(c) else 32


def on_screen(c):
    return 1 <= c.crt <= 24


def key_row(c):
    """The key line as the formula states it: the width's span from the margin (cols - width + 1) / 2, the first
    five labels from margin + k x slot, slot = (width + 1) / 5, each cut to slot - 1 cells (none below 1)."""
    n = ncols(c)
    m, slot = (n - c.width + 1) // 2, (c.width + 1) // 5
    row = [SP] * n
    for k in range(5):
        for j, ch in enumerate(labels(c)[k][:max(0, slot - 1)]):
            row[m + k * slot + j] = ch
    return row


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


def step(c):
    """The sprite pattern number's step: 4 when R1's size bit (16 x 16 sprites, bit 1) ends up set."""
    return 4 if c.rgg & 2 else 1


def keyplace_ok(c):
    """XJ (and XI) with the key line on, CRTCNT on screen: the rows read are the key line where they ARE row CRTCNT,
    spaces elsewhere; the name table's sum fits."""
    n = ncols(c)
    key = key_row(c) if c.key else [SP] * n
    total = 960 if n == 40 else 768
    after13 = [] if n == 40 else [SP] * 8
    ok = (c.row13 == (key if c.crt == 13 else [SP] * n) + after13
          and c.lastrow[:n] == (key if c.crt == 24 else [SP] * n)
          and c.namesum == (SP * (total - n) + sum(key)) & 0xFFFF)
    if xj(c):
        aft = [] if n == 40 else (c.lastrow[32:] if c.crt == 24 else [SP] * 8)
        ok = ok and c.rowc == key + aft
    return ok


def vram_ok(c):
    """XJ: every VRAM byte outside the tables the call writes stays $5A. The whole 16 KB's sum, less the pattern
    table's (the font: R-I-FONT), is the garbage's plus what the name / colour / sprite tables hold -- plus one
    key line drawn OFF the screen's rows when CRTCNT is 0 or above 24."""
    n = ncols(c)
    total = 960 if n == 40 else 768
    written = 2048 + total + (0 if is_txt(c) else 32 + 128)
    expect = g(c) * (16384 - written) + c.namesum + (0 if is_txt(c) else c.colsum + c.atrsum)
    if c.key and not on_screen(c):
        expect += sum(key_row(c)) - g(c) * n
    return (c.vsum - c.patsum - expect) & 0xFFFF == 0


RULES = [
    Rule("R-I-REGS-TXT", TXT, "R1..R7 (their copies RG1SAV..RG7SAV) are computed, never left as found: R1 = (the "
         "copy AND $A7) OR $50 -- bits 7, 5, 2, 1, 0 kept, bits 6 and 4 set, bit 3 cleared ($A5 gives F5, $A7 F7, "
         "$5A 52; each bit alone by XINIT4's walking copies); R2 / R3 / R4 / R5 / R6 from "
         "TXTNAM / TXTCOL / TXTCGP / TXTATR / TXTPAT (moved: 04 48 05 68 07); R7 = (FORCLR·16) OR BAKCLR in 8 bits "
         "($3A, $C5 gives E5, not the sum's 65; the border colour is not used).",
         lambda c: is_txt(c),
         lambda c: c.rg[1:] == [(c.rgg & 0xA7) | 0x50] + regs(c, TABLES[c.tbl][0:5]) + [((c.fg << 4) | c.bg) & 0xFF]),
    Rule("R-I-TAIL-TXT", TXT, "The 64 bytes after the 960 name cells are left as found, at widths 1 to 255 (41, 80, 255 "
         "included) -- not at width 0 with the key line on, which writes them (R-I-KEYEDGE's cells).", lambda c: is_txt(c) and not w0key(c), lambda c: c.tailsum == 64 * g(c)),
    Rule("R-I-ATR-TXT", TXT, "No sprite attribute table is written: moved (TXTATR $3456), the 128 bytes at R5's "
         "base are left as found.", lambda c: is_txt(c) and c.tbl, lambda c: c.atrsum == 128 * g(c)),
    Rule("R-I-REGS-32", T32, "R1 = (the copy AND $A7) OR $40 -- bit 6 set, bits 4 and 3 cleared ($A5 gives E5, $A7 "
         "E7, $5A 42); R2..R6 from T32NAM / T32COL / T32CGP / T32ATR "
         "/ T32PAT (moved: 07 BF 06 3F 01); R7 = BDRCLR as it is ($F9 stays F9).",
         lambda c: not is_txt(c),
         lambda c: c.rg[1:] == [(c.rgg & 0xA7) | 0x40] + regs(c, TABLES[c.tbl][5:10]) + [c.bd]),
    Rule("R-I-COL32", T32, "The colour table's 32 bytes all become (FORCLR·16) OR BAKCLR in 8 bits (their sum read).",
         lambda c: not is_txt(c) and not w0key(c),
         lambda c: c.colsum == 32 * (((c.fg << 4) | c.bg) & 0xFF)
         and (not xj(c) or c.col == [((c.fg << 4) | c.bg) & 0xFF] * 32)),
    Rule("R-I-SPR32", T32, "The sprite attribute table (32 entries at T32ATR) is written: each entry Y = 209 ($D1, "
         "the sprite is off screen), X left as found, the pattern = the sprite's number -- times 4 when R1's size bit "
         "is set (copies $5A / $A7: 16 × 16 sprites) -- the colour = FORCLR as it is ($3A stays 3A). Read byte for byte in entries 0 and 1 (the 8 cells after the name table, default tables) "
         "and as the sum for all 32; the rest of the 1 KB name block is left as found.",
         lambda c: not is_txt(c) and not w0key(c),
         lambda c: (c.atrsum == 32 * (209 + g(c) + c.fg) + step(c) * sum(range(32))
                    and c.tailsum == 128 * g(c) + c.atrsum + (sum(key_row(c)) - 32 * g(c) if c.key and c.crt == 30 else 0)
                    and c.lastrow[32:] == ([g(c)] * 8 if c.tbl else [209, g(c), 0, c.fg, 209, g(c), step(c), c.fg]))),
    Rule("R-I-R0", B, "R0 (RG0SAV) keeps only bit 0 (external video) of the copy: $A5 / $A7 give 01, $5A (M3 and "
         "bits 3, 4, 6 set) gives 00 -- pinned bit by bit by XINIT4's walking copies ($01, $04, $20, $80 and their "
         "complements).", lambda c: True, lambda c: c.rg[0] == c.rgg & 1),
    Rule("R-I-MODE", B, "SCRMOD and OLDSCR become 0 (INITXT) / 1 (INIT32), also from SCREEN 2.",
         lambda c: True, lambda c: (c.scrmod, c.oldscr) == ((0, 0) if is_txt(c) else (1, 1))),
    Rule("R-I-LINLEN", B, "LINLEN becomes LINL40 (INITXT) / LINL32 (INIT32) AS IT IS: 0, 1, 80, 255 included -- no "
         "validation; the other call's cell (77) is not used.", lambda c: True, lambda c: c.linlen == c.width),
    Rule("R-I-HOME", B, "The cursor goes home: CSRX 1, CSRY 1.", lambda c: True, lambda c: (c.csrx, c.csry) == (1, 1)),
    Rule("R-I-CRTCNT", B, "CRTCNT is NOT written, and not clamped: 13, 24, 20, 0 and 30 all stay, key line on or off.",
         lambda c: True, lambda c: c.crtcnt == c.crt),
    Rule("R-I-CNSDFG", B, "CNSDFG becomes 255 when it was non-zero (1, 2, $80, $FF), 0 when it was 0.",
         lambda c: True, lambda c: c.cnsdfg == (255 if c.key else 0)),
    Rule("R-I-LT", B, "LINTTB becomes 24, 23, …, 1 down the rows.", lambda c: True,
         lambda c: c.lt == [24 - r for r in range(24)]),
    Rule("R-I-KEYPLACE", B, "Where the key line goes, as a formula (XINIT3 pins it on widths no other case has: "
         "INITXT 33–35, INIT32 2 / 10 / 20 / 27): on row CRTCNT (13, 20 or 24), within the width's span from the "
         "left margin (columns − width + 1) ÷ 2; label k (k = 0..4, the FIRST five keys) from column margin + k × "
         "slot, slot = (width + 1) ÷ 5, cut to slot − 1 cells (width 2: none). Every other row is spaces. For "
         "widths up to the screen's columns only: one past (INITXT 41) leaves an extra 0 cell (R-I-KEYS' cells).",
         lambda c: c.key and on_screen(c) and 1 <= c.width <= ncols(c), keyplace_ok),
    Rule("R-I-KEYOUT", B, "With CRTCNT 0 or 30 (off the screen's rows) the key line is still drawn, somewhere OUTSIDE "
         "the name table: every row of the name table reads spaces, and the whole-VRAM sum holds exactly one more key "
         "line (INIT32 30: in the 256 bytes after the name table; the address itself is not read).",
         lambda c: c.key and not on_screen(c),
         lambda c: (c.namesum == SP * (960 if is_txt(c) else 768) and c.rowc[:ncols(c)] == [SP] * ncols(c)
                    and c.row13[:ncols(c)] == [SP] * ncols(c) and c.lastrow[:ncols(c)] == [SP] * ncols(c)
                    and (is_txt(c) or c.rowc[32:] == (c.lastrow[32:] if c.crt == 30 else [SP] * 8))
                    and (is_txt(c) or c.row13[32:] == [SP] * 8))),
    Rule("R-I-READBACK", B, "The call changes none of its inputs: LINL40 / LINL32 (the other call's cell keeps its "
         "77), FORCLR / BAKCLR / BDRCLR, the ten screen-table cells, FNKSTR.", lambda c: xj(c),
         lambda c: ((c.linl40, c.linl32) == ((c.width, 77) if is_txt(c) else (77, c.width))
                    and c.colours == [c.fg, c.bg, c.bd] and c.tables == TABLES[c.tbl]
                    and c.fnksum == (FNK_SUM7 if getattr(c, "lab", 0) else FNK_SUM))),
    Rule("R-I-VRAM", B, "Nothing else in VRAM is written: the whole 16 KB less the name, pattern, colour (INIT32) and "
         "sprite attribute (INIT32) tables stays as found -- INITXT writes no colour and no sprite table -- except, with "
         "CRTCNT 0 or 30, the one key line drawn off the screen's rows (R-I-KEYOUT).",
         lambda c: xj(c) and not edge4(c), vram_ok),
    Rule("R-I-NOCOL-TXT", TXT, "INITXT writes no colour table: moved out of every other table (TXTCOL $2000) its 32 "
         "bytes stay $5A; at the default TXTCOL 0 they are the name table's first row (spaces), and TXTATR $1800's "
         "128 bytes stay $5A.", lambda c: xj(c) and is_txt(c) and not edge4(c),
         lambda c: (c.col == ([g(c)] * 32 if c.tbl == 2 else [SP] * 32) and c.colsum == sum(c.col)
                    and c.atrsum == 128 * (g(c) if c.tbl == 2 else SP))),
    Rule("R-I-EDGE4", B, "The key line at the edge widths, with the whole VRAM read (XINIT4): widths 80 and 255 write "
         "only inside the name table (the whole-VRAM sum moves exactly as the name table's: +231, −253); width 0 "
         "writes outside it -- the name table's tail, and for INIT32 the colour and sprite tables -- with 0 / $FF "
         "pairs. Every cell and sum as the reference's.", edge4,
         lambda c: (c.namesum, c.colsum, c.tailsum, c.atrsum, c.vsum, bytes(c.row13).hex(), bytes(c.lastrow).hex(),
                    bytes(c.rowc).hex()) == EDGE4[c.idx] and bytes(c.col).hex() == EDGE4COL[c.idx]),
    Rule("R-I-CLEAR", B, "With the key line off the name table is cleared to spaces (960 / 768 cells): row 13 and "
         "the last row read blank.", lambda c: not c.key,
         lambda c: (c.namesum == SP * (960 if is_txt(c) else 768) and c.lastrow[:cols(c)] == [SP] * cols(c)
                    and c.row13 == [SP] * 40
                    and (not xj(c) or c.rowc == [SP] * cols(c) + ([] if is_txt(c) else
                                                                  (c.lastrow[32:] if c.crt == 24 else [SP] * 8))))),
    Rule("R-I-KEYS", B, "With the key line on, the key line is drawn on row CRTCNT -- row 13 here, NOT the last row "
         "(which stays blank) -- and shows the FIRST five function keys' labels, placed by the width ('key0' at "
         "column 1 for INITXT 40 / 41 and INIT32 32 / 33, 8 / 6 cells apart; elsewhere by the cases' cells); with "
         "CRTCNT 24 it is the last row (XJ 03, XJ 11: R-I-KEYPLACE). Entering from SCREEN 2, with the display off, or with CNSDFG 2 / $80 / $FF gives the same "
         "cells. Every cell and sum as the reference's.",
         lambda c: not xj(c) and c.key and c.width not in (0, 1, 80, 255),
         lambda c: (c.namesum, c.colsum, c.tailsum, c.atrsum, c.row13, c.lastrow) == key_ref(c)),
    Rule("R-I-KEYEDGE", B, "Key line on with width 0, 1, 80 or 255: as the reference leaves it. Width 1 / 80: row 13 "
         "blank (80: labels elsewhere, the name sum 30951); width 255: labels from column 22 (INITXT) / 18 (INIT32) of row 13; width 0: "
         "the name table is NOT cleared to spaces but mostly to 0 with $FF pairs, INIT32 also over its colour and "
         "sprite tables.",
         lambda c: not xj(c) and c.key and c.width in (0, 1, 80, 255),
         lambda c: (c.namesum, c.colsum, c.tailsum, c.atrsum, c.row13, c.lastrow) == key_ref(c)),
    Rule("R-I-FONT", B, "The pattern table holds the font (the VG-8020's sums to 31375).",
         lambda c: True, lambda c: c.patsum == FONT_SUM),
]
