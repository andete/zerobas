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
FN2 = ["SETDTA2", "FMAKE2", "W0", "W1", "SETRNDW", "FCLOSEW", "FOPEN2", "SETRND0", "RDSEQ0B", "SETRND1", "WRRND5B",
       "RDSEQCR3", "RDRND6", "RDRND20", "WRRND1", "RDRND1", "FCLOSER", "FOPEN6", "FSIZEPF"]
RUNS2 = [("XBREC2_run1.out", "D"), ("XBREC2_run2.out", "C")]
FN3 = ["SETDTA3", "FMAKE3", "SETRNDE", "W30", "W31", "WRRND53", "SETRND6", "RDSEQ10", "FCLOSE3", "FOPEN3", "FSIZEK"]
RUNS3 = [("XBREC3_run1.out", "D"), ("XBREC3_run2.out", "C")]
OUTPUTS = {"XR": ["a", "f", "fcb", "dta"], "XR0": ["a", "f", "dta"], "XR2": ["a", "f", "fcb", "dta"],
           "XR20": ["a", "f", "dta"], "XR3": ["a", "f", "fcb", "dta"], "XR30": ["a", "f", "dta"]}
R = list(b"R       TXT")
# the never-written record 3: its bytes are what the sector buffer held -- the two references read different bytes
UNSTABLE = {f"XR {row}13": (["dta"], "the never-written record 3's bytes: XBREC1 run 1 (the VG-8020 + NMS 1200) and run 2 "
                            "(the CF-3300) read different stale bytes for the same case -- undefined content")
            for row in "DC"}
UNSTABLE.update({f"XR2 {row}11": (["dta"], "RDSEQ of the never-written record 3: XBREC2 run 1 and run 2 read different "
                                  "stale bytes -- undefined content") for row in "DC"})
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
    for run, row in RUNS2:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 52 * len(FN2) - len(b)))
            for i, fn in enumerate(FN2):
                r = b[52 * i: 52 * (i + 1)]
                c = NS(src="XR20" if i == 0 else "XR2", id=f"XR2 {row}{i:02}", row=row, num=100 + i, fn=fn, a=r[0],
                       f=r[1], dta=list(r[39:52]))
                if i:
                    c.fcb = list(r[2:39])
                d[who].append(c)
    for run, row in RUNS3:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 52 * len(FN3) - len(b)))
            for i, fn in enumerate(FN3):
                r = b[52 * i: 52 * (i + 1)]
                c = NS(src="XR30" if i == 0 else "XR3", id=f"XR3 {row}{i:02}", row=row, num=200 + i, fn=fn, a=r[0],
                       f=r[1], dta=list(r[39:52]))
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


W = dict(idx=0, c1=2, c2=2)


