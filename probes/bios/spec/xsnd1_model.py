#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The shared loader for WRTPSG / RDPSG / CHGSND / LFTQ / PUTQ / GETVCP / GETVC2's EXECUTABLE RULES
(and GICINI / STRTMS / BEEP's) (docs/spec-method.md §3a): scratchpad/XSND1_run4.out and XSND1B_run1.out (rows N and D;
probes/bios/spec/xsnd1.asm and xsnd1b.asm document the presets, the case tables and the 80-byte record; xsnd1b's cases
are numbered from 107 and read SET with its own bits). Each page's module takes its op's cases from `load(op)`."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

SOURCES = ((os.path.join(HERE, "xsnd1.asm"), "XSND1_run4.out", 0), (os.path.join(HERE, "xsnd1b.asm"), "XSND1B_run1.out", 107))
REC = 80
FIELDS = ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "psg", "aa", "quetab", "cells", "win"]
OUTPUTS = {"XS": FIELDS}
PSGPRE = (0xA1, 0x02, 0xB3, 0x04, 0xC5, 0x06, 0x17, 0xB8, 0x09, 0x0A, 0x0B, 0x5C, 0x1D, 0x0E)
VCBA = 0xFB41


def table(asm):
    src = open(asm).read()
    pat = r"db\s+\$(..), \$(..), \$(..), \$(..), \$(..)\n\s+dw\s+\$(....), \$(....), \$(....), \$(....)"
    return [tuple(int(x, 16) for x in m) for m in re.findall(pat, src[src.index("\ncases:"):])]


def qsets(asm):
    """the probe's `qsets`: per set, QUETAB + QUEBAK (28 bytes) and QUEUEN, VOICEN, MUSICF, PLYCNT"""
    src = open(asm).read()
    body = src[src.index("\nqsets:"):src.index("\nfinish:")]
    vals = []
    for kind, args in re.findall(r"\b(db|dw)\s+([^\n;]+)", body):
        for v in re.findall(r"\$([0-9A-F]+)", args):
            n = int(v, 16)
            vals += [n] if kind == "db" else [n & 0xFF, n >> 8]
    return [tuple(vals[32 * k:32 * (k + 1)]) for k in range(len(vals) // 32)]


def fill(a):
    """the probe's preset of the queue / voice buffers: (address low) XOR $A5"""
    return (a & 0xFF) ^ 0xA5


def load(op):
    out = {"ref": [], "zb": []}
    for asm, run, base in SOURCES:
        load_one(op, asm, run, base, out)
    return out


def load_one(op, asm, RUN, base, out):
    tab, qs = table(asm), qsets(asm)
    second = base > 0
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
            for i, (cop, ca, cf, ei, st, bc, de, hl, win) in enumerate(tab, base):
                if cop != op:
                    continue
                r = b[1 + REC * (i - base):1 + REC * (i - base + 1)]
                q = qs[(st & (0x1E if second else 0x0E)) >> 1]
                out[who].append(NS(
                    src="XS", id=f"XS {row}{i:02}", i=i, row=row, op=cop, ca=ca, cf=cf, ei=ei, cset=st, cbc=bc, cde=de,
                    chl=hl, cwin=win, q=q, mask=0xFF if (i - base) & 4 else 0, pcbase=0x2F if second and st & 0x80 else 0x50,
                    a=r[0], f=r[1], bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7],
                    ix=r[8] << 8 | r[9], iy=r[10] << 8 | r[11], iff=r[12], psg=tuple(r[13:29]), aa=r[29],
                    quetab=tuple(r[30:58]), cells=tuple(r[58:62]), win=tuple(r[62:78])))


def aa_in(c):
    return c.pcbase | (0x80 if c.cset & 1 else 0)


def aa_ok(c):
    """port C as preset -- its high nibble only when interrupts were on (the timer interrupt sets the keyboard row)"""
    msk = 0xF0 if c.ei else 0xFF
    return c.aa & msk == aa_in(c) & msk


def marker(c, v):
    return v ^ (c.mask << 8 | c.mask)


def ixiy(c):
    return (c.ix, c.iy) == (marker(c, 0x4321), marker(c, 0x8765))


def win_kept(c, writes=None):
    w = writes or {}
    return c.win == tuple(w.get(c.cwin + k, fill(c.cwin + k)) for k in range(16))


def logical(v):
    return (v & 0xA8) | (0x40 if v == 0 else 0) | (0x04 if bin(v).count("1") % 2 == 0 else 0)


def keep_rule(tag, section, text, check):
    return Rule(f"R-{tag}-KEEP", section, text, lambda c: True, check)
