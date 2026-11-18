#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The shared loader and VRAM model for CLRSPR / CHGCLR's EXECUTABLE RULES (docs/spec-method.md §3a):
scratchpad/XCLR_run5.out (rows N and D; probes/bios/spec/xclr.asm documents the presets, the case table and the
128-byte record). xclrspr_rules.py and xchgclr_rules.py take their op's cases from `load(op)`."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

RUN = "XCLR_run5.out"
ASM = os.path.join(HERE, "xclr.asm")
REC = 128
MASK = (0x03, 0xFB, 0x0F, 0xFF, 0x07, 0x7F, 0x07, 0xFF)
VPRE = (0x00, 0x80, 0x06, 0x80, 0x00, 0x36, 0x07, 0xF4)
OUTPUTS = {"XC": ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "sav", "scrmod", "colours", "vdp", "sums", "w1", "w2",
                  "w3"]}
# CLRSPR with RG1SAV's bit 7 clear: the reference writes R#1 := RG1SAV before its VRAM writes, so they go through the
# TMS9918's 4 KB addressing, which the model does not reproduce -- that case's VRAM is not an output (group XC4)
OUTPUTS["XC4"] = [f for f in OUTPUTS["XC"] if f not in ("sums", "w1", "w2", "w3")]


def fill(a):
    """the probe's VRAM fill: ((address low) XOR (address high) XOR $5A) OR address / $400"""
    return (((a & 0xFF) ^ (a >> 8) ^ 0x5A) | (a >> 10)) & 0xFF


def table():
    src = open(ASM).read()
    pat = (r"db\s+\$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..)\n\s+dw\s+\$(....), \$(....)\n"
           r"\s+db\s+\$(..)\n\s+dw\s+\$(....), \$(....), \$(....)")
    return [tuple(int(x, 16) for x in m) for m in re.findall(pat, src[src.index("\ncases:"):])]


def tsets():
    src = open(ASM).read()
    body = src[src.index("tsets:"):src.index("finish:")]
    words = [int(w, 16) for w in re.findall(r"\$([0-9A-F]{4})", body)]
    return [words[20 * k:20 * (k + 1)] for k in range(5)]


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
            for i, (cop, cf, ei, scr, rg1, fo, ba, bd, atr, pat, cs, w1, w2, w3) in enumerate(tab):
                if cop != op:
                    continue
                r = b[1 + REC * i:1 + REC * (i + 1)]
                m = 0xFF if i & 4 else 0x00          # the marker set: bit 2 of the case number
                out[who].append(NS(
                    src="XC4" if cop == 0 and not rg1 & 0x80 else "XC", id=f"XC {row}{i:02}", row=row, op=cop, cf=cf, ei=ei, cscr=scr, crg1=rg1,
                    fo=fo, ba=ba, bd=bd, catr=atr, cpat=pat, t32col=ts[cs][6], cw=(w1, w2, w3), mask=m,
                    a=r[0], f=r[1], bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7],
                    ix=r[8] << 8 | r[9], iy=r[10] << 8 | r[11], iff=r[12], sav=tuple(r[13:21]), scrmod=r[21],
                    colours=tuple(r[22:25]), vdp=tuple(r[25:33]),
                    sums=tuple(r[33 + 2 * k] | r[34 + 2 * k] << 8 for k in range(16)),
                    w1=tuple(r[65:81]), w2=tuple(r[81:97]), w3=tuple(r[97:113])))
    return out


def marker(c, v):
    return v ^ (c.mask << 8 | c.mask)


def vram_after(c, writes):
    """the probe's fill with `writes` ({address: byte}) applied: (16 block sums, the three 16-byte windows)"""
    sums = []
    for k in range(16):
        sums.append(sum(writes.get(a, fill(a)) for a in range(k * 1024, (k + 1) * 1024)) & 0xFFFF)
    wins = tuple(tuple(writes.get((w + i) & 0x3FFF, fill((w + i) & 0x3FFF)) for i in range(16)) for w in c.cw)
    return tuple(sums), wins


def vram_rule(tag, section, text, writes):
    def check(c):
        sums, wins = vram_after(c, writes(c))
        return c.sums == sums and (c.w1, c.w2, c.w3) == wins
    return Rule(f"R-{tag}-VRAM", section, text, lambda c: c.src == "XC", check)


def keep_rule(tag, section, text, check):
    return Rule(f"R-{tag}-KEEP", section, text, lambda c: True, check)
