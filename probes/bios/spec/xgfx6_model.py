#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The shared loader for PNTINI / SCANR / SCANL's EXECUTABLE RULES (docs/spec-method.md §3a): scratchpad/XGFX6_run9.out
(rows N and D; probes/bios/spec/xgfx6.asm documents the presets, the case table and the 128-byte record). Each page's
module takes its op's cases from `load(op)`."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

RUN = "XGFX6_run9.out"
ASM = os.path.join(HERE, "xgfx6.asm")
REC = 128
FIELDS = ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "regs", "sums", "w1", "w2", "gwork", "cloc", "cmask",
          "atrbyt", "bdratr"]
# SCANR / SCANL leave A, F and BC (SCANL also DE) holding working values: the groups XR / XL, without them
OUTPUTS = {"XQ": FIELDS, "XR": [f for f in FIELDS if f not in ("a", "f", "bc")],
           "XL": [f for f in FIELDS if f not in ("a", "f", "bc", "de")]}
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
                    src=("XQ", "XR", "XL")[cop], id=f"XQ {row}{i:02}", i=i, row=row, op=cop, cf=cf, ei=ei, cscr=scr, ccm=cm, catr=at,
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


def pixel_byte(v, a, m, atr):
    """SCREEN 2, NSETCX's per-byte rule (docs/bios/NSETCX.md): the pattern byte at a gets the bits m in ATRBYT"""
    ca = a ^ 0x2000
    p, col = v.get(a, fill(a)), v.get(ca, fill(ca))
    if m == 0xFF:
        v[a], v[ca] = 0x00, atr
    elif atr == col & 0x0F:
        v[a] = p & ~m & 0xFF
    elif atr & 0x0F == col >> 4:
        v[a] = p | m
    elif p | m == 0xFF:
        v[a], v[ca] = p & ~m & 0xFF, (col & 0xF0) | atr
    else:
        v[a], v[ca] = p | m, ((atr << 4) & 0xF0) | (col & 0x0F)


def addr(c, x, y):
    """the pattern byte of pixel (x, y) -- SCREEN 2 -- or block (x, y) -- SCREEN 3 -- with the default tables; x past
    the right edge goes on into the next character row's cells, as NSETCX does"""
    if c.cscr == 2:
        return ((y & 0xF8) * 32 + (x & 0x1F8) + (y & 7)) & 0x3FFF
    return (((y >> 3) & 7) * 256 + (x >> 1) * 8 + (y & 7)) & 0x3FFF


def colour(c, v, x, y):
    a = addr(c, x, y)
    if c.cscr == 2:
        p, col = v.get(a, fill(a)), v.get(a ^ 0x2000, fill(a ^ 0x2000))
        return col >> 4 if p & (0x80 >> (x & 7)) else col & 0x0F
    b = v.get(a, fill(a))
    return b >> 4 if x % 2 == 0 else b & 0x0F


def start(c):
    """the pixel (block) CLOC / CMASK name on entry"""
    cl, cm = c.cclo, c.ccm
    if c.cscr == 2:
        return (cl & 0xF8) + (0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01).index(cm), ((cl >> 8) & 0x1F) * 8 + (cl & 7)
    return ((cl & 0xF8) >> 3) * 2 + (1 if cm == 0x0F else 0), ((cl >> 8) & 7) * 8 + (cl & 7)


def place(c, x, y):
    """CLOC / CMASK of pixel (block) (x, y)"""
    if c.cscr == 2:
        return addr(c, x, y), 0x80 >> (x & 7)
    return addr(c, x, y), 0xF0 if x % 2 == 0 else 0x0F


def paint(c, v, x, y, n):
    """n pixels (blocks) from (x, y) rightwards in ATRBYT: SCREEN 2 by NSETCX's per-byte rule, SCREEN 3 nibble by
    nibble as SETC writes it"""
    if c.cscr == 2:
        bits = {}
        for k in range(n):
            a = addr(c, x + k, y)
            bits[a] = bits.get(a, 0) | (0x80 >> ((x + k) & 7))
        for a, m in bits.items():
            pixel_byte(v, a, m, c.catr)
        return
    for k in range(n):
        a = addr(c, x + k, y)
        o = v.get(a, fill(a))
        v[a] = (o & 0x0F) | ((c.catr << 4) & 0xF0) if (x + k) % 2 == 0 else (o & 0xF0) | c.catr


def scanr(c):
    """SCANR's model: (VRAM writes, HL, DE, CLOC / CMASK, the run's start CLOC / CMASK or None when the skip ended the
    call)"""
    v, (x, y) = {}, start(c)
    w, de = (256 if c.cscr == 2 else 64), c.cde
    while x < w - 1 and colour(c, v, x, y) == c.cbdr:
        de = (de - 1) & 0xFFFF
        if de == 0:
            return v, 0, 0, place(c, x, y), None
        x += 1
    xs = x
    while x < w and colour(c, v, x, y) != c.cbdr:
        x += 1
    n = x - xs
    if c.cb or c.cscr != 2:
        paint(c, v, xs, y, n)
    return v, n, de, place(c, min(x, w - 1), y), place(c, xs, y)


def last_scanr_run(c):
    """HL of the most recent SCREEN 2 SCANR before case c in the probe's table (SCANL paints that many past its
    count): the model's, from the case table -- the probe runs its cases in table order"""
    k = None
    for i, t in enumerate(table()):
        if i >= c.i:
            break
        cop, cf, ei, scr, cm, at, bd, cb, cl, de, cs, w1, w2, w3, ca = t
        if cop == 1 and scr == 2:
            from types import SimpleNamespace as _NS
            k = scanr(_NS(cscr=scr, ccm=cm, catr=at, cbdr=bd, cb=cb, cclo=cl, cde=de))[1]
    return k
