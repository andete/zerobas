#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The shared loader for PNTINI / SCANR / SCANL's EXECUTABLE RULES (docs/spec-method.md §3a): scratchpad/XGFX6_run1.out
(rows N and D; probes/bios/spec/xgfx6.asm documents the presets, the case table and the 128-byte record). Each page's
module takes its op's cases from `load(op)`."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

RUN = "XGFX6_run1.out"
ASM = os.path.join(HERE, "xgfx6.asm")
REC = 128
FIELDS = ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "regs", "sums", "w1", "w2", "gwork", "cloc", "cmask",
          "atrbyt", "bdratr"]
OUTPUTS = {"XQ": FIELDS}
VPRE = (0x00, 0x80, 0x06, 0x80, 0x00, 0x36, 0x07, 0xF4)
GW = tuple(((i * 0x1D) & 0xFF) ^ 0xA5 for i in range(41))    # the preset of $F92D-$F955


def fill(a):
    return (((a & 0xFF) ^ (a >> 8) ^ 0x5A) | ((a >> 8) & 0x3C)) & 0xFF


def table():
    src = open(ASM).read()
    pat = (r"db\s+\$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..)\n\s+dw\s+\$(....), \$(....)\n"
           r"\s+db\s+\$(..)\n\s+dw\s+\$(....), \$(....), \$(....)\n\s+db\s+\$(..)")
    return [tuple(int(x, 16) for x in m) for m in re.findall(pat, src[src.index("\ncases:"):])]


def load(op):
    tab = table()
    out = {"ref": [], "zb": []}
    text = open(os.path.join(ROOT, "scratchpad", RUN)).read()
    secs = re.findall(r"===== \S+ (nodisk|disk): .*?CAP ref : (\w+)\n  CAP ours: (\w+)", text, re.S)
    if [s[0] for s in secs] != ["nodisk", "disk"]:
        sys.exit(f"FAIL: {RUN} does not hold the nodisk and disk sections")
    for rowname, hr, hz in secs:
        row = "N" if rowname == "nodisk" else "D"
        for who, h in (("ref", hr), ("zb", hz)):
            b = bytes.fromhex(h).ljust(1 + REC * len(tab) + 1, b"\0")
            if b[0] != 0xA5 or b[1 + REC * len(tab)] != 0xC3:
                sys.exit(f"FAIL: the {RUN} {rowname} {who} block is not complete (no sentinel)")
            for i, (cop, cf, ei, scr, cm, at, bd, cb, cl, de, cs, w1, w2, w3, ca) in enumerate(tab):
                if cop != op:
                    continue
                r = b[1 + REC * i:1 + REC * (i + 1)]
                out[who].append(NS(
                    src="XQ", id=f"XQ {row}{i:02}", i=i, row=row, op=cop, cf=cf, ei=ei, cscr=scr, ccm=cm, catr=at,
                    cbdr=bd, cb=cb, cclo=cl, cde=de, cset=cs, cw=(w1, w2), ca=ca, mask=0xFF if i & 4 else 0,
                    a=r[0], f=r[1], bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7],
                    ix=r[8] << 8 | r[9], iy=r[10] << 8 | r[11], iff=r[12], regs=tuple(r[13:22]) + tuple(r[25:33]),
                    sums=tuple(r[33 + 2 * k] | r[34 + 2 * k] << 8 for k in range(16)),
                    w1=tuple(r[65:81]), w2=tuple(r[81:97]),
                    gwork=tuple(r[118:125]) + tuple(r[97:113]) + tuple(r[125:128]),
                    cloc=r[113] | r[114] << 8, cmask=r[115], atrbyt=r[116], bdratr=r[117]))
    return out


def gwork_kept():
    """the recorded work-area bytes ($F92D-$F933, $F942-$F951, $F952-$F954) as preset"""
    return GW[0:7] + GW[0x15:0x25] + GW[0x25:0x28]


def marker(c, v):
    return v ^ (c.mask << 8 | c.mask)


def vram_after(c, writes):
    sums = tuple(sum(writes.get(a, fill(a)) for a in range(k * 1024, (k + 1) * 1024)) & 0xFFFF for k in range(16))
    wins = tuple(tuple(writes.get((w + i) & 0x3FFF, fill((w + i) & 0x3FFF)) for i in range(16)) for w in c.cw)
    return sums, wins
