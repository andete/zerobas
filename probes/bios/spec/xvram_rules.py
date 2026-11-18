#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The shared loader and model for the VRAM access calls' EXECUTABLE RULES (docs/spec-method.md §3a):
scratchpad/XVRAM_run1.out (rows N and D; probes/bios/spec/xvram.asm documents the presets, the case table and the
32-byte record). Each page's module (xrdvrm_rules.py, xwrtvrm_rules.py, xsetrd_rules.py, xsetwrt_rules.py,
xfilvrm_rules.py, xldirmv_rules.py, xldirvm_rules.py) takes its op's cases from `load(op)`.

The model is the probe's own set-up, then the call's documented effect: VRAM bytes the probe preset hold
pv(a) = low(a) XOR high(a) XOR $5A, RAM windows $E0 + i / $E8 + i, LDIRVM's source $80 + i; a VRAM address is
taken AND $3FFF."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

RUN = "XVRAM_run1.out"
ASM = os.path.join(HERE, "xvram.asm")
REC = 32
SRC = 0xE9A0
REGS = ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "w1", "w2"]
OUTPUTS = {"XM": REGS, "XMR": REGS + ["p0", "p1"]}       # XMR: SETRD's cases, with the two port reads


def pv(a):
    a &= 0x3FFF
    return (a & 0xFF) ^ (a >> 8) ^ 0x5A


def logical(v):
    """F as an OR / XOR leaves it: S, Z, bits 5 / 3 from v, P/V the even parity, H / N / C clear"""
    f = (v & 0xA8) | (0x40 if v == 0 else 0)
    return f | (0x04 if bin(v).count("1") % 2 == 0 else 0)


def table():
    src = open(ASM).read()
    pat = (r"db\s+\$(..), \$(..), \$(..), \$(..)\n\s+dw\s+\$(....), \$(....), \$(....), \$(....), \$(....)\n"
           r"\s+db\s+\$(..)")
    return [tuple(int(x, 16) for x in m) for m in re.findall(pat, src)]


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
            for i, (cop, ca, cf, ei, hl, de, bc, w1, w2, wk) in enumerate(tab):
                if cop != op:
                    continue
                r = b[1 + REC * i:1 + REC * (i + 1)]
                d = dict(src="XMR" if op == 2 else "XM", id=f"XM {row}{i:02}", row=row, op=cop, ca=ca, cf=cf, ei=ei,
                         chl=hl, cde=de, cbc=bc, cw1=w1, cw2=w2, wk=wk,
                         a=r[0], f=r[1], bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7],
                         ix=r[8] << 8 | r[9], iy=r[10] << 8 | r[11], iff=r[12],
                         w1=tuple(r[15:23]), w2=tuple(r[23:31]))
                if op == 2:
                    d["p0"], d["p1"] = r[13], r[14]
                out[who].append(NS(**d))
    return out


def model(c):
    """(vram, ram) dicts after the call, over the addresses the probe preset, from the case's inputs alone"""
    vram, ram = {}, {}
    if c.wk == 0:
        for w in (c.cw1, c.cw2):
            for i in range(8):
                vram[(w + i) & 0x3FFF] = pv(w + i)
    else:
        for w, base in ((c.cw1, 0xE0), (c.cw2, 0xE8)):
            for i in range(8):
                ram[w + i] = base + i
    span = c.cde if c.op == 6 else c.chl
    for i in range(8):
        vram[(span + i) & 0x3FFF] = pv(span + i)
    for i in range(8):
        ram[SRC + i] = 0x80 + i
    n = c.cbc or 0x10000
    if c.op == 1:
        vram[c.chl & 0x3FFF] = c.ca
    elif c.op == 3:
        vram[c.chl & 0x3FFF] = 0xC7
        vram[(c.chl + 1) & 0x3FFF] = 0xC8
    elif c.op == 4:
        if n >= 0x4000:
            vram = {k: c.ca for k in vram}
        else:
            for i in range(n):
                vram[(c.chl + i) & 0x3FFF] = c.ca
    elif c.op == 5:
        for i in range(n):
            ram[c.cde + i] = vram[(c.chl + i) & 0x3FFF]
    elif c.op == 6:
        for i in range(n):
            vram[(c.cde + i) & 0x3FFF] = ram[c.chl + i]
    return vram, ram


def windows(c):
    vram, ram = model(c)
    mem = (lambda a: vram[a & 0x3FFF]) if c.wk == 0 else (lambda a: ram[a])
    return tuple(mem(c.cw1 + i) for i in range(8)), tuple(mem(c.cw2 + i) for i in range(8))


def mem_rule(tag, section, text):
    return Rule(f"R-{tag}-MEM", section, text, lambda c: True, lambda c: (c.w1, c.w2) == windows(c))


def ei_rule(tag, section):
    return Rule(f"R-{tag}-EI", section, "Interrupts are on after the call, whether they were on or off before it.",
                lambda c: True, lambda c: c.iff == 1)


def keep(c, names):
    want = dict(a=c.ca, f=c.cf, bc=c.cbc, de=c.cde, hl=c.chl, ix=0x4321, iy=0x8765)
    return all(getattr(c, n) == want[n] for n in names)
