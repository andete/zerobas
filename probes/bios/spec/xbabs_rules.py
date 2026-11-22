#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bdos/WRABS.md's EXECUTABLE RULES (docs/spec-method.md §3a): WRABS ($30) through $F37D, read back with RDABS
($2F), from the XBABS1 probe (probes/bios/spec/xbabs1.asm documents the 8 cases and the 66-byte record: A, F, the FCB,
the DTA's first 13, HL, the DTA at +383 .. +1024) on two reference rows: run 1 (scratchpad/XBABS1_run1.out, the
VG-8020 + NMS 1200) and run 2 (XBABS1_run2.out, the CF-3300). The DTA's 1040 bytes hold
($40 + the case + (i AND $FF) + (i >> 8) x 16) AND $FF before each case."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bdos/WRABS.md"
FN = ["SETDTA", "WRABS20", "RDABS20", "WRABS21", "RDABS22", "RDABS21", "WRABS1439", "RDABS1439"]
RUNS = [("XBABS1_run1.out", "D"), ("XBABS1_run2.out", "C")]
SPOTS = (383, 384, 476, 511, 512, 639, 640, 767, 768, 776, 1023, 1024)
OUTPUTS = {"XA": ["a", "f", "fcb", "dta", "hl", "spots"]}
UNSTABLE = {f"XA {row}{i:02}": (["fcb"], "the FCB at $A600 is not passed (DE is the sector) and the probe never "
                                "fills it: start-up RAM -- XBABS1 run 1 (VG-8020 + NMS 1200) reads $FF $FF 0 0 "
                                "repeated, run 2 (CF-3300) all $FF") for row in "DC" for i in range(len(FN))}
_cache = {}


def cases():
    if "d" in _cache:
        return _cache["d"]
    d = {"ref": [], "zb": []}
    for run, row in RUNS:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 66 * len(FN) - len(b)))
            for i, fn in enumerate(FN):
                r = b[66 * i: 66 * (i + 1)]
                d[who].append(NS(src="XA", id=f"XA {row}{i:02}", row=row, num=i, fn=fn, a=r[0], f=r[1],
                                 fcb=list(r[2:39]), dta=list(r[39:52]), hl=(r[52] << 8) | r[53],
                                 spots=list(r[54:66])))
    _cache["d"] = d
    return d


def m(n, i):
    """the DTA byte i as case n filled it"""
    return (0x40 + n + (i & 0xFF) + (i >> 8) * 16) & 0xFF


# the bytes a read leaves: (the case whose fill was written, the first byte of it, the length read)
READ = {"RDABS20": (1, 0, 512), "RDABS22": (3, 512, 512), "RDABS21": (3, 0, 1024), "RDABS1439": (6, 0, 512)}


def expect(c):
    if c.fn in READ:
        src, off, n = READ[c.fn]
        at = lambda o: m(src, off + o) if o < n else m(c.num, o)  # noqa: E731
    else:
        at = lambda o: m(c.num, o)  # noqa: E731
    return [at(i) for i in range(13)], [at(o) for o in SPOTS]


def other_ref(c):
    return next(o for o in cases()["ref"] if o.num == c.num and o.row != c.row)


F = lambda *names: (lambda c: c.fn in names)          # noqa: E731
S1 = "1. WRABS through $F37D"
RULES = [
    Rule("R-BA-WRABS", S1, "WRABS ($30) with DE the first sector, H the count and L 0 (drive A) writes H x 512 bytes "
         "from the DTA -- one sector (20), two (21 and 22), the disk's last (1439) -- and answers A 0, HL 0, the DTA "
         "left as it was.", F("WRABS20", "WRABS21", "WRABS1439"),
         lambda c: (c.a, c.hl) == (0, 0) and (c.dta, c.spots) == expect(c)),
    Rule("R-BA-BACK", S1, "Read back with RDABS the sectors hold exactly what WRABS took from the DTA, in order: "
         "sector 20 the first 512 bytes of case 1's DTA, sector 22 bytes 512 .. 1023 of case 3's, both of case 3's "
         "read together, sector 1439 case 6's; nothing past the H x 512 bytes is touched (+512 / +1024 keep "
         "the reading case's fill). A 0, HL 0.", F("RDABS20", "RDABS22", "RDABS21", "RDABS1439"),
         lambda c: (c.a, c.hl) == (0, 0) and (c.dta, c.spots) == expect(c)),
    Rule("R-BA-WORK", S1, "F (and SETDTA's A and HL) are the same on both references in every case; SETDTA leaves "
         "the DTA.", lambda c: True,
         lambda c: (lambda o: (c.a, c.f, c.hl) == (o.a, o.f, o.hl))(other_ref(c))
         and (c.fn != "SETDTA" or (c.dta, c.spots) == expect(c))),
]
