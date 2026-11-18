#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bios/WRTVDP.md's EXECUTABLE RULES (docs/spec-method.md §3a): WRTVDP ($0047) -- scratchpad/XVDPREG_run4.out
(rows N and D; probes/bios/spec/xvdpreg.asm documents the presets, the case table and the 32-byte record).
DISSCR.md, ENASCR.md and RDVDP.md read the same run: `load(op)` serves all four (op 0 WRTVDP, 1 DISSCR, 2 ENASCR,
3 RDVDP)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bios/WRTVDP.md"
RUN = "XVDPREG_run4.out"
ASM = os.path.join(HERE, "xvdpreg.asm")
REC = 32
VPRE = (0x00, 0xC0, 0x06, 0x80, 0x00, 0x36, 0x07, 0xF4)     # the VDP registers' preset, by hand
MASK = (0x03, 0xFB, 0x0F, 0xFF, 0x07, 0x7F, 0x07, 0xFF)     # the bits each register holds (the rest read 0)
FIELDS = ["a", "f", "b", "c", "moved", "iff", "sav", "e7", "vdp"]
OUTPUTS = {"XW": FIELDS + ["far"], "XV": FIELDS}   # XW: WRTVDP, with the byte at RG0SAV + C


def parity_even(v):
    return bin(v).count("1") % 2 == 0


def table():
    rows = []
    for line in open(ASM):
        m = re.match(r"\s+db\s+\$(..), \$(..), \$(..), \$(..), \$(..), \$(..)\s+;", line)
        if m:
            rows.append(tuple(int(x, 16) for x in m.groups()))
    return rows


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
            b = bytes.fromhex(h).ljust(9 + REC * len(tab) + 1, b"\0")
            if b[0] != 0xA5 or b[9 + REC * len(tab)] != 0xC3:
                sys.exit(f"FAIL: the {RUN} {rowname} {who} block is not complete (no sentinel)")
            boot = tuple(b[1:9])
            for i, (cop, cc, bb, ef, ei, rg1) in enumerate(tab):
                if cop != op:
                    continue
                r = b[9 + REC * i:9 + REC * (i + 1)]
                d = dict(src="XW" if cop == 0 else "XV", id=f"XV {row}{i:02}", row=row, op=cop, cc=cc, bb=bb, ef=ef,
                         ei=ei, rg1=rg1, boot=boot, f=r[1], b=r[2], c=r[3], moved=r[4], iff=r[5],
                         sav=tuple(r[6:14]), e7=tuple(r[14:22]), vdp=tuple(r[22:30]))
                d["a"] = r[0]
                if cop == 0:
                    d["far"] = r[30]
                out[who].append(NS(**d))
    return out


def presav(c):
    """RG0SAV-RG7SAV and $F3E7-$F3EE as the probe set them before the call"""
    s = [0x30 + k for k in range(8)]
    s[1] = c.rg1
    return s + list(c.boot)


def cases():
    return load(0)


def after_write(c, k, v):
    """the 16 work-area bytes and the 8 registers, with byte k of the work area (k < 16) and register k & 7 := v"""
    s = presav(c)
    if k < 16:
        s[k] = v
    r = list(VPRE)
    r[k & 7] = v & MASK[k & 7]
    return tuple(s[:8]), tuple(s[8:]), tuple(r)


S1 = "1. WRTVDP ($0047): write B to VDP register C"
ALL = lambda c: True  # noqa: E731

RULES = [
    Rule("R-WV-REG", S1, "VDP register C AND 7 := B, as the VDP holds it (its unused bits read 0: R#0 keeps bits 1-0, R#1 "
         "all but bit 2, R#2 bits 3-0, R#4 and R#6 bits 2-0, R#5 bits 6-0); the other seven registers keep their values. "
         "C 0-7, each with B $00, $FF, $5A and $A5; C 8-15 with $5A and $A5; C $10, $28, $80, $FF.", ALL,
         lambda c: c.vdp == after_write(c, c.cc, c.bb)[2]),
    Rule("R-WV-SAV", S1, "The byte at RG0SAV + C ($F3DF + C, for every C) := B: for C 0-7 the register's own shadow "
         "RG0SAV-RG7SAV; for C 8-15 a cell past RG7SAV ($F3E7-$F3EE); for C $10, $28, $80, $FF further on ($F3EF, "
         "$F407, $F45F, $F4DE). Every other byte of $F3DF-$F3EE keeps its value.", ALL,
         lambda c: c.far == c.bb and (c.sav, c.e7) == (after_write(c, c.cc, c.bb)[:2] if c.cc < 16
                                                       else (tuple(presav(c)[:8]), tuple(presav(c)[8:])))),
    Rule("R-WV-ABC", S1, "A = B on return, B = 0, and C is kept.", ALL,
         lambda c: c.a == c.bb and c.b == 0 and c.c == c.cc),
    Rule("R-WV-F", S1, "F is $A0 (S and bit 5 set), with P/V set when C OR $80 has an even number of 1 bits ($A4) -- "
         "whatever F was on entry ($00 or $FF).", ALL,
         lambda c: c.f == (0xA4 if parity_even(c.cc | 0x80) else 0xA0)),
    Rule("R-WV-EI", S1, "Interrupts are on after the call, whether they were on or off before it.", ALL,
         lambda c: c.iff == 1),
    Rule("R-WV-KEEP", S1, "DE, HL, IX and IY are kept (two sets of values).", ALL, lambda c: c.moved == 0),
]


if __name__ == "__main__":
    for c in load(int(sys.argv[1]) if len(sys.argv) > 1 else 0)["ref"]:
        print(c)
