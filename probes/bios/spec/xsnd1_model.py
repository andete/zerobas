#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The shared loader for WRTPSG / RDPSG / CHGSND / LFTQ / PUTQ / GETVCP / GETVC2's EXECUTABLE RULES
(docs/spec-method.md §3a): scratchpad/XSND1_run3.out (rows N and D; probes/bios/spec/xsnd1.asm documents the presets,
the case table and the 80-byte record). Each page's module takes its op's cases from `load(op)`."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

RUN = "XSND1_run3.out"
ASM = os.path.join(HERE, "xsnd1.asm")
REC = 80
FIELDS = ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "psg", "aa", "quetab", "cells", "win"]
OUTPUTS = {"XS": FIELDS}
PSGPRE = (0xA1, 0x02, 0xB3, 0x04, 0xC5, 0x06, 0x17, 0xB8, 0x09, 0x0A, 0x0B, 0x5C, 0x1D, 0x0E)
VCBA = 0xFB41


def table():
    src = open(ASM).read()
    pat = r"db\s+\$(..), \$(..), \$(..), \$(..), \$(..)\n\s+dw\s+\$(....), \$(....), \$(....), \$(....)"
    return [tuple(int(x, 16) for x in m) for m in re.findall(pat, src[src.index("\ncases:"):])]


def qsets():
    """the probe's `qsets`: per set, QUETAB + QUEBAK (28 bytes) and QUEUEN, VOICEN, MUSICF, PLYCNT"""
    src = open(ASM).read()
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
    tab, qs = table(), qsets()
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
            for i, (cop, ca, cf, ei, st, bc, de, hl, win) in enumerate(tab):
                if cop != op:
                    continue
                r = b[1 + REC * i:1 + REC * (i + 1)]
                q = qs[(st & 0x0E) >> 1]
                out[who].append(NS(
                    src="XS", id=f"XS {row}{i:02}", i=i, row=row, op=cop, ca=ca, cf=cf, ei=ei, cset=st, cbc=bc, cde=de,
                    chl=hl, cwin=win, q=q, mask=0xFF if i & 4 else 0,
                    a=r[0], f=r[1], bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7],
                    ix=r[8] << 8 | r[9], iy=r[10] << 8 | r[11], iff=r[12], psg=tuple(r[13:29]), aa=r[29],
                    quetab=tuple(r[30:58]), cells=tuple(r[58:62]), win=tuple(r[62:78])))
    return out


def aa_in(c):
    return 0x50 | (0x80 if c.cset & 1 else 0)


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
