#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The shared loader and model for the VRAM access calls' EXECUTABLE RULES (docs/spec-method.md §3a):
scratchpad/XVRAM_run4.out (rows N and D; probes/bios/spec/xvram.asm documents the presets, the case table and the
48-byte record). Each page's module (xrdvrm_rules.py, xwrtvrm_rules.py, xsetrd_rules.py, xsetwrt_rules.py,
xfilvrm_rules.py, xldirmv_rules.py, xldirvm_rules.py) takes its op's cases from `load(op)`.

The model is the probe's own set-up, then the call's documented effect: VRAM bytes the probe preset hold
pv(a) = low(a) XOR high(a) XOR $5A, RAM windows $E0 + i / $E8 + i, LDIRVM's source (address low) XOR (address high); a VRAM address is
taken AND $3FFF."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

RUN = "XVRAM_run4.out"
ASM = os.path.join(HERE, "xvram.asm")
REC = 48
SRC = 0xE9A0
REGS = ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "w1", "w2", "w3"]
OUTPUTS = {"XM": REGS + ["p0"], "XMR": REGS + ["p0", "p1"], "XMW": REGS}   # XM RDVRM / LDIRMV, XMR SETRD, XMW the rest
WRITERS = (1, 4, 6)                     # WRTVRM, FILVRM, LDIRVM: the probe writes $C9 to port $98 after the call


def pv(a):
    a &= 0x3FFF
    return (a & 0xFF) ^ (a >> 8) ^ 0x5A


def logical(v):
    """F as an OR / XOR leaves it: S, Z, bits 5 / 3 from v, P/V the even parity, H / N / C clear"""
    f = (v & 0xA8) | (0x40 if v == 0 else 0)
    return f | (0x04 if bin(v).count("1") % 2 == 0 else 0)


def table():
    src = open(ASM).read()
    pat = (r"db\s+\$(..), \$(..), \$(..), \$(..)\n\s+dw\s+\$(....), \$(....), \$(....), \$(....), \$(....), \$(....)\n"
           r"\s+db\s+\$(..)")
    return [tuple(int(x, 16) for x in m) for m in re.findall(pat, src)]


def case_ns(i, t):
    cop, ca, cf, ei, hl, de, bc, w1, w2, w3, kind = t
    return NS(i=i, op=cop, ca=ca, cf=cf, ei=ei, chl=hl, cde=de, cbc=bc, cw1=w1, cw2=w2, cw3=w3, kind=kind)


def span_len(c):
    return c.cbc if c.op in (5, 6) and 8 <= c.cbc <= 0x200 else 8


def preset(c, vram, ram):
    """the probe's set-up for case c, into the dicts"""
    wins = [(c.cw1, c.kind & 1, 0xE0), (c.cw2, c.kind & 1, 0xE8), (c.cw3, c.kind & 2, None)]
    for w, isram, base in wins:
        for i in range(8):
            if isram:
                if base is not None:
                    ram[w + i] = base + i
            else:
                vram[(w + i) & 0x3FFF] = pv(w + i)
    span = c.cde if c.op == 6 else c.chl
    for i in range(span_len(c)):
        vram[(span + i) & 0x3FFF] = pv(span + i)
    for i in range(0x110):
        a = SRC + i
        ram[a] = (a & 0xFF) ^ (a >> 8)


def effect(c, vram, ram):
    """the call's documented effect on the dicts; returns the next port read the VDP is left on (None: unknown)"""
    n = c.cbc or 0x10000
    if c.op == 0:
        return vram.get((c.chl + 1) & 0x3FFF)
    if c.op == 1:
        vram[c.chl & 0x3FFF] = c.ca
        vram[(c.chl + 1) & 0x3FFF] = 0xC9
        return None
    if c.op == 2:
        return None
    if c.op == 3:
        vram[c.chl & 0x3FFF] = 0xC7
        vram[(c.chl + 1) & 0x3FFF] = 0xC8
        return None
    if c.op == 4:
        if n >= 0x4000:
            for k in range(0x4000):
                vram[k] = c.ca
        else:
            for i in range(n):
                vram[(c.chl + i) & 0x3FFF] = c.ca
        vram[(c.chl + n) & 0x3FFF] = 0xC9
        return None
    if c.op == 5:
        for i in range(n):
            ram[c.cde + i] = vram[(c.chl + i) & 0x3FFF]
        return vram.get((c.chl + n) & 0x3FFF)
    for i in range(n):
        vram[(c.cde + i) & 0x3FFF] = ram[c.chl + i]
    vram[(c.cde + n) & 0x3FFF] = 0xC9
    return None


