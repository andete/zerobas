#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The shared loader and VRAM model for READC / SETC / NSETCX's EXECUTABLE RULES (docs/spec-method.md §3a):
scratchpad/XGFX3_run6.out (rows N and D; probes/bios/spec/xgfx3.asm documents the presets, the case table and the
128-byte record). Each page's module takes its op's cases from `load(op)`."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

RUN = "XGFX3_run6.out"
ASM = os.path.join(HERE, "xgfx3.asm")
REC = 128
FIELDS = ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "sums", "w1", "w2", "w3", "cloc", "cmask", "atrbyt", "regs"]
# NSETCX's A, F, BC, DE and HL after the call are working values (the reference's are not a function the probe
# separates); its cases are the group XN, without them
OUTPUTS = {"XP": FIELDS, "XN": [f for f in FIELDS if f not in ("a", "f", "bc", "de", "hl")]}


def fill(a):
    return (((a & 0xFF) ^ (a >> 8) ^ 0x5A) | ((a >> 8) & 0x3C)) & 0xFF


def table():
    src = open(ASM).read()
    pat = (r"db\s+\$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..)\n\s+dw\s+\$(....), \$(....)\n"
           r"\s+db\s+\$(..)\n\s+dw\s+\$(....), \$(....), \$(....)\n\s+db\s+\$(..)")
    return [tuple(int(x, 16) for x in m) for m in re.findall(pat, src[src.index("\ncases:"):])]


def tsets():
    src = open(ASM).read()
    body = src[src.index("tsets:"):src.index("finish:")]
    words = [int(w, 16) for w in re.findall(r"\$([0-9A-F]{4})", body)]
    return [words[20 * k:20 * (k + 1)] for k in range(len(words) // 20)]


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
            for i, (cop, cf, ei, scr, cm, atr, ba, bd, cl, hl, cs, w1, w2, w3, ca) in enumerate(tab):
                if cop != op:
                    continue
                r = b[1 + REC * i:1 + REC * (i + 1)]
                cells = ts[cs]
                d = dict(src="XN" if cop == 2 else "XP", id=f"XP {row}{i:02}", i=i, row=row, op=cop, ca=ca, cf=cf,
                         ei=ei, cscr=scr, ccm=cm, catr=atr, cclo=cl, chl=hl, cset=cs, cw=(w1, w2, w3),
                         grpcol=cells[11], grpcgp=cells[12], mask=0xFF if i & 4 else 0,
                         ix=r[8] << 8 | r[9], iy=r[10] << 8 | r[11], iff=r[12],
                         sums=tuple(r[33 + 2 * k] | r[34 + 2 * k] << 8 for k in range(16)),
                         w1=tuple(r[65:81]), w2=tuple(r[81:97]), w3=tuple(r[97:113]),
                         cloc=r[113] | r[114] << 8, cmask=r[115], atrbyt=r[116], cba=ba, cbd=bd, regs=tuple(r[13:22]) + tuple(r[25:33]))
                if cop != 2:
                    d.update(a=r[0], f=r[1], bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7])
                out[who].append(NS(**d))
    return out


def logical(v):
    f = (v & 0xA8) | (0x40 if v == 0 else 0)
    return f | (0x04 if bin(v).count("1") % 2 == 0 else 0)


def marker(c, v):
    return v ^ (c.mask << 8 | c.mask)


def colour_addr(c, cl):
    """SCREEN 2: the colour byte of the pattern byte at cl -- cl XOR $2000, whatever GRPCOL / GRPCGP hold"""
    return (cl ^ 0x2000) & 0x3FFF


def pixel_byte(c, a, m):
    """SCREEN 2: the writes that set the pixels `m` (a bit mask, 0 for none) of the pattern byte at a to ATRBYT, by the
    first that applies: m = $FF -- pattern $00, colour byte ATRBYT; ATRBYT (whole) = the background nibble -- the
    bits cleared; ATRBYT's low nibble = the foreground nibble -- the bits set; pattern OR m = $FF -- the bits cleared and (colour AND $F0) OR ATRBYT into
    the background nibble; otherwise the bits set and (ATRBYT x 16) AND $F0 into the foreground nibble. Returns the
    writes and the byte the call reports (the colour byte when it is written, else the pattern byte)."""
    ca = colour_addr(c, a)
    p, col = fill(a), fill(ca)
    if m == 0xFF:
        return {a: 0x00, ca: c.catr}, c.catr
    if c.catr == col & 0x0F:
        return {a: p & ~m & 0xFF}, p & ~m & 0xFF
    if c.catr & 0x0F == col >> 4:
        return {a: p | m}, p | m
    if p | m == 0xFF:
        n = (col & 0xF0) | c.catr
        return {a: p & ~m & 0xFF, ca: n}, n
    n = ((c.catr << 4) & 0xF0) | (col & 0x0F)
    return {a: p | m, ca: n}, n


def pattern_flags(v):
    """S, Z and P/V of v; H, N, C and bits 3 / 5 clear"""
    return (v & 0x80) | (0x40 if v == 0 else 0) | (0x04 if bin(v).count("1") % 2 == 0 else 0)


def vram_after(c, writes):
    sums = tuple(sum(writes.get(a, fill(a)) for a in range(k * 1024, (k + 1) * 1024)) & 0xFFFF for k in range(16))
    wins = tuple(tuple(writes.get((w + i) & 0x3FFF, fill((w + i) & 0x3FFF)) for i in range(16)) for w in c.cw)
    return sums, wins


def vram_rule(tag, section, text, writes):
    def check(c):
        sums, wins = vram_after(c, writes(c))
        return c.sums == sums and (c.w1, c.w2, c.w3) == wins
    return Rule(f"R-{tag}-VRAM", section, text, lambda c: True, check)


VPRE = (0x00, 0x80, 0x06, 0x80, 0x00, 0x36, 0x07, 0xF4)     # the probe's VDP preset, as R#0-R#7 hold it


def regs_rule(tag, section):
    return Rule(f"R-{tag}-REGS", section, "RG0SAV-RG7SAV ($A5 preset), SCRMOD and the VDP registers R#0-R#7 are kept: "
                "the call writes no VDP register. (FORCLR / BAKCLR / BDRCLR, recorded too, are not preset by the "
                "probe: not compared.)", lambda c: True,
                lambda c: c.regs == (0xA5,) * 8 + (c.cscr,) + VPRE)


def ei_rule(tag, section):
    return Rule(f"R-{tag}-EI", section, "Interrupts are on after the call, whether they were on or off before it.",
                lambda c: True, lambda c: c.iff == 1)
