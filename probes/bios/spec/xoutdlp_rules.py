#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""docs/bios/OUTDLP.md's EXECUTABLE RULES (docs/spec-method.md §3a): OUTDLP ($014D) with the printer logger plugged --
scratchpad/XOUTDLP_run2.out (row N) and XOUTDLP_run2d.out (row D); probes/bios/spec/xoutdlp.asm documents the
sequences, the four passes (NTMSXP 0 / $FF / $01 / 0) and the 4-byte record."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/OUTDLP.md"
RUNS = [("XOUTDLP_run2.out", "N"), ("XOUTDLP_run2d.out", "D")]
SEQ = [0x41, 0x42, 0x09, 0x43, 0x0D, 0x0A, 0x09, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x09, 0x78, 0x01, 0x41,
       0x85, 0xFF, 0x20, 0x0D, 0x0A]
SEQ2 = [0x41, 0x01, 0x5F, 0x09, 0x42, 0x01, 0x7E, 0x0D, 0x0A]
PASSES = [(0x00, 0x00, SEQ), (0xFF, 0xFF, SEQ), (0x01, 0x5A, SEQ2), (0x00, 0x00, SEQ2)]   # NTMSXP, entry F, sequence
SPACED = {0x41, 0x5F}   # the graphic codes measured to go out as a space on a printer that is not an MSX one ($7E not)
OUTPUTS = {"XO": ["pos", "a", "f", "moved"], "XP": ["prn"]}


def logical(a):
    return (a & 0x80) | (0x40 if a == 0 else 0) | (a & 0x28) | (0x04 if bin(a).count("1") % 2 == 0 else 0)


def model(ntmsx, ef, seq):
    """per call: (LPTPOS after, A after, F after) and the bytes the printer gets, for one pass"""
    col, out, per, graph = 0, [], [], False
    for b in seq:
        if graph:                                   # the character after $01 on a printer that is not MSX
            graph = False
            s_ = 0x20 if b in SPACED else b
            out.append(s_)
            col += 1
            per.append((col, s_, logical(s_) | 0x10))
        elif b == 0x09:
            n = 8 - col % 8
            out += [0x20] * n
            col += n
            per.append((col, b, ef))
        elif b == 0x01:
            if ntmsx:
                graph = True
                per.append((col, b, 0x42))
            else:
                out.append(b)
                per.append((col, b, logical(b) | 0x10))
        else:
            out.append(b)
            col = 0 if b == 0x0D else (col if b == 0x0A else col + 1)
            per.append((col, b, logical(b) | 0x10))
    return per, out


def cases():
    out = {"ref": [], "zb": []}
    for name, row in RUNS:
        t = open(os.path.join(ROOT, "scratchpad", name)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}[ \t]*:[ \t]*([0-9a-fA-F]+)", t).group(1))
            n = sum(len(q) for _, _, q in PASSES)
            if b[0] != 0xA5 or len(b) < 2 + 4 * n or b[1 + 4 * n] != 0xC3:
                sys.exit(f"FAIL: the {name} block is not complete (no sentinel)")
            prn = bytes.fromhex(re.search(rf"PRN {key}[ \t]*:[ \t]*([0-9a-fA-F]*)", t).group(1))
            k = 0
            for p, (ntm, ef, seq) in enumerate(PASSES):
                per, _ = model(ntm, ef, seq)
                for i, c in enumerate(seq):
                    o = 1 + 4 * k
                    k += 1
                    out[who].append(NS(src="XO", id=f"XO {row}{p}.{i:02}", row=row, p=p, i=i, c=c, ef=ef,
                                       exp=per[i], pos=b[o], a=b[o + 1], f=b[o + 2], moved=b[o + 3]))
            out[who].append(NS(src="XP", id=f"XP {row}", row=row, prn=prn))
    return out


S1 = "1. OUTDLP ($014D): print a character the way BASIC's printer output does"
XO = lambda c: c.src == "XO"  # noqa: E731

RULES = [
    Rule("R-OD-PRN", S1, "The printer receives the bytes as sent (letters, $20, $78, $85, $FF, CR, LF), except: a TAB "
         "becomes spaces up to the next column that is a multiple of 8 (from columns 2, 0, 7 and 8, and right after "
         "a graphic character); and, on a printer that is not an MSX one (NTMSXP $F417 $FF or $01), a graphic "
         "character's $01 is dropped and its code $41 or $5F becomes one space ($7E goes out as it is). On an MSX "
         "printer (NTMSXP 0) $01 and the code go out as they are.", lambda c: c.src == "XP",
         lambda c: c.prn == bytes(sum((model(n, f, q)[1] for n, f, q in PASSES), []))),
    Rule("R-OD-POS", S1, "LPTPOS ($F415) follows the printer's column: +1 per character printed, to the next multiple "
         "of 8 for a TAB, 0 after CR, unchanged by LF and by the $01 of a graphic character -- on any printer, so a "
         "TAB after a graphic character goes to the column the visible characters reach.", XO,
         lambda c: c.pos == c.exp[0]),
    Rule("R-OD-A", S1, "A is kept -- except that a graphic code sent as a space returns A $20 -- and BC, DE, "
         "HL, IX and IY are kept.", XO, lambda c: c.a == c.exp[1] and c.moved == 0),
    Rule("R-OD-F", S1, "F is LPTOUT's on the byte sent (an AND's flags on it: H set, the carry clear); after a TAB "
         "it is F as on entry ($00 / $FF / $5A); after the $01 held back for a printer that is not an MSX one, $42.", XO,
         lambda c: c.f == c.exp[2]),
]
