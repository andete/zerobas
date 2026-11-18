#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/CHRGTR.md's EXECUTABLE RULES (docs/spec-method.md §3a): CHRGTR ($0010) for every byte value after the
text pointer, in two passes (entry A / F, register markers, the cells' seeds and the CONTXT text all differ) --
scratchpad/XCHRGTR_run4.out (probes/bios/spec/xchrgtr.asm documents the text, the passes and the 20-byte record); and
three calls in a row from a numeric token -- scratchpad/XCHRGTR2_run1.out (probes/bios/spec/xchrgtr2.asm)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/CHRGTR.md"
OUTPUTS = {"XC": ["a", "f", "hl", "kept", "cells"], "XC2": ["calls", "cells"]}
TOKS2 = [0x0B, 0x0C, 0x0D, 0x0E, 0x0F] + list(range(0x11, 0x1E)) + [0x1F]
BUF = 0xE900
# per pass: $F666-$F671 before each call (CONTXT, then one value per cell), and the text at CONTXT
SEEDS = [bytes([0x20, 0xE9]) + bytes(range(0x61, 0x6B)), bytes([0x30, 0xE9]) + bytes(range(0x71, 0x7B))]
CTEXT = {BUF + 0x20: b"\x20\x41\x00", BUF + 0x30: b"\x42\x41\x00"}
SKIP = (0x20, 0x09, 0x0A)
# the numeric-constant tokens: token -> (bytes of text after the token, CONTYP)
NUM = {0x0B: (2, 2), 0x0C: (2, 2), 0x0D: (2, 2), 0x0E: (2, 2), 0x0F: (1, 2), 0x1C: (2, 2), 0x1D: (4, 4),
       0x1F: (8, 8), **{t: (0, 2) for t in range(0x11, 0x1C)}}


def cases():
    t = open(os.path.join(ROOT, "scratchpad", "XCHRGTR_run4.out")).read()
    out = {}
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        if b[0] != 0xA5 or len(b) < 2 + 20 * 512 or b[1 + 20 * 512] != 0xC3:
            sys.exit("FAIL: the XCHRGTR block is not complete (no sentinel)")
        out[who] = [NS(src="XC", id=f"XC {i >> 8}.{i & 0xFF:02X}", c=i & 0xFF, seed=SEEDS[i >> 8], a=b[1 + 20 * i],
                       f=b[2 + 20 * i], hl=(BUF + (b[3 + 20 * i] | b[4 + 20 * i] << 8)) & 0xFFFF, kept=b[5 + 20 * i],
                       cells=bytes(b[6 + 20 * i:18 + 20 * i])) for i in range(512)]
    t = open(os.path.join(ROOT, "scratchpad", "XCHRGTR2_run1.out")).read()
    for who, key in (("ref", "ref"), ("zb", "ours")):
        b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
        if b[0] != 0xA5 or len(b) < 2 + 24 * 38 or b[1 + 24 * 38] != 0xC3:
            sys.exit("FAIL: the XCHRGTR2 block is not complete (no sentinel)")
        for i in range(38):
            r = b[1 + 24 * i:25 + 24 * i]
            out[who].append(NS(src="XC2", id=f"XC2 {i // 19}.{TOKS2[i % 19]:02X}", c=TOKS2[i % 19], seed=SEEDS[0],
                               calls=[(r[4 * k], r[4 * k + 1], r[4 * k + 2] | r[4 * k + 3] << 8) for k in range(3)],
                               cells=bytes(r[12:24])))
    return out


def logical(a):
    """F after a logical instruction on A: S, Z, bits 5 / 3 from A, H / N / C clear, P/V = even parity."""
    return (a & 0x80) | (0x40 if a == 0 else 0) | (a & 0x28) | (0x04 if bin(a).count("1") % 2 == 0 else 0)


def plain(c):
    """F for a plain character c (not end, not skipped, not a token)."""
    if c >= 0x3A:   # a compare with ':' -- bits 5 / 3 from the ':' ($3A), not the result
        r = (c - 0x3A) & 0xFF
        return ((r & 0x80) | (0x40 if r == 0 else 0) | 0x28 | (0x10 if (c & 0xF) < 0xA else 0)
                | (0x04 if (c ^ 0x3A) & (c ^ r) & 0x80 else 0) | 0x02 | (0x01 if c < 0x3A else 0))
    x = c + 1       # a decrement from c + 1, the carry set exactly on a digit
    return ((c & 0x80) | (0x40 if c == 0 else 0) | (c & 0x28) | (0x10 if (x & 0xF) == 0 else 0)
            | (0x04 if x == 0x80 else 0) | 0x02 | (0x01 if 0x30 <= c <= 0x39 else 0))


def const_cells(c, seed):
    n, typ = NUM[c]
    text = bytes(range(0x31, 0x3A))
    val = bytes([c - 0x11, 0]) if n == 0 else (text[:1] + b"\0" if n == 1 else text[:n])
    cells = bytearray(seed)
    cells[0:2] = (BUF + 2 + n).to_bytes(2, "little")
    cells[2], cells[3] = c, typ
    cells[4:4 + len(val)] = val
    return bytes(cells)


def resume(seed):
    """$10: where the text at CONTXT gives its first character -- the byte AT CONTXT, spaces skipped."""
    at = seed[0] | seed[1] << 8
    k = 0
    while CTEXT[at][k] == 0x20:
        k += 1
    return at + k, CTEXT[at][k]


XC = lambda c: c.src == "XC"  # noqa: E731
PLAIN = lambda c: XC(c) and c.c not in SKIP and c.c not in NUM and c.c not in (0x00, 0x10, 0x1E)  # noqa: E731
S1 = "1. CHRGTR ($0010, RST 10h): the next character of a BASIC text"
S2 = "2. The numeric-constant tokens $0B-$1F"

RULES = [
    Rule("R-C-PLAIN", S1, "Any other byte (not 00, not a space / TAB / LF, not $0B-$1F) is returned as it is: HL "
         "one past the entry HL, pointing at it, and A the byte.", PLAIN,
         lambda c: c.hl == BUF + 1 and c.a == c.c),
    Rule("R-C-ZC", S1, "Z is set exactly when the character returned is 00 or ':', and the carry exactly when it is a "
         "digit '0'-'9' -- over every case but the numeric tokens and $1E, entry F $00 and $FF alike.", lambda c: XC(c) and c.c not in NUM and c.c != 0x1E,
         lambda c: ((c.f & 0x40) != 0) == (c.a in (0, 0x3A)) and ((c.f & 0x01) != 0) == (0x30 <= c.a <= 0x39)),
    Rule("R-C-F", S1, "The whole F for such a byte: from ':' up, a compare with ':' (A − $3A, N set, bits 5 / 3 set as in $3A); below it a "
         "decrement's flags from A + 1, N set, with the carry set exactly on a digit -- whatever F was on entry ($00 / $FF).", PLAIN,
         lambda c: c.f == plain(c.c)),
    Rule("R-C-SKIP", S1, "A space, a TAB ($09) and an LF ($0A) are skipped: HL goes on to the next byte (here '1', "
         "so HL + 2, A $31 and that digit's F).", lambda c: XC(c) and c.c in SKIP,
         lambda c: c.hl == BUF + 2 and c.a == 0x31 and c.f == plain(0x31)),
    Rule("R-C-END", S1, "00 (the end of the line) gives A 00, HL + 1 and F $44: Z and P/V, N clear -- a logical "
         "result's flags.", lambda c: XC(c) and c.c == 0,
         lambda c: c.hl == BUF + 1 and c.a == 0 and c.f == logical(0)),
    Rule("R-C-KEPT", S1, "BC, DE, IX and IY are kept -- two sets of values, the second every marker complemented.",
         XC, lambda c: c.kept == 0),
    Rule("R-C-CELLS", S1, "No byte but the numeric-constant tokens writes $F666-$F671 ($10 and $1E write nothing).", lambda c: XC(c) and c.c not in NUM,
         lambda c: c.cells == c.seed),
    Rule("R-C-NUM", S2, "A numeric-constant token ($0B-$0F, $11-$1D, $1F) returns A = the token, F a logical "
         "result's on it (S, Z, bits 5 / 3, P/V even parity; H, N and the carry clear), and HL = $46E6 -- not a "
         "pointer into the text.", lambda c: XC(c) and c.c in NUM,
         lambda c: c.a == c.c and c.f == logical(c.c) and c.hl == 0x46E6),
    Rule("R-C-CONST", S2, "It records the constant: CONTXT ($F666) := the text address after the constant; CONSAV "
         "($F668) := the token; CONTYP ($F669) := 2, or 4 for $1D, 8 for $1F; CONLO ($F66A..) := the value -- two "
         "text bytes for $0B-$0E and $1C, one for $0F (high byte 0), 0-10 for $11-$1B, four for $1D, eight for "
         "$1F. The cells after the value keep their bytes.", lambda c: XC(c) and c.c in NUM,
         lambda c: c.cells == const_cells(c.c, c.seed)),
    Rule("R-C-10", S2, "$10 continues at CONTXT: HL := ($F666), and the character there -- the byte AT CONTXT, not "
         "after it -- is returned as above, spaces skipped (pass 0: a space then 'A', HL = CONTXT + 1, A $41; pass 1: "
         "'B', HL = CONTXT, A $42).", lambda c: XC(c) and c.c == 0x10,
         lambda c: (c.hl, c.a) == resume(c.seed) and c.f == plain(c.a)),
    Rule("R-C-1E", S2, "$1E returns A = CONSAV ($F668), F a logical result's on it, and HL = entry HL + 1, at the token "
         "(CONSAV $61 and $71).",
         lambda c: XC(c) and c.c == 0x1E, lambda c: c.a == c.seed[2] and c.f == logical(c.seed[2]) and c.hl == BUF + 1),
    Rule("R-C-CHAIN", S2, "A caller going on from a numeric token gets the text after the constant: the next CHRGTR "
         "(from HL = $46E6) returns the first byte of the text after the constant, HL pointing at it, and the one after it the following byte, "
         "each with a plain character's F; the cells stay as the token left them. Entry F $00 and $FF alike.",
         lambda c: c.src == "XC2",
         lambda c: (c.calls[0][2] == 0x46E6
                    and c.calls[1] == (0x31 + NUM[c.c][0], plain(0x31 + NUM[c.c][0]), BUF + 2 + NUM[c.c][0])
                    and c.calls[2] == (0x32 + NUM[c.c][0], plain(0x32 + NUM[c.c][0]), BUF + 3 + NUM[c.c][0])
                    and c.cells == const_cells(c.c, c.seed))),
]
