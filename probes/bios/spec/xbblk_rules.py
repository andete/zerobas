#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bdos/BLOCKS.md's EXECUTABLE RULES (docs/spec-method.md §3a): the BDOS's block functions through $F37D, from the
XBBLK1 probe (probes/bios/spec/xbblk1.asm documents the 13 cases and the 54-byte record: A, F, the FCB, the DTA's first
13 bytes, HL after the call) on two reference rows: run 1 (scratchpad/XBBLK1_run1.out, the VG-8020 + NMS 1200) and
run 2 (XBBLK1_run2.out, the CF-3300). The DTA's 128 bytes hold $40 + the case number + the offset before each case."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
from spec_rules import Rule  # noqa: E402
from xbfile_rules import fcb  # noqa: E402

PAGE = "docs/bdos/BLOCKS.md"
FN = ["SETDTA", "FMAKE", "WRBLK200", "FCLOSE", "FOPEN", "RDBLK13", "RDBLK190", "RDBLK128", "RDBLKPART", "FSIZERS1",
      "WRZER3", "FSIZERS128", "RDABS0"]
RUNS = [("XBBLK1_run1.out", "D"), ("XBBLK1_run2.out", "C")]
OUTPUTS = {"XK": ["a", "f", "fcb", "dta", "hl"], "XK0": ["a", "f", "dta", "hl"]}
B = list(b"B       TXT")
BOOT = list(open(os.path.join(ROOT, "disk", "empty720.dsk"), "rb").read()[:13])   # our own generated image's sector 0
# bytes 128 .. 199 of the file came from RAM past the probe's 128-byte DTA fill (WRBLK wrote 200 bytes): reads of them
# show each machine's own leftover RAM
UNSTABLE = {f"XK {row}{n:02}": (["dta"], "bytes 128 .. 199 of B.TXT: WRBLK took them from RAM past the probe's 128-byte "
                                "fill, so XBBLK1 run 1 (VG-8020 + NMS 1200) and run 2 (CF-3300) read different bytes")
            for row in "DC" for n in (6, 8)}
_cache = {}


def cases():
    if "d" in _cache:
        return _cache["d"]
    d = {"ref": [], "zb": []}
    for run, row in RUNS:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 54 * len(FN) - len(b)))
            for i, fn in enumerate(FN):
                r = b[54 * i: 54 * (i + 1)]
                c = NS(src="XK0" if i == 0 else "XK", id=f"XK {row}{i:02}", row=row, num=i, fn=fn, a=r[0], f=r[1],
                       dta=list(r[39:52]), hl=(r[52] << 8) | r[53])
                if i:
                    c.fcb = list(r[2:39])
                d[who].append(c)
    _cache["d"] = d
    return d


def other_ref(c):
    return next(o for o in cases()["ref"] if o.num == c.num and o.row != c.row)


def mark(n, off=0):
    return [(0x40 + n + off + i) & 0xFF for i in range(13)]


def rs(f, size):
    """an FCB with the record size word at +14"""
    f = list(f)
    f[14], f[15] = size & 0xFF, size >> 8
    return f


O = dict(c1=2, c2=2)                                  # the file's cluster, 2
F = lambda *names: (lambda c: c.fn in names)          # noqa: E731
S1 = "1. The block functions through $F37D"
RULES = [
    Rule("R-BK-WRBLK", S1, "WRBLK ($26) with record size 1 (+14) and RR 0 writes HL = 200 records of 1 byte from the "
         "DTA: A 0, HL 200 (the records written), the size 200, RR 200, +24's bit 6 cleared, the clusters 2; FCLOSE "
         "answers A 0 and leaves the FCB. FOPEN then shows +15 2 (records of 128, rounded up) and the record size 0.",
         F("FMAKE", "WRBLK200", "FCLOSE", "FOPEN"),
         lambda c: c.a == 0 and c.dta == mark(c.num) and {
             "FMAKE": c.fcb == fcb(B),
             "WRBLK200": c.hl == 200 and c.fcb == rs(fcb(B, size=200, b24=0, rr=200, **O), 1),
             "FCLOSE": c.fcb == rs(fcb(B, size=200, b24=0, rr=200, **O), 1),
             "FOPEN": c.fcb == fcb(B, rc=2, size=200, **O)}[c.fn]),
    Rule("R-BK-RDBLK", S1, "RDBLK ($27) reads HL records of the record size into the DTA from RR, advances RR, and answers "
         "HL = the records read: 13 x 1 byte from 0 (the bytes WRBLK wrote, in order; A 0, RR 13); 20 x 1 from 190 runs "
         "into the end at 200 -- A 1, HL 10, RR 200; with record size 128, record 0 (A 0, HL 1, RR 1), then the "
         "PARTIAL last record 1 (bytes 128 .. 199) counts as read: A 0, HL 1, RR 2.",
         F("RDBLK13", "RDBLK190", "RDBLK128", "RDBLKPART"),
         lambda c: (c.a, c.hl) == {"RDBLK13": (0, 13), "RDBLK190": (1, 10), "RDBLK128": (0, 1),
                                   "RDBLKPART": (0, 1)}[c.fn]
         and (c.fn not in ("RDBLK13", "RDBLK128") or c.dta == mark(2))
         and c.fcb == rs(fcb(B, size=200, rr={"RDBLK13": 13, "RDBLK190": 200, "RDBLK128": 1, "RDBLKPART": 2}[c.fn],
                             **O), 1 if c.fn in ("RDBLK13", "RDBLK190") else 128)),
    Rule("R-BK-FSIZE", S1, "FSIZE ignores the record size: with +14 1 or 128 it answers the records of 128 (2 for 200 "
         "bytes, rounded up) and CLEARS the record size (+14 / +15 0). It reads the DIRECTORY: the 512 bytes WRZER wrote "
         "(no FCLOSE) are not counted yet.", F("FSIZERS1", "FSIZERS128"),
         lambda c: c.a == 0 and c.dta == mark(c.num) and c.fcb == fcb(B, b24=0, date=0, rr=2)),
    Rule("R-BK-WRZER", S1, "WRZER ($28) with RR 3 on that FCB (not opened: FSIZE's) answers A 0 and writes record 3 "
         "(size 512, CR 3, RR 3, clusters 3), the record size then 0; HL 0.", F("WRZER3"),
         lambda c: (c.a, c.hl) == (0, 0) and c.dta == mark(10)
         and c.fcb == fcb(B, size=512, b24=0, c1=3, c2=3, cr=3, rr=3)),
    Rule("R-BK-RDABS", S1, "RDABS ($2F) with DE 0, H 1, L 0 reads sector 0 of drive A into the DTA (the generated "
         "image's boot sector) and answers A 0, HL 0; the FCB is not touched.", F("RDABS0"),
         lambda c: (c.a, c.hl) == (0, 0) and c.dta == BOOT and c.fcb == fcb(B, b24=0, date=0, rr=2)),
    Rule("R-BK-WORK", S1, "A, F and HL are the same on both references in every case (HL is a working value after the "
         "non-block functions: $FF00 after FMAKE / FOPEN, $0300 after FCLOSE, $5808 after SETDTA); SETDTA answers A "
         "$08 and leaves the DTA.", lambda c: True,
         lambda c: (lambda o: (c.a, c.f, c.hl) == (o.a, o.f, o.hl))(other_ref(c))
         and (c.fn != "SETDTA" or c.dta == mark(0))),
]