def mark2(n):
    """XBREC2's DTA fill as case n left it: byte i = $40 + n + i (its first 13)"""
    return [(0x40 + n + i) & 0xFF for i in range(13)]                          # the file's one cluster, 2
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
    Rule("R-BR-SETRND2", S1, "SETRND sets the random record to 1 (+33 1, +34 / +35 0) whatever the position: after "
         "two writes (CR 2), after FOPEN (CR 0) and after a good read (CR 1) -- not CR, not the last record; +36 is left. "
         "A $12.", F("SETRNDW", "SETRND0", "SETRND1"),
         lambda c: c.a == 0x12 and c.dta == mark2(c.num - 100) and c.fcb == {
             "SETRNDW": fcb(R, size=256, b24=0, cr=2, rr=1, **W), "SETRND0": fcb(R, rc=2, size=256, cr=0, rr=1, **W),
             "SETRND1": fcb(R, rc=2, size=256, cr=1, rr=1, **W)}[c.fn]),
    Rule("R-BR-SEQ2", S1, "Round 2's sequential side: WRSEQ writes the DTA's bytes in ORDER (the read-back of record 0 is "
         "case 2's $42, $43, ... -- byte i at offset i); RDSEQ ends at the file's SIZE, not at +15: at CR 3 after WRRND "
         "made the file 768 bytes (+15 still 2) it reads (A 0, the never-written record's bytes: UNSTABLE) and CR "
         "becomes 4. FOPEN of the 6-record file sets +15 6.", F("FMAKE2", "W0", "W1", "FCLOSEW", "FOPEN2", "RDSEQ0B",
                                                                "RDSEQCR3", "FOPEN6"),
         lambda c: c.a == 0 and (c.fn == "RDSEQCR3" or c.dta == {"RDSEQ0B": mark2(2)}.get(c.fn, mark2(c.num - 100)))
         and c.fcb == {"FMAKE2": fcb(R), "W0": fcb(R, size=128, b24=0, cr=1, **W), "W1": fcb(R, size=256, b24=0, cr=2,
                                                                                            **W),
                       "FCLOSEW": fcb(R, size=256, b24=0, cr=2, rr=1, **W), "FOPEN2": fcb(R, rc=2, size=256, **W),
                       "RDSEQ0B": fcb(R, rc=2, size=256, cr=1, rr=1, **W),
                       "RDSEQCR3": fcb(R, rc=2, size=768, b24=0, cr=4, rr=5, **W),
                       "FOPEN6": fcb(R, rc=6, size=768, **W)}[c.fn]),
    Rule("R-BR-RND2", S1, "RDRND past the end (RR 6 and 20 on the 6-record file) answers A 1, sets CR to RR and leaves "
         "the DTA. WRRND inside the file (RR 1) overwrites that record -- the size stays 768 -- and RDRND 1 reads the "
         "new bytes back in order. WRRND 5 grows the file to 768 as in round 1. FCLOSE answers A 0.",
         F("WRRND5B", "RDRND6", "RDRND20", "WRRND1", "RDRND1", "FCLOSER"),
         lambda c: c.a == {"RDRND6": 1, "RDRND20": 1}.get(c.fn, 0)
         and c.dta == {"RDRND1": mark2(14)}.get(c.fn, mark2(c.num - 100))
         and c.fcb == fcb(R, rc=2, size=768, b24=0, cr={"WRRND5B": 5, "RDRND6": 6, "RDRND20": 20}.get(c.fn, 1),
                          rr={"WRRND5B": 5, "RDRND6": 6, "RDRND20": 20}.get(c.fn, 1), **W)),
    Rule("R-BR-SIZE2", S1, "FSIZE over $FF at +34 .. +36 writes 6 to +33 .. +35 and leaves +36; SETDTA answers A $08.",
         lambda c: c.fn in ("FSIZEPF", "SETDTA2"),
         lambda c: (c.a, c.dta) == ((0x08, mark2(0)) if c.fn == "SETDTA2" else (0, mark2(18)))
         and (c.fn == "SETDTA2" or c.fcb == fcb(R, b24=0, date=0, rr=6, r36=0xFF))),
    Rule("R-BR-SETRND3", S1, "Round 3: SETRND sets RR to 1 on an EMPTY file and on a 6-record one too -- not the last "
         "record (5), not the size's high byte (3); it writes +34 / +35 0 and LEAVES +36 (poked $FF before). WRSEQ "
         "leaves RR (1 after it); RDSEQ at CR 10, past the end, answers A 1 and leaves CR 10; FSIZE on the FCB as FOPEN "
         "left it writes only +33 .. +35 (6), leaving +12 .. +32. SETDTA A $08.", lambda c: c.src in ("XR3", "XR30"),
         lambda c: c.a == {"SETRNDE": 0x12, "SETRND6": 0x12, "RDSEQ10": 1, "SETDTA3": 0x08}.get(c.fn, 0)
         and c.dta == mark2(c.num - 200) and (c.fn == "SETDTA3" or c.fcb == {
             "FMAKE3": fcb(R), "SETRNDE": fcb(R, rr=1, r36=0xFF),
             "W30": fcb(R, size=128, b24=0, cr=1, rr=1, r36=0xFF, **W),
             "W31": fcb(R, size=256, b24=0, cr=2, rr=1, r36=0xFF, **W),
             "WRRND53": fcb(R, size=768, b24=0, cr=5, rr=5, **W),
             "SETRND6": fcb(R, size=768, b24=0, cr=5, rr=1, r36=0xFF, **W),
             "RDSEQ10": fcb(R, size=768, b24=0, cr=10, rr=1, r36=0xFF, **W),
             "FCLOSE3": fcb(R, size=768, b24=0, cr=10, rr=1, r36=0xFF, **W),
             "FOPEN3": fcb(R, rc=6, size=768, **W), "FSIZEK": fcb(R, rc=6, size=768, rr=6, **W)}[c.fn])),
    Rule("R-BR-WORK", S1, "A and F are the same on both references in every case (F $44 on most; FCLOSE $42 or $93 -- "
         "what decides it is not separated; SETRND $00, $44 or $04; SETDTA A $08, F 0).",
         lambda c: True, lambda c: (lambda o: (c.a, c.f) == (o.a, o.f))(other_ref(c))
         and (c.fn != "SETDTA" or c.dta == mark(0))),
]
