#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The shared loader for the sprite table calls' EXECUTABLE RULES (docs/spec-method.md §3a): scratchpad/XSPR_run3.out
(rows N and D; probes/bios/spec/xspr.asm documents the case table and the 20-byte record). xcalpat_rules.py,
xcalatr_rules.py and xgspsiz_rules.py take their op's cases from `load(op)`."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

RUN = "XSPR_run3.out"
ASM = os.path.join(HERE, "xspr.asm")
REC = 20
OUTPUTS = {"XP": ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "rg1", "patbas", "atrbas"]}


def table():
    pat = r"db\s+\$(..), \$(..), \$(..), \$(..), \$(..)\n\s+dw\s+\$(....), \$(....)"
    return [tuple(int(x, 16) for x in m) for m in re.findall(pat, open(ASM).read())]


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
            for i, (cop, ca, cf, ei, rg1, pat, atr) in enumerate(tab):
                if cop != op:
                    continue
                r = b[1 + REC * i:1 + REC * (i + 1)]
                m = 0xFF if i & 1 else 0x00
                out[who].append(NS(src="XP", id=f"XP {row}{i:02}", row=row, op=cop, ca=ca, cf=cf, ei=ei, crg1=rg1,
                                   cpat=pat, catr=atr, mask=m,
                                   a=r[0], f=r[1], bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7],
                                   ix=r[8] << 8 | r[9], iy=r[10] << 8 | r[11], iff=r[12], rg1=r[13],
                                   patbas=r[14] | r[15] << 8, atrbas=r[16] | r[17] << 8))
    return out


def marker(c, v):
    return v ^ (c.mask << 8 | c.mask)


def add_flags(hl, de):
    """H, C, bits 5 / 3 and N as ADD HL,DE leaves them (N clear)"""
    r = (hl + de) & 0xFFFF
    h = 0x10 if (hl & 0xFFF) + (de & 0xFFF) > 0xFFF else 0
    return ((r >> 8) & 0x28) | h | (1 if hl + de > 0xFFFF else 0)


def kept(c, names):
    want = dict(bc=marker(c, 0x1357), de=marker(c, 0x9BDF), hl=marker(c, 0x2468), ix=marker(c, 0x4321),
                iy=marker(c, 0x8765))
    return all(getattr(c, n) == want[n] for n in names)


def cells_rule(tag, section):
    return Rule(f"R-{tag}-CELLS", section, "RG1SAV, PATBAS and ATRBAS are not changed, and the interrupt state is kept "
                "(off, or on).", lambda c: True,
                lambda c: (c.rg1, c.patbas, c.atrbas, c.iff) == (c.crg1, c.cpat, c.catr, c.ei))
