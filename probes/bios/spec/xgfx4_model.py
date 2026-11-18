#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The loader for SCALXY's EXECUTABLE RULES (docs/spec-method.md §3a):
scratchpad/XGFX4_run2.out (rows N and D; probes/bios/spec/xgfx4.asm documents the presets, the case table and the
28-byte record). Each page's module takes its op's cases from `load(op)`."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

RUN = "XGFX4_run2.out"
ASM = os.path.join(HERE, "xgfx4.asm")
REC = 28
GTB = -1                                    # no case gets the second ASPCT preset
FIELDS = ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "cloc", "cmask", "atrbyt", "aspct", "scrmod", "cgp"]
# MAPXYC in SCREEN 2 with X above 255: the reference's CMASK is not a bit of X (group XGX, without it)
OUTPUTS = {"XG1": FIELDS, "XGX": [f for f in FIELDS if f != "cmask"]}


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
                d = dict(src="XGX" if wide else "XG1", id=f"XS {row}{i:02}", i=i, row=row, op=cop, ca=ca, cf=cf,
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
