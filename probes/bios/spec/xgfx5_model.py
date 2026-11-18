#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The loader and drawing model for GRPPRT's EXECUTABLE RULES (docs/spec-method.md §3a): scratchpad/XGFX5_run3.out
(rows N and D; probes/bios/spec/xgfx5.asm documents the presets, the probe's RAM font, the case table and the 128-byte
record)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

RUN = "XGFX5_run3.out"
ASM = os.path.join(HERE, "xgfx5.asm")
REC = 128
FIELDS = ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "regs", "sums", "w1", "w2", "w3", "cloc", "cmask", "atrbyt",
          "grpac", "forclr", "logopr"]
OUTPUTS = {"XT": FIELDS}
TSETS = {0: (0x0000, 0x0000), 1: (0x2000, 0x1000), 6: (0x0800, 0x0000)}     # cell sets: GRPCGP, MLTCGP
VPRE = (0x00, 0x80, 0x06, 0x80, 0x00, 0x36, 0x07, 0xF4)


def fill(a):
    return (((a & 0xFF) ^ (a >> 8) ^ 0x5A) | ((a >> 8) & 0x3C)) & 0xFF


def glyph(ch, j):
    """the probe's RAM font: character ch's line j"""
    return ((ch * 7) & 0xFF) ^ ((j * 0x33) & 0xFF) ^ 0x96


def table():
    src = open(ASM).read()
    pat = (r"db\s+\$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..)\n\s+dw\s+\$(....), \$(....)\n"
           r"\s+db\s+\$(..)\n\s+dw\s+\$(....), \$(....), \$(....)\n\s+db\s+\$(..)")
    return [tuple(int(x, 16) for x in m) for m in re.findall(pat, src[src.index("\ncases:"):])]


def load():
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
            for i, (op, cf, ei, scr, fo, lo, at, _, x, y, cs, w1, w2, w3, ch) in enumerate(tab):
                r = b[1 + REC * i:1 + REC * (i + 1)]
                out[who].append(NS(
                    src="XT", id=f"XT {row}{i:02}", i=i, row=row, cf=cf, ei=ei, cscr=scr, cfor=fo, clog=lo, catr=at,
                    cx=x, cy=y, cset=cs, cw=(w1, w2, w3), ch=ch, mask=0xFF if i & 4 else 0,
                    a=r[0], f=r[1], bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7],
                    ix=r[8] << 8 | r[9], iy=r[10] << 8 | r[11], iff=r[12], regs=tuple(r[13:22]) + tuple(r[25:33]),
                    sums=tuple(r[33 + 2 * k] | r[34 + 2 * k] << 8 for k in range(16)),
                    w1=tuple(r[65:81]), w2=tuple(r[81:97]), w3=tuple(r[97:113]),
                    cloc=r[113] | r[114] << 8, cmask=r[115], atrbyt=r[116],
                    grpac=(r[117] | r[118] << 8, r[119] | r[120] << 8), forclr=r[121], logopr=r[122]))
    return out


def marker(c, v):
    return v ^ (c.mask << 8 | c.mask)


def drawn(c):
    return c.ch >= 0x20 and c.cx <= 255 and c.cy <= 191


def pixel_byte(v, a, m, atr):
    """SCREEN 2, one pattern byte at a with the glyph bits m: nothing when m = 0; ATRBYT (whole) = the background
    nibble of the colour byte (a XOR $2000) -- the bits cleared; ATRBYT's low nibble = the foreground nibble -- the
    bits set; otherwise the bits set and (ATRBYT x 16) AND $F0 into the foreground nibble"""
    if m == 0:
        return
    ca = a ^ 0x2000
    p, col = v.get(a, fill(a)), v.get(ca, fill(ca))
    if atr == col & 0x0F:
        v[a] = p & ~m & 0xFF
    elif atr & 0x0F == col >> 4:
        v[a] = p | m
    else:
        v[a] = p | m
        v[ca] = ((atr << 4) & 0xF0) | (col & 0x0F)


def draw(c):
    """(VRAM writes, CLOC, CMASK) of a drawn character"""
    g, mlt = TSETS[c.cset]
    v, fo, x, y = {}, c.cfor, c.cx, c.cy
    if c.cscr == 2:
        cl, s = (g + (y & 0xF8) * 32 + (x & 0xF8) + (y & 7)) & 0xFFFF, x & 7
        for j in range(8):
            gl = glyph(c.ch, j)
            pixel_byte(v, cl & 0x3FFF, gl >> s, fo)
            if s and (x & 0xF8) < 248:
                pixel_byte(v, (cl + 8) & 0x3FFF, (gl << (8 - s)) & 0xFF, fo)
            if cl & 7 == 7 and cl >= ((g + 0x1700) & 0xFFFF):
                break
            cl = (cl + (0xF9 if cl & 7 == 7 else 1)) & 0xFFFF
        return v, cl, 0x80 >> s
    bx, by = x >> 2, y >> 2
    cl = (mlt + ((by >> 3) & 7) * 256 + ((bx >> 1) & 31) * 8 + (by & 7)) & 0xFFFF
    for j in range(8):
        gl = glyph(c.ch, j)
        for k in range(8):
            xx = bx + k
            if xx > 63 or not gl & (0x80 >> k):
                continue
            a = (cl + ((xx >> 1) - (bx >> 1)) * 8) & 0x3FFF
            old = v.get(a, fill(a))
            v[a] = (old & 0x0F) | ((fo << 4) & 0xF0) if xx % 2 == 0 else (old & 0xF0) | fo
        if cl & 7 == 7 and (cl >> 8) >= 5:
            break
        cl = (cl + (0xF9 if cl & 7 == 7 else 1)) & 0xFFFF
    return v, cl, 0xF0 if bx % 2 == 0 else 0x0F


def vram_after(c, writes):
    sums = tuple(sum(writes.get(a, fill(a)) for a in range(k * 1024, (k + 1) * 1024)) & 0xFFFF for k in range(16))
    wins = tuple(tuple(writes.get((w + i) & 0x3FFF, fill((w + i) & 0x3FFF)) for i in range(16)) for w in c.cw)
    return sums, wins
