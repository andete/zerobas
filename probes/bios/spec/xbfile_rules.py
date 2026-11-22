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
FN2 = ["SETDTA93", "SETDTAA8", "SDATE25", "FMAKEPF", "WRSEQ", "FCLOSE2", "SDATE26", "FMAKE2PF", "FOPENPF", "FSIZE2",
       "SFIRSTQ", "SNEXT1", "SNEXT2", "FRENEX", "FMAKEEX"]
RUNS2 = [("XBFILE2_run1.out", "D"), ("XBFILE2_run2.out", "C")]
FN3 = ["FMAKE3A", "WRSEQEX", "FCLOSEEX", "FMAKE3B", "WRSEQCR", "FCLOSECR", "FMAKE3C", "WRSEQ85", "FCLOSE85",
       "FOPENEXFF", "FOPENEX1", "FOPEN6", "FSIZE6", "FDELMISS", "FRENMISS", "FSIZEMISS"]
RUNS3 = [("XBFILE3_run1.out", "D"), ("XBFILE3_run2.out", "C")]
# case 0 (SETDTA) runs on the FCB as start-up left it -- not set up, not evidence: its group records no FCB
OUTPUTS = {"XB": ["a", "f", "fcb", "dta"], "XB0": ["a", "f", "dta"], "XB2": ["a", "f", "fcb", "dta"],
           "XB20": ["a", "f", "dta"], "XB3": ["a", "f", "fcb", "dta"]}
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
    for run, row in RUNS2:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 52 * len(FN2) - len(b)))
            for i, fn in enumerate(FN2):
                r = b[52 * i: 52 * (i + 1)]
                c = NS(src="XB20" if i < 3 else "XB2", id=f"XB2 {row}{i:02}", row=row, num=100 + i, fn=fn,
                       a=r[0], f=r[1], dta=list(r[39:52]))
                if i >= 3:
                    c.fcb = list(r[2:39])
                d[who].append(c)
    for run, row in RUNS3:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 52 * len(FN3) - len(b)))
            for i, fn in enumerate(FN3):
                r = b[52 * i: 52 * (i + 1)]
                d[who].append(NS(src="XB3", id=f"XB3 {row}{i:02}", row=row, num=200 + i, fn=fn, a=r[0], f=r[1],
                                 fcb=list(r[2:39]), dta=list(r[39:52])))
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


def fcb(name, ext=0, rc=0, size=0, date=0x0821, b24=0x40, idx=0, c1=0, c2=0, c3=0, cr=0, rr=0, r36=0, new=None):
    """an FCB from its fields: +12 extent, +13 / +14 0, +15 the records in the extent, +16 .. +19 the size, +20 the
    date word, +22 the time 0, +24 the flags byte, +25 the entry index, +26 / +28 / +30 cluster words, +32 the current
    record, +33 .. +35 the random record, +36"""
    f = [0] + name + [ext, 0, 0, rc] + list(size.to_bytes(4, "little")) + [date & 0xFF, date >> 8, 0, 0, b24, idx]
    f += [c1 & 0xFF, c1 >> 8, c2 & 0xFF, c2 >> 8, c3 & 0xFF, c3 >> 8, cr] + list(rr.to_bytes(3, "little")) + [r36]
    if new:
        f[17:28] = new
    return f


TWO, THREE, MISSING = list(b"TWO     TXT"), list(b"THREE   TXT"), list(b"MISSING TXT")
TEST2, SECOND = TEST, list(b"SECOND  TXT")


def dword(y, m, d):
    return ((y - 1980) << 9) | (m << 5) | d


def made2(name, date, index, pre):
    """FMAKE's FCB over one pre-filled with `pre` at +12 .. +36: +12 / +13 kept, +14 .. +19 0 (record size, file size),
    the date word at +20, the time 0, $40 at +24, the directory entry's index at +25, +26 .. +31 0, +32 .. +36 kept"""
    dw = dword(*date)
    return [0] + name + [pre, pre] + [0] * 6 + [dw & 0xFF, dw >> 8, 0, 0, 0x40, index] + [0] * 6 + [pre] * 5
