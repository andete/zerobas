#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The shared loader and model for INIGRP / INIMLT / CHGMOD's EXECUTABLE RULES (docs/spec-method.md §3a):
scratchpad/XINIG_run2.out (rows N and D; probes/bios/spec/xinig.asm documents the presets, the case table and the
128-byte record). xinigrp_rules.py, xinimlt_rules.py and xchgmod_rules.py take their op's cases from `load(op)`;
the direct INITXT / INIT32 cases (ops 3, 4) are only CHGMOD's partners, reached through `partner()`."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

RUN = "XINIG_run2.out"
ASM = os.path.join(HERE, "xinig.asm")
REC = 128
MASK = (0x03, 0xFB, 0x0F, 0xFF, 0x07, 0x7F, 0x07, 0xFF)
FIELDS = ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "sav", "scrmod", "colours", "vdp", "sums", "w1", "w2", "w3",
          "oldscr", "patbas", "atrbas", "grpac"]
OUTPUTS = {"XG": FIELDS}
PAIRS = {12: 0, 13: 6, 14: 20, 15: 21, 16: 24, 17: 25, 31: 24, 32: 24, 33: 25, 34: 25, 35: 18}     # CHGMOD case -> the same set-up, called directly


def fill(a):
    """the probe's VRAM fill: ((address low) XOR (address high) XOR $5A) OR (address high AND $3C)"""
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


def _all():
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
            for i, (cop, cf, ei, scr, rg1, fo, ba, bd, atr, pat, cs, w1, w2, w3, ca) in enumerate(tab):
                r = b[1 + REC * i:1 + REC * (i + 1)]
                m = 0xFF if i & 4 else 0x00
                out[who].append(NS(
                    src="XG", id=f"XG {row}{i:02}", i=i, row=row, who=who, op=cop, ca=ca, cf=cf, ei=ei, cscr=scr, crg1=rg1,
                    fo=fo, ba=ba, bd=bd, catr=atr, cpat=pat, cells=ts[cs], cw=(w1, w2, w3), mask=m,
                    a=r[0], f=r[1], bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7],
                    ix=r[8] << 8 | r[9], iy=r[10] << 8 | r[11], iff=r[12], sav=tuple(r[13:21]), scrmod=r[21],
                    colours=tuple(r[22:25]), vdp=tuple(r[25:33]),
                    sums=tuple(r[33 + 2 * k] | r[34 + 2 * k] << 8 for k in range(16)),
                    w1=tuple(r[65:81]), w2=tuple(r[81:97]), w3=tuple(r[97:113]), oldscr=r[113],
                    patbas=r[114] | r[115] << 8, atrbas=r[116] | r[117] << 8,
                    grpac=(r[118] | r[119] << 8, r[120] | r[121] << 8)))
    return out


ALL = _all()


def load(op):
    return {k: [c for c in v if c.op == op] for k, v in ALL.items()}


def partner(c, who):
    j = PAIRS[c.i]
    return next(x for x in ALL[who] if x.row == c.row and x.i == j)


def marker(c, v):
    return v ^ (c.mask << 8 | c.mask)


def kept_ixiy(c):
    return (c.ix, c.iy) == (marker(c, 0x4321), marker(c, 0x8765))


def vram_after(c, writes):
    sums = tuple(sum(writes.get(a, fill(a)) for a in range(k * 1024, (k + 1) * 1024)) & 0xFFFF for k in range(16))
    wins = tuple(tuple(writes.get((w + i) & 0x3FFF, fill((w + i) & 0x3FFF)) for i in range(16)) for w in c.cw)
    return sums, wins


def sprite_writes(c, w, atr):
    big = c.crg1 & 2
    for k in range(32):
        a = atr + 4 * k
        w[a & 0x3FFF] = 0xD1
        w[(a + 2) & 0x3FFF] = (4 * k if big else k) & 0xFF
        w[(a + 3) & 0x3FFF] = c.fo


def screen_rules(tag, section, mode, writes, r0, r1, shadows, regs_text, de, hl, scrmod):
    """INIGRP / INIMLT's shared rule shapes; `mode` 2 (GRP cells, $F3C7..) or 3 (MLT cells, $F3D1..)"""
    k = 10 if mode == 2 else 15
    cellname = "GRP" if mode == 2 else "MLT"

    def sav(c):
        return (r0(0xA5), r1(c.crg1)) + shadows(c.cells[k:k + 5]) + (c.bd,)

    def vram(c):
        sums, wins = vram_after(c, writes(c))
        return c.sums == sums and (c.w1, c.w2, c.w3) == wins
    ALLc = lambda c: True  # noqa: E731
    return [
        Rule(f"R-{tag}-VRAM", section, writes.__doc__, ALLc, vram),
        Rule(f"R-{tag}-VDP", section, f"The VDP is set up as {'SETGRP' if mode == 2 else 'SETMLT'} sets it from the "
             f"{cellname} cells (RG0SAV-RG6SAV and R#0-R#6 as on that page), with RG1SAV's bit 6 set besides -- the "
             "display on (RG1SAV $80 gives $C0, $A0 $E0) -- and R#7 / RG7SAV := BDRCLR. The VDP registers hold those "
             "values as the VDP keeps them.", ALLc,
             lambda c: c.sav == sav(c) and c.vdp == tuple(v & MASK[n] for n, v in enumerate(sav(c)))),
        Rule(f"R-{tag}-CELLS", section, f"SCRMOD := {scrmod}; PATBAS ($F926) := {cellname}PAT and ATRBAS ($F928) := "
             f"{cellname}ATR. OLDSCR, GRPACX / GRPACY and FORCLR / BAKCLR / BDRCLR are not changed.", ALLc,
             lambda c: (c.scrmod == scrmod and c.patbas == c.cells[k + 4] and c.atrbas == c.cells[k + 3]
                        and c.oldscr == 0x66 and c.grpac == (0x1234, 0x5678) and c.colours == (c.fo, c.ba, c.bd))),
        Rule(f"R-{tag}-REGS", section, regs_text, ALLc,
             lambda c: (c.a == sav(c)[1] and c.f == 0xA4 and c.bc == 0x0001 and c.de == de and c.hl == hl
                        and kept_ixiy(c))),
        Rule(f"R-{tag}-EI", section, "Interrupts are on after the call, whether they were on or off before it.", ALLc,
             lambda c: c.iff == 1),
    ]
