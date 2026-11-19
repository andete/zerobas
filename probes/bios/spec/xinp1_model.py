#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The shared loader for the input region's EXECUTABLE RULES (SNSMAT, KILBUF, CHGCAP, GTSTCK, GTTRIG, BREAKX, ISCNTC,
CKCNTC, GTPAD, GTPDL; docs/spec-method.md §3a): scratchpad/XINP1_run2.out (rows N and D; probes/bios/spec/xinp1.asm
documents the presets, the key matrix per case, the case table and the 48-byte record)."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

RUN = "XINP1_run2.out"
ASM = os.path.join(HERE, "xinp1.asm")
REC = 48
FIELDS = ["a", "f", "bc", "de", "hl", "ix", "iy", "iff", "aa", "r14", "r15", "putpnt", "getpnt", "intflg", "capst",
          "trgflg", "newkey", "oldkey"]
# GTSTCK, GTTRIG, SNSMAT, GTPAD, GTPDL leave F (and some of BC, DE, HL) holding working values: groups without them
OUTPUTS = {"XI": FIELDS, "XIF": [f for f in FIELDS if f != "f"],
           "XIW": [f for f in FIELDS if f not in ("f", "bc", "de", "hl")], "XIA": [f for f in FIELDS if f != "a"],
           "XIP": [f for f in FIELDS if f not in ("f", "bc", "de", "hl", "r15")]}
KEYBUF = 0xFBF0
PUT0, GET0 = KEYBUF + 5, KEYBUF + 2


def table():
    src = open(ASM).read()
    pat = (r"db\s+\$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..), \$(..)\n"
           r"\s+dw\s+\$(....), \$(....), \$(....)")
    return [tuple(int(x, 16) for x in m) for m in re.findall(pat, src[src.index("\ncases:"):])]


def load(op, group="XI"):
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
            for i, (cop, ca, cf, ei, r1, m1, r2, m2, it, pc, bc, de, hl) in enumerate(tab):
                if cop != op:
                    continue
                r = b[1 + REC * i:1 + REC * (i + 1)]
                keys = [0] * 11
                for rr, mm in ((r1, m1), (r2, m2)):
                    if rr < 11:
                        keys[rr] |= mm
                out[who].append(NS(
                    src=group, id=f"XI {row}{i:02}", cpc=pc, i=i, row=row, op=cop, ca=ca, cf=cf, ei=ei, keys=tuple(keys),
                    cint=it, cbc=bc, cde=de, chl=hl, mask=0xFF if i & 4 else 0,
                    a=r[0], f=r[1], bc=r[2] << 8 | r[3], de=r[4] << 8 | r[5], hl=r[6] << 8 | r[7],
                    ix=r[8] << 8 | r[9], iy=r[10] << 8 | r[11], iff=r[12], aa=r[13], r14=r[14], r15=r[15],
                    putpnt=r[16] | r[17] << 8, getpnt=r[18] | r[19] << 8, intflg=r[20], capst=r[21], trgflg=r[22],
                    newkey=tuple(r[23:34]), oldkey=tuple(r[34:45])))
    return out


def matrix(c, row):
    """the byte the PPI reads for a key row: 0 = pressed"""
    return 0xFF ^ c.keys[row] if row < 11 else 0xFF


def ixiy(c):
    m = c.mask << 8 | c.mask
    return (c.ix, c.iy) == (0x4321 ^ m, 0x8765 ^ m)


def quiet(c, put=PUT0, get=GET0, oldkey=None, r15=0xCF):
    """the key-scan cells (the key buffer pointers, NEWKEY, OLDKEY, TRGFLG) and PSG R15 as preset, or as given: the
    probe runs with the VDP's frame interrupt off, so no timer interrupt scans the keys behind the call"""
    ok = (c.newkey == (0xFF,) * 11 and c.oldkey == (oldkey or (0xFF,) * 11) and c.trgflg == 0xF1
          and (c.putpnt, c.getpnt) == (put, get) and (r15 is None or c.r15 == r15))
    return ok


def r15_port(c):
    """PSG R15 after a joystick-port call: bit 6 (the port select) := 0 for an odd port number, 1 for an even one
    (A 0, the keyboard, keeps it); the other bits kept ($CF preset)"""
    if c.ca == 0:
        return 0xCF
    return 0x8F if c.ca & 1 else 0xCF


def cells(c):
    """INTFLG, CAPST and R14 as preset / read: kept"""
    return (c.intflg, c.capst, c.r14) == (c.cint, 0, 0xBF)


def keep_rule(tag, section, text, check):
    return Rule(f"R-{tag}-KEEP", section, text, lambda c: True, check)