F = lambda *names: (lambda c: c.fn in names)          # noqa: E731
S1 = "1. The FCB directory functions through $F37D"
RULES = [
    Rule("R-BF-MAKE", S1, "FMAKE ($16) of TEST.TXT on the empty disk, over a CLEARED FCB, answers A 0 and leaves it: "
         "+12 .. +19 0 (+12 / +13 as entered, R-BF-MAKE2; record size and file size written 0), the DATE word at +20 ($0821: 1984-01-01, the date after start-up), the time 0, "
         "$40 at +24, the rest 0. FCLOSE ($10) answers A 0 and leaves the FCB; FOPEN ($0F) of the closed file answers "
         "A 0 with the same FCB.", F("FMAKE", "FCLOSE", "FOPEN"),
         lambda c: c.a == 0 and c.fcb == made(TEST) and c.dta == E5),
    Rule("R-BF-SEARCH", S1, "SFIRST ($11) of ????????.TXT answers A 0 and puts the entry in the DTA: drive 1 (A:), the "
         "name, attribute 0; the FCB stays as set up. SNEXT ($12) then answers A $FF (no more) and leaves the DTA. After "
         "the file was renamed and deleted (a deleted entry left), SFIRST of ????????.??? answers A $FF and leaves the "
         "DTA.", F("SFIRST", "SNEXT", "SFIRSTALL"),
         lambda c: c.fcb == named(ALLQ if c.fn != "SFIRSTALL" else list(b"???????????"))
         and (c.a, c.dta) == ((0, [1] + TEST + [0]) if c.fn == "SFIRST" else (0xFF, E5))),
    Rule("R-BF-SIZE", S1, "FSIZE ($23) of the empty TEST.TXT answers A 0 with the random record +33 .. +35 = 0 (the FCB "
         "otherwise as set up).", F("FSIZE"), lambda c: c.a == 0 and c.fcb == named(TEST) and c.dta == E5),
    Rule("R-BF-REN", S1, "FREN ($17) TEST.TXT -> NEW.TXT (the new name at +17) answers A 0 and leaves the FCB; FOPEN of "
         "TEST.TXT then answers A $FF; FDEL ($13) of NEW.TXT answers A 0.", F("FREN", "FOPENOLD", "FDEL"),
         lambda c: {"FREN": c.a == 0 and c.fcb == named(TEST, NEW), "FOPENOLD": c.a == 0xFF and c.fcb == named(TEST),
                    "FDEL": c.a == 0 and c.fcb == named(NEW)}[c.fn] and c.dta == E5),
    Rule("R-BF-CARRY", S1, "The carry is SET on a NOT-FOUND answer (A $FF from SNEXT with no more, FOPEN of a missing "
         "file, SFIRST finding nothing) and clear on A 0 -- but FREN refusing a name that exists answers A $FF with the "
         "carry CLEAR (XB2 13): it marks not-found, not every A $FF. (The extent-$FF cases are R-BF-EXTENT's.)",
         lambda c: c.src in ("XB", "XB2") and c.fn not in ("WRSEQ", "FCLOSE2", "SDATE26", "FOPENPF"),
         lambda c: (c.f & 1) == (c.a == 0xFF and c.fn != "FRENEX")),
    Rule("R-BF-MAKE2", S1, "FMAKE writes the FCB's +14 .. +31 -- record size 0, file size 0, the DATE word of the current "
         "date ($5ACF after SDATE 2025-06-15, $5D76 after 2026-11-22), time 0, $40 at +24, the new entry's INDEX in the "
         "directory at +25 (0, then 1 for the second file), +26 .. +31 0 -- and leaves +12 / +13 and +32 .. +36 as they "
         "were ($FF here). FMAKE of a name that exists answers A 0 and makes it again (today's date).",
         F("FMAKEPF", "FMAKE2PF", "FMAKEEX"),
         lambda c: c.a == 0 and c.fcb == {"FMAKEPF": made2(TEST, (2025, 6, 15), 0, 0xFF),
                                           "FMAKE2PF": made2(SECOND, (2026, 11, 22), 1, 0xFF),
                                           "FMAKEEX": made2(TEST, (2026, 11, 22), 0, 0)}[c.fn] and c.dta == E5),
    Rule("R-BF-EXTENT", S1, "The FCB's EXTENT byte (+12) counts: left $FF by FMAKE, it makes WRSEQ ($15) answer A 1 and "
         "write nothing (+24 then 0, +32 $7F; FCLOSE answers A 0 with that FCB; FSIZE of the file then reads 0 "
         "records), and FOPEN with +12 $FF answers A $FF (no extent 255), writing +14 0 and leaving the rest. (Round 3 "
         "shows the extent ALONE does it: R-BF-SEQ3.) The flags there: "
         "WRSEQ F $44, FCLOSE F $93 (the carry SET with A 0), FOPEN F $82 (the carry CLEAR with A $FF); an SDATE "
         "between them leaves the FCB.", F("WRSEQ", "FCLOSE2", "SDATE26", "FSIZE2", "FOPENPF"),
         lambda c: {"WRSEQ": (c.a, c.f) == (1, 0x44), "FCLOSE2": (c.a, c.f) == (0, 0x93),
                    "SDATE26": (c.a, c.f) == (0, 0x44), "FSIZE2": (c.a, c.f) == (0, 0x44),
                    "FOPENPF": (c.a, c.f) == (0xFF, 0x82)}[c.fn]
         and c.fcb == {"FSIZE2": named(TEST),
                       "FOPENPF": [0] + TEST + [0xFF, 0xFF, 0x00] + [0xFF] * 22}.get(
             c.fn, (lambda f: f[:24] + [0] + f[25:32] + [0x7F] + f[33:])(made2(TEST, (2025, 6, 15), 0, 0xFF)))
         and c.dta == E5),
    Rule("R-BF-SEARCH2", S1, "With two files, SFIRST ??????????? finds TEST.TXT (the first entry), SNEXT SECOND.TXT, the "
         "next SNEXT A $FF.", F("SFIRSTQ", "SNEXT1", "SNEXT2"),
         lambda c: c.fcb == named(list(b"???????????")) and (c.a, c.dta) == {"SFIRSTQ": (0, [1] + TEST + [0]),
                                                                            "SNEXT1": (0, [1] + SECOND + [0]),
                                                                            "SNEXT2": (0xFF, E5)}[c.fn]),
    Rule("R-BF-RENEX", S1, "FREN onto a name that exists answers A $FF (carry clear, R-BF-CARRY) and leaves the FCB.",
         F("FRENEX"), lambda c: c.a == 0xFF and c.fcb == named(SECOND, TEST) and c.dta == E5),
    Rule("R-BF-SETDTA2", S1, "SETDTA answers A $08 whatever DE is ($9300 and $A800), F 0; SDATE of a valid date answers "
         "A 0 (as on the system functions' page).", lambda c: c.src == "XB20",
         lambda c: (c.a, c.f) == ((0x08, 0) if c.fn.startswith("SETDTA") else (0, 0x44)) and c.dta == E5),
    Rule("R-BF-SEQ3", S1, "Round 3 separates round 2's cause. With ONLY the extent +12 $FF, WRSEQ answers A 1 and "
         "writes nothing (+24's bit 6 cleared; FCLOSE then F $93). With only the current record +32 $FF it WRITES: at "
         "record (+32 AND $7F) = 127 of the extent -- the file becomes 16384 bytes, the clusters 2 .. 17 -- then the "
         "extent advances (+12 1) and +32 is 0; with +24 $41 and +32 $85 it writes record 5 (768 bytes, cluster 18), "
         "+32 becomes 6 and +24 $01: WRSEQ CLEARS bit 6 of +24, it does not write it. FCLOSE answers A 0 and leaves the "
         "FCB (F $42).", F(*FN3[:9]),
         lambda c: c.a == {"WRSEQEX": 1}.get(c.fn, 0) and c.dta == E5 and c.fcb == {
             "FMAKE3A": fcb(TEST), "WRSEQEX": fcb(TEST, ext=0xFF, b24=0), "FCLOSEEX": fcb(TEST, ext=0xFF, b24=0),
             "FMAKE3B": fcb(TWO, idx=1), "WRSEQCR": fcb(TWO, ext=1, size=0x4000, b24=0, idx=1, c1=2, c2=17, c3=15),
             "FCLOSECR": fcb(TWO, ext=1, size=0x4000, b24=0, idx=1, c1=2, c2=17, c3=15),
             "FMAKE3C": fcb(THREE, idx=2), "WRSEQ85": fcb(THREE, size=768, b24=1, idx=2, c1=18, c2=18, cr=6),
             "FCLOSE85": fcb(THREE, size=768, b24=1, idx=2, c1=18, c2=18, cr=6)}[c.fn]
         and (c.fn not in ("FCLOSEEX", "FCLOSECR", "FCLOSE85") or c.f == {"FCLOSEEX": 0x93}.get(c.fn, 0x42))),
    Rule("R-BF-OPEN3", S1, "FOPEN asks for the extent in +12: with +12 $FF, or 1 on a file of one extent, it answers A "
         "$FF (F $82 / $42 -- the carry CLEAR) and leaves the FCB. FOPEN of THREE.TXT (6 records) fills +15 (the "
         "records in the extent) 6, the size 768, the date, $40, its index 2, the clusters 18 / 18, the rest 0. FSIZE "
         "over $FF at +33 .. +36 writes the record count 6 to +33 .. +35 and leaves +36.",
         F("FOPENEXFF", "FOPENEX1", "FOPEN6", "FSIZE6"),
         lambda c: c.dta == E5 and {"FOPENEXFF": (c.a, c.f, c.fcb) == (0xFF, 0x82, fcb(TEST, ext=0xFF, b24=0, date=0)),
                                    "FOPENEX1": (c.a, c.f, c.fcb) == (0xFF, 0x42, fcb(TEST, ext=1, b24=0, date=0)),
                                    "FOPEN6": (c.a, c.fcb) == (0, fcb(THREE, rc=6, size=768, idx=2, c1=18, c2=18)),
                                    "FSIZE6": (c.a, c.fcb) == (0, fcb(THREE, b24=0, date=0, rr=6, r36=0xFF))}[c.fn]),
    Rule("R-BF-MISS", S1, "FDEL, FREN (the source) and FSIZE of a MISSING file answer A $FF with the carry SET and "
         "leave the FCB.", F("FDELMISS", "FRENMISS", "FSIZEMISS"),
         lambda c: (c.a, c.f & 1) == (0xFF, 1) and c.dta == E5
         and c.fcb == fcb(MISSING, b24=0, date=0, new=NEW if c.fn == "FRENMISS" else None)),
    Rule("R-BF-WORK", S1, "F, and SETDTA's A, are the same on both references in every case (mostly $44 on A 0, $45 on "
         "a not-found; but $10 / $42 / $93 after FCLOSE, $42 after FDEL, $44 on FREN's refusal, $82 / $42 on FOPEN's "
         "extent refusals; SETDTA A $08, F 0); SETDTA leaves the DTA alone.", lambda c: True,
         lambda c: (lambda o: (c.a, c.f) == (o.a, o.f))(other_ref(c)) and (c.fn != "SETDTA" or c.dta == E5)
         and (c.src not in ("XB2",) or True)),
]
