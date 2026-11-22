#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bdos/RECORDS.md's EXECUTABLE RULES (docs/spec-method.md §3a): the BDOS's record functions through $F37D, from
the XBREC1 probe (probes/bios/spec/xbrec1.asm documents the 16 cases and the 52-byte record; the DTA is filled with $40 +
the case number before each case, so a record carries its writer's mark) on two reference rows: run 1
(scratchpad/XBREC1_run1.out, the VG-8020 + NMS 1200) and run 2 (XBREC1_run2.out, the CF-3300)."""
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

PAGE = "docs/bdos/RECORDS.md"
FN = ["SETDTA", "FMAKE", "WRSEQ0", "WRSEQ1", "FCLOSE1", "FOPEN", "RDSEQ0", "RDSEQ1", "RDSEQEOF", "SETRND", "RDRND0",
      "WRRND5", "RDRND5", "RDRND3", "FCLOSE2", "FSIZE"]
RUNS = [("XBREC1_run1.out", "D"), ("XBREC1_run2.out", "C")]
OUTPUTS = {"XR": ["a", "f", "fcb", "dta"], "XR0": ["a", "f", "dta"]}
R = list(b"R       TXT")
# the never-written record 3: its bytes are what the sector buffer held -- the two references read different bytes
UNSTABLE = {f"XR {row}13": (["dta"], "the never-written record 3's bytes: XBREC1 run 1 (the VG-8020 + NMS 1200) and run 2 "
                            "(the CF-3300) read different stale bytes for the same case -- undefined content")
            for row in "DC"}
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
                c = NS(src="XR0" if i == 0 else "XR", id=f"XR {row}{i:02}", row=row, num=i, fn=fn, a=r[0], f=r[1],
                       dta=list(r[39:52]))
                if i:
                    c.fcb = list(r[2:39])
                d[who].append(c)
    _cache["d"] = d
    return d


def other_ref(c):
    return next(o for o in cases()["ref"] if o.num == c.num and o.row != c.row)


def mark(n):
    """the DTA's first 13 bytes as case n filled them: $40 + n"""
    return [0x40 + n] * 13


W = dict(idx=0, c1=2, c2=2)                          # the file's one cluster, 2
F = lambda *names: (lambda c: c.fn in names)          # noqa: E731
S1 = "1. The record functions through $F37D"
RULES = [
    Rule("R-BR-WSEQ", S1, "WRSEQ ($15) writes the DTA's 128 bytes at the current record (+32) and advances it: after "
         "FMAKE, record 0 (size 128, CR 1), then record 1 (size 256, CR 2); it clears bit 6 of +24 and sets +26 / +28 "
         "to the file's first cluster (2). A 0; the DTA is left. FCLOSE answers A 0 and leaves the FCB.",
         F("FMAKE", "WRSEQ0", "WRSEQ1", "FCLOSE1"),
         lambda c: c.a == 0 and c.dta == mark(c.num) and c.fcb == {
             "FMAKE": fcb(R), "WRSEQ0": fcb(R, size=128, b24=0, cr=1, **W), "WRSEQ1": fcb(R, size=256, b24=0, cr=2, **W),
             "FCLOSE1": fcb(R, size=256, b24=0, cr=2, **W)}[c.fn]),
    Rule("R-BR-RSEQ", S1, "After FOPEN (+15 2 records, CR 0), RDSEQ ($14) reads record 0 into the DTA -- the bytes WRSEQ "
         "wrote, case 2's mark -- then record 1 (case 3's), advancing CR; past the end it answers A 1, leaves the DTA "
         "and CR (2).", F("FOPEN", "RDSEQ0", "RDSEQ1", "RDSEQEOF"),
         lambda c: c.a == {"RDSEQEOF": 1}.get(c.fn, 0)
         and c.dta == {"RDSEQ0": mark(2), "RDSEQ1": mark(3)}.get(c.fn, mark(c.num))
         and c.fcb == fcb(R, rc=2, size=256, cr={"FOPEN": 0, "RDSEQ0": 1}.get(c.fn, 2), **W)),
    Rule("R-BR-SETRND", S1, "SETRND ($24) with CR 2 (after the EOF read) sets the random record +33 .. +35 to 1 and "
         "answers A $12; the DTA is left.", F("SETRND"),
         lambda c: c.a == 0x12 and c.dta == mark(c.num) and c.fcb == fcb(R, rc=2, size=256, cr=2, rr=1, **W)),
    Rule("R-BR-RND", S1, "RDRND ($21) reads the record the random record names into the DTA and sets CR to it (RR 0: "
         "case 2's bytes, CR 0); WRRND ($22) writes the DTA there (RR 5: the file becomes 768 bytes, +24's bit 6 "
         "cleared, CR 5), and RDRND 5 reads it back (case 11's bytes). RDRND of the never-written record 3 answers A 0 "
         "and sets CR 3 (its bytes: undefined, UNSTABLE below). FCLOSE answers A 0 and leaves the FCB.",
         F("RDRND0", "WRRND5", "RDRND5", "RDRND3", "FCLOSE2"),
         lambda c: c.a == 0 and {"RDRND0": c.dta == mark(2), "WRRND5": c.dta == mark(11), "RDRND5": c.dta == mark(11),
                                 "RDRND3": True, "FCLOSE2": c.dta == mark(14)}[c.fn]
         and c.fcb == {"RDRND0": fcb(R, rc=2, size=256, cr=0, **W),
                       "WRRND5": fcb(R, rc=2, size=768, b24=0, cr=5, rr=5, **W)}.get(
             c.fn, fcb(R, rc=2, size=768, b24=0, cr=5 if c.fn == "RDRND5" else 3, rr=5 if c.fn == "RDRND5" else 3, **W))),
    Rule("R-BR-SIZE", S1, "FSIZE of the file then answers 6 records (+33 .. +35), records 0 .. 5.", F("FSIZE"),
         lambda c: c.a == 0 and c.dta == mark(15) and c.fcb == fcb(R, b24=0, date=0, rr=6)),
    Rule("R-BR-WORK", S1, "A and F are the same on both references in every case (F $44 on most; FCLOSE $42 after the "
         "sequential writes, $93 after the random ones; RDSEQ's EOF $44; SETRND $00; SETDTA A $08, F 0).",
         lambda c: True, lambda c: (lambda o: (c.a, c.f) == (o.a, o.f))(other_ref(c))
         and (c.fn != "SETDTA" or c.dta == mark(0))),
]
