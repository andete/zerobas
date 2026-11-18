#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The shared loader and model for SETTXT / SETT32 / SETGRP / SETMLT's EXECUTABLE RULES (docs/spec-method.md §3a):
scratchpad/XSET_run4.out (rows N and D; probes/bios/spec/xset.asm documents the presets, the four table sets, the
case table and the 112-byte record). Each page's module takes its op's cases from `load(op)` and its rules from
`rules(op, ...)`."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

RUN = "XSET_run4.out"
ASM = os.path.join(HERE, "xset.asm")
REC = 112
MASK = (0x03, 0xFB, 0x0F, 0xFF, 0x07, 0x7F, 0x07, 0xFF)
VPRE = (0x00, 0x80, 0x06, 0x80, 0x00, 0x36, 0x07, 0xF4)
OUTPUTS = {"XS": ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "sav", "scrmod", "vdp", "sums", "cells"]}
# the probe's VRAM fill: ((address low) XOR (address high) XOR $5A) OR address / $400, so each 1 KB block sums apart
FILLSUM = tuple(sum((((a & 0xFF) ^ (a >> 8) ^ 0x5A) | (a >> 10)) & 0xFF for a in range(k * 1024, (k + 1) * 1024)) & 0xFFFF
                for k in range(16))
TXTNAM = 0xF3B3
NAMES = ("TXT", "T32", "GRP", "MLT")


def table():
    pat = r"db\s+\$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..)\s+;"
    src = open(ASM).read()
    return [tuple(int(x, 16) for x in m) for m in re.findall(pat, src[src.index("\ncases:"):])]


def tsets():
    src = open(ASM).read()
    body = src[src.index("tsets:"):src.index("finish:")]
    words = [int(w, 16) for w in re.findall(r"\$([0-9A-F]{4})", body)]
    return [words[20 * k:20 * (k + 1)] for k in range(6)]


def load(op):
    tab, ts = table(), tsets()
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
            for i, (cop, cf, ei, rg0, rg1, t, scr, rg7, rgp) in enumerate(tab):
                if cop != op:
                    continue
                r = b[1 + REC * i:1 + REC * (i + 1)]
                m = 0xFF if i & 1 else 0x00
                out[who].append(NS(
                    src="XS", id=f"XS {row}{i:02}", row=row, op=cop, cf=cf, ei=ei, rg0=rg0, rg1=rg1, ts=t,
                    cscr=scr, crg7=rg7, crgp=rgp, allcells=tuple(ts[t]), cells5=ts[t][5 * cop:5 * cop + 5], mask=m,
                    a=r[0], f=r[1], bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7],
                    ix=r[8] << 8 | r[9], iy=r[10] << 8 | r[11], iff=r[12], sav=tuple(r[13:21]), scrmod=r[21],
                    vdp=tuple(r[22:30]), sums=tuple(r[30 + 2 * k] | r[31 + 2 * k] << 8 for k in range(16)),
                    cells=tuple(r[62 + 2 * k] | r[63 + 2 * k] << 8 for k in range(20))))
    return out


def shadows(c):
    """RG2SAV-RG6SAV from the mode's five cells (NAM COL CGP ATR PAT): each cell shifted right, its low byte"""
    nam, col, cgp, atr, pat = c.cells5
    r3 = (col >> 6) & 0xFF
    r4 = (cgp >> 11) & 0xFF
    if c.op == 2:                       # SCREEN 2: the colour and pattern tables' mask bits set
        r3 |= 0x7F
        r4 |= 0x03
    return ((nam >> 10) & 0xFF, r3, r4, (atr >> 7) & 0xFF, (pat >> 11) & 0xFF)


R0 = (lambda v: v & 1, lambda v: v & 1, lambda v: v | 2, lambda v: v & 1)
R1 = (lambda v: (v & 0xE7) | 0x10, lambda v: v & 0xE7, lambda v: v & 0xE7, lambda v: (v & 0xE7) | 0x08)


def sav_after(c):
    return (R0[c.op](c.rg0), R1[c.op](c.rg1)) + shadows(c) + (c.crg7,)


def marker(c, v):
    return v ^ (c.mask << 8 | c.mask)


def rules(op, tag, section, r0text, r1text, regtext):
    ALL = lambda c: True  # noqa: E731
    mode = NAMES[op]
    end = TXTNAM + 10 * op + 10
    return [
        Rule(f"R-{tag}-SHADOW", section, f"RG2SAV-RG6SAV := {mode}NAM / $400, {mode}COL / $40, {mode}CGP / $800, "
             f"{mode}ATR / $80, {mode}PAT / $800 -- each cell shifted right, its low byte (so a cell's low bits are "
             "dropped and $FFFF gives $3F, $FF, $1F, $FF, $1F)" + (", with RG3SAV OR $7F and RG4SAV OR $03" if op == 2
                                                                 else "") + ". Whatever they held ($A5, or $5A), "
             "RG2SAV-RG6SAV are wholly replaced; RG7SAV is kept ($A5, $00, $FF, $5A). Six sets of cells: the published "
             "defaults, moved, others with low bits set, every cell $FFFF, and two with $4000 / $8000 / $C000 -- bits 14 "
             "and 15 apart, each way round (a plain shift: NAM $4000 gives $10, ATR $C000 $80, PAT $C000 $18).", ALL,
             lambda c: c.sav[2:] == sav_after(c)[2:]),
        Rule(f"R-{tag}-R01", section, f"RG0SAV := {r0text}; RG1SAV := {r1text} (RG0SAV / RG1SAV $00 / $00, $FF / $FF, "
             "$5A / $A5, and apart: $01 / $00, $FE / $FF).", ALL, lambda c: c.sav[:2] == sav_after(c)[:2]),
        Rule(f"R-{tag}-VDP", section, "The VDP registers R#0-R#6 := those values, as the VDP holds them (R#0 bits 1-0, "
             "R#1 all but bit 2, R#2 bits 3-0, R#4 / R#6 bits 2-0, R#5 bits 6-0); R#7 is not written.", ALL,
             lambda c: c.vdp == tuple(v & MASK[k] for k, v in enumerate(sav_after(c)[:7])) + (VPRE[7],)),
        Rule(f"R-{tag}-REGS", section, f"On return {regtext}; IX and IY are kept -- whatever F was on entry ($00, $FF).",
             ALL, lambda c: (c.a == sav_after(c)[6] and c.f == 0 and c.bc == 0x0007
                             and c.de == (0x7F03 if op == 2 else 0) and c.hl == end
                             and (c.ix, c.iy) == (marker(c, 0x4321), marker(c, 0x8765)))),
        Rule(f"R-{tag}-EI", section, "Interrupts are on after the call, whether they were on or off before it.", ALL,
             lambda c: c.iff == 1),
        Rule(f"R-{tag}-KEEP", section, "VRAM is not written (each 1 KB block still has its own sum from the probe's "
             "fill, sixteen different sums), and SCRMOD (entry $77, 0, 1, 2, 3) and the 20 screen-table cells are not "
             "changed.", ALL,
             lambda c: c.sums == FILLSUM and c.scrmod == c.cscr and c.cells == c.allcells),
    ]