def history():
    """the whole run in order: per case (vram, ram) after the call over what is known, and the expected next port
    read -- VRAM bytes an earlier case wrote count as known, bytes never written by the probe or a call do not"""
    vram, ram, out = {}, {}, []
    for i, t in enumerate(table()):
        c = case_ns(i, t)
        preset(c, vram, ram)
        before = dict(vram)
        nxt = effect(c, vram, ram)
        out.append((before, dict(vram), dict(ram), nxt))
    return out


HIST = history()


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
            for i, t in enumerate(tab):
                if t[0] != op:
                    continue
                r = b[1 + REC * i:1 + REC * (i + 1)]
                c = case_ns(i, t)
                d = dict(vars(c), src="XMR" if op == 2 else "XM" if op in (0, 5) else "XMW", id=f"XM {row}{i:02}", row=row,
                         a=r[0], f=r[1], bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7],
                         ix=r[8] << 8 | r[9], iy=r[10] << 8 | r[11], iff=r[12],
                         w1=tuple(r[15:23]), w2=tuple(r[23:31]), w3=tuple(r[31:39]))
                if op in (0, 2, 5):
                    d["p0"] = r[13]
                if op == 2:
                    d["p1"] = r[14]
                out[who].append(NS(**d))
    return out


def model(c):
    _, vram, ram, _ = HIST[c.i]
    return vram, ram


def windows(c):
    vram, ram = model(c)
    get = lambda isram, a: ram[a] if isram else vram[a & 0x3FFF]  # noqa: E731
    return (tuple(get(c.kind & 1, c.cw1 + i) for i in range(8)), tuple(get(c.kind & 1, c.cw2 + i) for i in range(8)),
            tuple(get(c.kind & 2, c.cw3 + i) for i in range(8)))


def next_read(c):
    return HIST[c.i][3]


def before(c, a):
    return HIST[c.i][0].get(a & 0x3FFF)


def mem_rule(tag, section, text):
    return Rule(f"R-{tag}-MEM", section, text, lambda c: True, lambda c: (c.w1, c.w2, c.w3) == windows(c))


def ei_rule(tag, section):
    return Rule(f"R-{tag}-EI", section, "Interrupts are on after the call, whether they were on or off before it.",
                lambda c: True, lambda c: c.iff == 1)


def port_rule(tag, section, text):
    return Rule(f"R-{tag}-PORT", section, text, lambda c: next_read(c) is not None, lambda c: c.p0 == next_read(c))


def landing(c):
    """where the probe's $C9 lands after a writing call"""
    n = c.cbc or 0x10000
    return {1: c.chl + 1, 4: c.chl + n, 6: c.cde + n}[c.op] & 0x3FFF


def land_rule(tag, section, text):
    def wins(c):
        out = [(c.cw1, c.w1), (c.cw2, c.w2)] if c.kind & 1 == 0 else []
        return out + ([(c.cw3, c.w3)] if c.kind & 2 == 0 else [])

    def sel(c):
        a = landing(c)
        return any((a - w) & 0x3FFF < 8 for w, _ in wins(c))

    def chk(c):
        a = landing(c)
        return all(win[(a - w) & 0x3FFF] == 0xC9 for w, win in wins(c) if (a - w) & 0x3FFF < 8)
    return Rule(f"R-{tag}-NEXT", section, text, sel, chk)


def unread(op):
    """the cases whose next port read lands on a VRAM byte neither the probe nor a call had written: not modelled"""
    if op not in (0, 5):                # only RDVRM / LDIRMV record one read
        return {}
    return {c.id: (["p0"], "the next port read lands on a VRAM byte neither the probe nor an earlier call wrote, "
                   "so no rule predicts it (the same on both machines)")
            for c in load(op)["ref"] if next_read(c) is None}


def keep(c, names):
    want = dict(a=c.ca, f=c.cf, bc=c.cbc, de=c.cde, hl=c.chl, ix=0x4321, iy=0x8765)
    return all(getattr(c, n) == want[n] for n in names)
