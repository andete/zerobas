#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bdos/FILES.md's EXECUTABLE RULES (docs/spec-method.md §3a): the BDOS's FCB directory functions through $F37D,
from the XBFILE1 probe (probes/bios/spec/xbfile1.asm documents the 11 cases and the 52-byte record: A, F, the FCB's 37
bytes, the DTA's first 13) on two reference rows: run 1 (scratchpad/XBFILE1_run1.out, the VG-8020 + NMS 1200) and run 2
(XBFILE1_run2.out, the CF-3300). Each rule holds on both; F's unpublished bits are what both references agree on."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bdos/FILES.md"
FN = ["SETDTA", "FMAKE", "FCLOSE", "SFIRST", "SNEXT", "FOPEN", "FSIZE", "FREN", "FOPENOLD", "FDEL", "SFIRSTALL"]
RUNS = [("XBFILE1_run1.out", "D"), ("XBFILE1_run2.out", "C")]
# case 0 (SETDTA) runs on the FCB as start-up left it -- not set up, not evidence: its group records no FCB
OUTPUTS = {"XB": ["a", "f", "fcb", "dta"], "XB0": ["a", "f", "dta"]}
TEST, NEW, ALLQ = list(b"TEST    TXT"), list(b"NEW     TXT"), list(b"????????TXT")
_cache = {}


def cases():
    if "d" in _cache:
        return _cache["d"]
    d = {"ref": [], "zb": []}
    for run, row in RUNS:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 52 * len(FN) - len(b)))
            for i, fn in enumerate(FN):
                r = b[52 * i: 52 * (i + 1)]
                c = NS(src="XB0" if i == 0 else "XB", id=f"XB {row}{i:02}", row=row, num=i, fn=fn,
                       a=r[0], f=r[1], dta=list(r[39:52]))
                if i:
                    c.fcb = list(r[2:39])
                d[who].append(c)
    _cache["d"] = d
    return d


def other_ref(c):
    return next(o for o in cases()["ref"] if o.num == c.num and o.row != c.row)


def made(name):
    """the FCB after FMAKE / FOPEN of an empty file: drive 0, the name, extent / record fields 0, size 0, the date word
    of 1984-01-01 ($0821: (year - 1980) x 512 + month x 32 + day) at +20, time 0, $40 at +24, the rest 0"""
    f = [0] + name + [0] * 25
    f[20], f[21], f[24] = 0x21, 0x08, 0x40
    return f


def named(name, new=None):
    """the FCB as the probe set it up: drive 0, the name, (FREN) the new name at +17, the rest 0"""
    f = [0] + name + [0] * 25
    if new:
        f[17:28] = new
    return f


E5 = [0xE5] * 13
F = lambda *names: (lambda c: c.fn in names)          # noqa: E731
S1 = "1. The FCB directory functions through $F37D"
RULES = [
    Rule("R-BF-MAKE", S1, "FMAKE ($16) of TEST.TXT on the empty disk answers A 0 and fills the FCB: +12 .. +19 0 (extent, "
         "record size, file size), the DATE word at +20 ($0821: 1984-01-01, the date after start-up), the time 0, "
         "$40 at +24, the rest 0. FCLOSE ($10) answers A 0 and leaves the FCB; FOPEN ($0F) of the closed file answers "
         "A 0 with the same FCB.", F("FMAKE", "FCLOSE", "FOPEN"),
         lambda c: c.a == 0 and c.fcb == made(TEST) and c.dta == E5),
    Rule("R-BF-SEARCH", S1, "SFIRST ($11) of ????????.TXT answers A 0 and puts the entry in the DTA: drive 1 (A:), the "
         "name, attribute 0; the FCB stays as set up. SNEXT ($12) then answers A $FF (no more) and leaves the DTA. On "
         "the empty disk SFIRST of ????????.??? answers A $FF and leaves the DTA.", F("SFIRST", "SNEXT", "SFIRSTALL"),
         lambda c: c.fcb == named(ALLQ if c.fn != "SFIRSTALL" else list(b"???????????"))
         and (c.a, c.dta) == ((0, [1] + TEST + [0]) if c.fn == "SFIRST" else (0xFF, E5))),
    Rule("R-BF-SIZE", S1, "FSIZE ($23) of the empty TEST.TXT answers A 0 with the random record +33 .. +35 = 0 (the FCB "
         "otherwise as set up).", F("FSIZE"), lambda c: c.a == 0 and c.fcb == named(TEST) and c.dta == E5),
    Rule("R-BF-REN", S1, "FREN ($17) TEST.TXT -> NEW.TXT (the new name at +17) answers A 0 and leaves the FCB; FOPEN of "
         "TEST.TXT then answers A $FF; FDEL ($13) of NEW.TXT answers A 0.", F("FREN", "FOPENOLD", "FDEL"),
         lambda c: {"FREN": c.a == 0 and c.fcb == named(TEST, NEW), "FOPENOLD": c.a == 0xFF and c.fcb == named(TEST),
                    "FDEL": c.a == 0 and c.fcb == named(NEW)}[c.fn] and c.dta == E5),
    Rule("R-BF-CARRY", S1, "The carry is SET exactly when A is $FF (SNEXT with no more, FOPEN of a missing file, SFIRST "
         "on an empty disk) and clear on A 0.", lambda c: c.src == "XB", lambda c: (c.f & 1) == (c.a == 0xFF)),
    Rule("R-BF-WORK", S1, "The rest of F, and SETDTA's A (case 0), are the same on both references (F $44 after FMAKE, "
         "SFIRST, FOPEN, FSIZE, FREN; $10 after FCLOSE; $42 after FDEL; $45 on the A $FF answers; SETDTA A $08, F 0); "
         "SETDTA leaves the DTA alone.", lambda c: True,
         lambda c: (lambda o: (c.a, c.f) == (o.a, o.f))(other_ref(c)) and (c.fn != "SETDTA" or c.dta == E5)),
]
