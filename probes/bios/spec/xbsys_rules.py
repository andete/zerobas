#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bdos/SYSTEM.md's EXECUTABLE RULES (docs/spec-method.md §3a): the BDOS system functions through $F37D, from the
XBSYS1 probe (probes/bios/spec/xbsys1.asm documents the 15 cases and the 15-byte record) on TWO reference rows: run 1
(scratchpad/XBSYS1_run1.out, `--row disk`: the VG-8020 + NMS 1200) and run 2 (XBSYS1_run2.out, `--row cf3300`: the
CF-3300). Each rule holds on both; where the published contract is silent, the WORKING values are those both
references agree on (R-BS-WORK) -- the other reference is the expectation, never zerobas."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bdos/SYSTEM.md"
FN = ["VERSION", "CURDRV", "SELDSK", "LOGIN", "SETDTA", "ALLOC", "GDATE", "SDATE", "GDATE2", "GTIME", "STIME", "GTIME2",
      "DSKRST", "SDATE13", "STIME25"]
RUNS = [("XBSYS1_run1.out", "D"), ("XBSYS1_run2.out", "C")]
OUTPUTS = {"XS": ["a", "f", "b", "c", "d", "e", "h", "l", "iff", "ix", "iy", "dta"]}
_cache = {}


def cases():
    if "d" in _cache:
        return _cache["d"]
    d = {"ref": [], "zb": []}
    for run, row in RUNS:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 15 * len(FN) - len(b)))
            for i, fn in enumerate(FN):
                r = b[15 * i: 15 * (i + 1)]
                d[who].append(NS(src="XS", id=f"XS {row}{i:02}", row=row, num=i, fn=fn,
                                 a=r[0], f=r[1], b=r[2], c=r[3], d=r[4], e=r[5], h=r[6], l=r[7], iff=r[8],
                                 ix=(r[9] << 8) | r[10], iy=(r[11] << 8) | r[12], dta=(r[13] << 8) | r[14]))
    _cache["d"] = d
    return d


def other_ref(c):
    """the same case on the other reference row"""
    return next(o for o in cases()["ref"] if o.num == c.num and o.row != c.row)


def hl(c):
    return (c.h << 8) | c.l


def de(c):
    return (c.d << 8) | c.e


F = lambda *names: (lambda c: c.fn in names)          # noqa: E731
S1 = "1. The system functions through $F37D"
RULES = [
    Rule("R-BS-VERSION", S1, "VERSION ($0C): A $22 and HL $0022 (CP/M 2.2), B 0.", F("VERSION"),
         lambda c: (c.a, hl(c), c.b) == (0x22, 0x0022, 0)),
    Rule("R-BS-DRIVES", S1, "CURDRV ($19): A 0 (drive A). SELDSK ($0E) with E 0: A 2, the number of drives (drive A "
         "and its phantom B). LOGIN ($18): A 3 and HL $0003, the online-drive bitmap.", F("CURDRV", "SELDSK", "LOGIN"),
         lambda c: {"CURDRV": c.a == 0, "SELDSK": c.a == 2, "LOGIN": (c.a, hl(c)) == (3, 3)}[c.fn]),
    Rule("R-BS-DTA", S1, "The DTA cell ($F23D) is $0000 before any SETDTA; SETDTA ($1A) sets it to DE ($A800) and DE "
         "comes back unchanged; DSKRST ($0D) resets it to $0080 with A 0.", lambda c: True,
         lambda c: c.dta == (0 if c.num < 4 else 0xA800 if c.num < 12 else 0x0080)
         and (c.fn != "SETDTA" or de(c) == 0xA800) and (c.fn != "DSKRST" or c.a == 0)),
    Rule("R-BS-ALLOC", S1, "ALLOC ($1B) with E 0 on the empty 720 KB disk: A 2 (sectors per cluster), BC 512 (bytes per "
         "sector), DE 713 (clusters), HL 713 (free clusters), IX and IY pointing into the disk ROM's work area (the "
         "DPB and the FAT buffer: $F197 / $E597 on the VG-8020 + NMS 1200, $F195 / $E595 on the CF-3300).",
         F("ALLOC"), lambda c: (c.a, (c.b << 8) | c.c, de(c), hl(c)) == (2, 512, 713, 713)
         and c.ix >= 0xE000 and c.iy >= 0xE000 and c.ix - c.iy == 0x0C00),
    Rule("R-BS-DATE", S1, "GDATE ($2A) after start-up: 1984-01-01 (HL 1984, D 1, E 1) and A 0, the day of the week "
         "(Sunday). SDATE ($2B) of 2026-11-22 answers A 0, and GDATE then returns it (HL 2026, D 11, E 22, A 0: also "
         "a Sunday). SDATE with month 13 answers A $FF.", F("GDATE", "SDATE", "GDATE2", "SDATE13"),
         lambda c: {"GDATE": (hl(c), c.d, c.e, c.a) == (1984, 1, 1, 0), "SDATE": c.a == 0,
                    "GDATE2": (hl(c), c.d, c.e, c.a) == (2026, 11, 22, 0), "SDATE13": c.a == 0xFF}[c.fn]),
    Rule("R-BS-TIME", S1, "GTIME ($2C): A 0 and HL, DE 0 (no clock on an MSX1). STIME ($2D) of 12:34:56 answers A 0 -- "
         "and GTIME still reads 0. STIME with hour 25 answers A $FF.", F("GTIME", "STIME", "GTIME2", "STIME25"),
         lambda c: {"GTIME": (c.a, hl(c), de(c)) == (0, 0, 0), "STIME": c.a == 0,
                    "GTIME2": (c.a, hl(c), de(c)) == (0, 0, 0), "STIME25": c.a == 0xFF}[c.fn]),
    Rule("R-BS-DI", S1, "Every call leaves interrupts off (entered off).", lambda c: True, lambda c: c.iff == 0),
    Rule("R-BS-WORK", S1, "The registers the published contract leaves open -- F, and the rest of A, BC, DE, HL, IX and "
         "IY -- are the SAME on both references, but for the values that are addresses in the disk ROM's work area "
         "or carry its slot (ALLOC's IX / IY, DSKRST's DE / IX, and IY, which R-BS-ALLOC and R-BS-SLOT state).",
         lambda c: True,
         lambda c: (lambda o: (c.a, c.f, c.b, c.c) == (o.a, o.f, o.b, o.c)
                    and (c.fn in ("DSKRST",) or (c.d, c.e) == (o.d, o.e)) and (c.h, c.l) == (o.h, o.l)
                    and (c.fn in ("ALLOC", "DSKRST") or c.ix == o.ix))(other_ref(c))),
    Rule("R-BS-SLOT", S1, "IY after a call is the inter-slot call's leftover, a value of the interface: $0110 on the "
         "VG-8020 + NMS 1200, $0314 on the CF-3300 (its high byte the slot: 1 / 3); after DSKRST, DE = IX, an address "
         "in the work area.", lambda c: c.fn != "ALLOC",
         lambda c: c.iy == {"D": 0x0110, "C": 0x0314}[c.row] and (c.fn != "DSKRST" or (de(c) == c.ix >= 0xE000))),
]
