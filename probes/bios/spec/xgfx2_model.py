#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The shared loader and model for RIGHTC / LEFTC / UPC / TUPC / DOWNC / TDOWNC's EXECUTABLE RULES
(docs/spec-method.md §3a): scratchpad/XGFX2_run3.out (rows N and D; probes/bios/spec/xgfx2.asm documents the presets,
the case table and the 28-byte record, as xgfx1.asm's). Each page's module takes its op's cases from `load(op)`."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

RUN = "XGFX2_run3.out"
ASM = os.path.join(HERE, "xgfx2.asm")
REC = 28
GTB = 255                                   # the probe's GTB ($FF): case 255 gets ASPCT1 / ASPCT2 $0100 / $00C0
FIELDS = ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "cloc", "cmask", "atrbyt", "aspct", "scrmod", "cgp"]
OUTPUTS = {"XG1": FIELDS}


def table():
    src = open(ASM).read()
    pat = (r"db\s+\$(..), \$(..), \$(..), \$(..), \$(..)\n\s+dw\s+\$(....), \$(....), \$(....), \$(....)\n\s+db\s+\$(..)\n"
           r"\s+dw\s+\$(....), \$(....)")
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
            for i, (cop, ca, cf, ei, scr, bc, de, hl, clo, cm, gcg, mcg) in enumerate(tab):
                if cop != op:
                    continue
                r = b[1 + REC * i:1 + REC * (i + 1)]
                wide = False
                d = dict(src="XG1", id=f"XM {row}{i:03}", i=i, row=row, op=cop, ca=ca, cf=cf,
                         ei=ei, cscr=scr, cbc=bc, cde=de, chl=hl, cclo=clo, ccm=cm, cgcg=gcg, cmcg=mcg,
                         mask=0xFF if i & 4 else 0,
                         a=r[0], f=r[1], bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7],
                         ix=r[8] << 8 | r[9], iy=r[10] << 8 | r[11], iff=r[12], cloc=r[13] | r[14] << 8,
                         atrbyt=r[16], aspct=(r[17] | r[18] << 8, r[19] | r[20] << 8), scrmod=r[21],
                         cgp=(r[22] | r[23] << 8, r[24] | r[25] << 8))
                if not wide:
                    d["cmask"] = r[15]
                out[who].append(NS(**d))
    return out


def aspct_in(c):
    return (0x0100, 0x00C0) if c.i == GTB else (0x1234, 0x5678)


def kept(c, names):
    want = dict(a=c.ca, f=c.cf, bc=c.cbc, de=c.cde, hl=c.chl, ix=0x4321 ^ (c.mask * 0x101),
                iy=0x8765 ^ (c.mask * 0x101), iff=c.ei, cloc=c.cclo, cmask=c.ccm, atrbyt=0x77, aspct=aspct_in(c),
                scrmod=c.cscr, cgp=(c.cgcg, c.cmcg))
    return all(getattr(c, n) == want[n] for n in names)


def logical(v):
    f = (v & 0xA8) | (0x40 if v == 0 else 0)
    return f | (0x04 if bin(v).count("1") % 2 == 0 else 0)


def keep_rule(tag, section, text, names):
    return Rule(f"R-{tag}-KEEP", section, text, lambda c: True, lambda c: kept(c, names))


def move(c):
    """(CLOC, CMASK, A, F, stopped) after the call, from the case's inputs -- op 0 RIGHTC, 1 LEFTC, 2 UPC, 3 TUPC,
    4 DOWNC, 5 TDOWNC; SCRMOD 2 or 3"""
    cl, cm, mlt = c.cclo, c.ccm, c.cscr != 2
    andf = lambda v: logical(v) | 0x10  # noqa: E731   (an AND's flags)
    if c.op in (0, 1):
        if c.op == 0:
            edge = cm == (0x0F if mlt else 0x01)
            cm = (0xF0 if mlt else 0x80) if edge else (0x0F if mlt else cm >> 1)
            cl = (cl + 8) & 0xFFFF if edge else cl
        else:
            edge = cm == (0xF0 if mlt else 0x80)
            cm = (0x0F if mlt else 0x01) if edge else (0xF0 if mlt else cm << 1)
            cl = (cl - 8) & 0xFFFF if edge else cl
        return cl, cm, cm, andf(cm), False
    if c.op in (2, 3):
        if c.op == 3:
            stop = (cl & 0xFF07) == 0 if mlt else ((cl >> 8) == (c.cgcg >> 8) and cl & 7 == 0)
            if stop:
                return cl, cm, 0, 0x45, True
        a = cl & 7
        cl = (cl - (0xF9 if a == 0 else 1)) & 0xFFFF
        return cl, cm, a, andf(a), False
    if c.op == 5:
        stop = (cl & 7 == 7 and (cl >> 8) >= 5) if mlt else (cl & 7 == 7 and (cl >> 8) == ((c.cgcg >> 8) + 0x17) & 0xFF)
        if stop:
            return cl, cm, 0, 0x45, True
    cl = (cl + (0xF9 if cl & 7 == 7 else 1)) & 0xFFFF
    a = cl & 7
    return cl, cm, a, andf(a), False


def move_rules(tag, section, what, stop_text=None):
    ALL = lambda c: True  # noqa: E731
    rules = [
        Rule(f"R-{tag}-POS", section, what, ALL, lambda c: (c.cloc, c.cmask) == move(c)[:2]),
        Rule(f"R-{tag}-AF", section, "A and F: " + ("on a stop A = 0 and F = $45 (Z, P/V and the carry); otherwise "
             if stop_text else "") + ("A := the new CMASK" if tag in ("RC", "LC") else
             ("A := the old CLOC AND 7" if tag in ("UC", "TU") else "A := the new CLOC AND 7")) +
             ", and F that value's flags as an AND leaves them (H set; S, Z, bits 5 / 3, P/V from A; N and C "
             "clear) -- whatever A and F were on entry.", ALL, lambda c: (c.a, c.f) == move(c)[2:4]),
        keep_rule(tag, section, "BC, DE, HL, IX, IY, the interrupt state and the rest of the work area recorded "
                  "(ATRBYT, ASPCT1 / ASPCT2, SCRMOD, GRPCGP / MLTCGP) are kept.",
                  ["bc", "de", "hl", "ix", "iy", "iff", "atrbyt", "aspct", "scrmod", "cgp"]),
    ]
    if stop_text:
        rules.insert(1, Rule(f"R-{tag}-EDGE", section, stop_text, ALL, lambda c: (c.f & 1) == int(move(c)[4])))
    return rules
