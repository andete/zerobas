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
FN2 = ["SETDTA2", "FMAKE2", "WRBLK2", "FCLOSE2A", "FOPEN2A", "RDBLKFO", "RDBLKEND", "RDBLKPART2", "WRBLK0", "FCLOSE2B",
       "FOPEN2B", "WRZERRS1", "FCLOSE2C", "FOPEN2C", "RDBLK4", "RDABS2"]
RUNS2 = [("XBBLK2_run1.out", "D"), ("XBBLK2_run2.out", "C")]
FN3 = ["SETDTA3", "FMAKEC", "WRZERC", "FCLOSEC", "FOPENC", "RDBLKC", "FMAKED", "WRBLKD", "FCLOSED", "FOPEND",
       "RDBLKD", "FSIZEMISS"]
RUNS3 = [("XBBLK3_run1.out", "D"), ("XBBLK3_run2.out", "C")]
SPOTS3 = (383, 384, 511, 512, 767, 768, 1023, 1024)
FN4 = ["SETDTA4", "FMAKEE", "WRBLKE512", "FSIZE4A", "WRBLK0RS1", "FSIZE4B", "FCLOSE4A", "FSIZE4C", "FOPEN4A",
       "RDBLK3", "WRBLKOVER", "WRBLK0EXT", "WRZERHL2", "WRZERLOW", "FCLOSE4B", "FSIZE4D", "FOPEN4B", "RDBLK8"]
RUNS4 = [("XBBLK4_run1.out", "D"), ("XBBLK4_run2.out", "C")]
SPOTS4 = (49, 50, 127, 128, 255, 383, 511, 767, 1023, 1024)
FN5 = ["SETDTA5", "FMAKEF", "WRBLKF1024", "FCLOSE5A", "FOPENF80", "RDBLK180", "WRBLK0SHR", "RDBLK400", "WRZER6",
       "WRBLKRR2", "WRBLKGAP", "FCLOSE5B", "FSIZE5", "FOPEN5", "RDBLK8A", "RDBLK8B"]
RUNS5 = [("XBBLK5_run1.out", "D"), ("XBBLK5_run2.out", "C")]
SPOTS5 = (127, 128, 383, 384, 511, 512, 520, 700, 767, 768, 1023, 1024)
FN6 = ["SETDTA6", "FMAKEH", "WRBLKH1", "WRBLKH2", "FCLOSE6A", "FDELH", "FMAKEG", "WRBLKG", "WRBLK180", "WRBLK0180",
       "WRBLKRR5", "WRBLK1800", "FCLOSE6B", "FOPEN6", "RDBLK6A", "RDBLK6B"]
RUNS6 = [("XBBLK6_run1.out", "D"), ("XBBLK6_run2.out", "C")]
SPOTS6 = (383, 384, 476, 511, 512, 639, 640, 767, 768, 776, 1023, 1024)
BOOT512 = list(open(os.path.join(ROOT, "disk", "empty720.dsk"), "rb").read()[:512])
OUTPUTS = {"XK": ["a", "f", "fcb", "dta", "hl"], "XK0": ["a", "f", "dta", "hl"], "XK2": ["a", "f", "fcb", "dta", "hl", "spots"],
           "XK20": ["a", "f", "dta", "hl", "spots"], "XK3": ["a", "f", "fcb", "dta", "hl", "spots"],
           "XK30": ["a", "f", "dta", "hl", "spots"], "XK4": ["a", "f", "fcb", "dta", "hl", "spots"],
           "XK40": ["a", "f", "dta", "hl", "spots"], "XK5": ["a", "f", "fcb", "dta", "hl", "spots"],
           "XK50": ["a", "f", "dta", "hl", "spots"], "XK6": ["a", "f", "fcb", "dta", "hl", "spots"],
           "XK60": ["a", "f", "dta", "hl", "spots"]}
B = list(b"B       TXT")
BOOT = list(open(os.path.join(ROOT, "disk", "empty720.dsk"), "rb").read()[:13])   # our own generated image's sector 0
# bytes 128 .. 199 of the file came from RAM past the probe's 128-byte DTA fill (WRBLK wrote 200 bytes): reads of them
# show each machine's own leftover RAM
UNSTABLE = {f"XK {row}{n:02}": (["dta"], "bytes 128 .. 199 of B.TXT: WRBLK took them from RAM past the probe's 128-byte "
                                "fill, so XBBLK1 run 1 (VG-8020 + NMS 1200) and run 2 (CF-3300) read different bytes")
            for row in "DC" for n in (6, 8)}
# XBBLK2 case 9: FCLOSE after WRBLK with HL 0 -- the two references answer different A / F / HL
UNSTABLE.update({f"XK2 {row}09": (["a", "f", "hl"], "FCLOSE after WRBLK HL 0: XBBLK2 run 1 (VG-8020 + NMS 1200) "
                                  "answers A 0, run 2 (CF-3300) A $FF -- an error answer, though FOPEN then finds the "
                                  "size written on both") for row in "DC"})
# XBBLK4 cases 6 / 14: FCLOSE after a WRBLK HL 0 / a WRZER -- the same split (case 14), or F / HL only (case 6)
UNSTABLE.update({f"XK4 {row}{n:02}": (["a", "f", "hl"], "FCLOSE: XBBLK4 run 1 (VG-8020 + NMS 1200) and run 2 "
                                      "(CF-3300) return different F and HL (case 6) and A 0 vs $FF (case 14), while "
                                      "FSIZE / FOPEN after it find the same size on both") for row in "DC" for n in (6, 14)})
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
    for run, row in RUNS2:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 58 * len(FN2) - len(b)))
            res = b[57]                                  # DTA+512 at case 0: past the fill, this machine's own RAM
            for i, fn in enumerate(FN2):
                r = b[58 * i: 58 * (i + 1)]
                c = NS(src="XK20" if i == 0 else "XK2", id=f"XK2 {row}{i:02}", row=row, num=100 + i, fn=fn, a=r[0],
                       f=r[1], dta=list(r[39:52]), hl=(r[52] << 8) | r[53], spots=list(r[54:58]), res=res)
                if i:
                    c.fcb = list(r[2:39])
                d[who].append(c)
    for run, row in RUNS3:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 62 * len(FN3) - len(b)))
            for i, fn in enumerate(FN3):
                r = b[62 * i: 62 * (i + 1)]
                c = NS(src="XK30" if i == 0 else "XK3", id=f"XK3 {row}{i:02}", row=row, num=200 + i, fn=fn, a=r[0],
                       f=r[1], dta=list(r[39:52]), hl=(r[52] << 8) | r[53], spots=list(r[54:62]))
                if i:
                    c.fcb = list(r[2:39])
                d[who].append(c)
    for run, row in RUNS4:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 64 * len(FN4) - len(b)))
            for i, fn in enumerate(FN4):
                r = b[64 * i: 64 * (i + 1)]
                c = NS(src="XK40" if i == 0 else "XK4", id=f"XK4 {row}{i:02}", row=row, num=300 + i, fn=fn, a=r[0],
                       f=r[1], dta=list(r[39:52]), hl=(r[52] << 8) | r[53], spots=list(r[54:64]))
                if i:
                    c.fcb = list(r[2:39])
                d[who].append(c)
    for run, row in RUNS5:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 66 * len(FN5) - len(b)))
            for i, fn in enumerate(FN5):
                r = b[66 * i: 66 * (i + 1)]
                c = NS(src="XK50" if i == 0 else "XK5", id=f"XK5 {row}{i:02}", row=row, num=400 + i, fn=fn, a=r[0],
                       f=r[1], dta=list(r[39:52]), hl=(r[52] << 8) | r[53], spots=list(r[54:66]))
                if i:
                    c.fcb = list(r[2:39])
                d[who].append(c)
    for run, row in RUNS6:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 66 * len(FN6) - len(b)))
            for i, fn in enumerate(FN6):
                r = b[66 * i: 66 * (i + 1)]
                c = NS(src="XK60" if i == 0 else "XK6", id=f"XK6 {row}{i:02}", row=row, num=500 + i, fn=fn, a=r[0],
                       f=r[1], dta=list(r[39:52]), hl=(r[52] << 8) | r[53], spots=list(r[54:66]))
                if i:
                    c.fcb = list(r[2:39])
                d[who].append(c)
    _cache["d"] = d
    return d


def other_ref(c):
    return next(o for o in cases()["ref"] if o.src == c.src and o.num == c.num and o.row != c.row)


def mark(n, off=0):
    return [(0x40 + n + off + i) & 0xFF for i in range(13)]


def rs(f, size):
    """an FCB with the record size word at +14"""
    f = list(f)
    f[14], f[15] = size & 0xFF, size >> 8
    return f


O = dict(c1=2, c2=2)                                  # the file's cluster, 2


def m2(n, off):
    """XBBLK2's DTA byte at offset off as case n filled it"""
    return (0x40 + n + off) & 0xFF


def data(off):
    """byte off of B.TXT as WRBLK (case 2) wrote it"""
    return m2(2, off)


C, D3, MISS = list(b"C       TXT"), list(b"D       TXT"), list(b"MISSING TXT")


def file3(fn, i):
    """byte i of C.TXT (records 0 .. 2 WRZER's zero fill, record 3 case 2's DTA) or D.TXT (case 7's 300 bytes)"""
    if fn == "RDBLKC":
        return m2(2, i - 384) if 384 <= i < 512 else 0
    return m2(7, i) if i < 300 else 0


def expect3(c):
    """(DTA's first 13, the 8 spots) after case c of XBBLK3: a read of +15 x 256 bytes, else the fill"""
    n = c.num - 200
    span = {"RDBLKC": 1024, "RDBLKD": 768}.get(c.fn, 0)
    at = lambda o: file3(c.fn, o) if o < span else m2(n, o)
    return [at(i) for i in range(13)], [at(o) for o in SPOTS3]


E = list(b"E       TXT")


def file4(fn, i):
    """byte i of E.TXT as RDBLK reads it in XBBLK4 case 9 (the 50-byte file) or 17 (the 768-byte one)"""
    if fn == "RDBLK3":
        return m2(2, i) if i < 50 else 0
    if i < 10:
        return m2(10, i)                       # the overwrite
    if 128 <= i < 256:
        return m2(13, i - 128)                 # WRZER RR 1: the DTA's record
    if 384 <= i < 640:
        return 0                               # records 3 .. 4: WRZER RR 5's zero fill
    if 640 <= i < 768:
        return m2(12, i - 640)                 # WRZER RR 5: the DTA's record
    return m2(2, i)                            # the first 512 bytes as case 2 wrote them, past every later EOF


def expect4(c):
    n = c.num - 300
    span = {"RDBLK3": 128, "RDBLK8": 768}.get(c.fn, 0)
    at = lambda o: file4(c.fn, o) if o < span else m2(n, o)
    return [at(i) for i in range(13)], [at(o) for o in SPOTS4]


FT = list(b"F       TXT")


def file5(fn, j):
    """byte j of F.TXT as RDBLK reads it in XBBLK5 case 5, 7, 14 or 15"""
    if fn == "RDBLK180":
        return m2(2, j)                        # the 1024 bytes case 2 wrote
    if fn == "RDBLK400":
        return m2(2, j) if j < 384 else 0      # shrunk to 384: zeros past it, not the older bytes
    if j >= 2001:
        return 0                               # past the end
    if 1536 <= j:                              # the sector WRBLK RR 2000 wrote into: the DOS's buffer -- the
        k = j - 1536                           # file's sector 0 as case 9 left it -- with byte 2000 in it
        return m2(10, 0) if j == 2000 else (m2(2, k) if k < 256 else m2(9, k - 256))
    if 1024 <= j:
        return 0                               # the new cluster's first sector: never written (the blank image)
    if 256 <= j < 512:
        return m2(9, j - 256)                  # WRBLK 2 x 128 at RR 2
    if 512 <= j < 768:
        return 0                               # WRZER RR 6's zero fill, over the older bytes
    if 768 <= j < 896:
        return m2(8, j - 768)                  # WRZER's record
    return m2(2, j)                            # case 2's bytes: 0 .. 255, and 896 .. 1023 (the gap's older bytes)


def expect5(c):
    n = c.num - 400
    span = {"RDBLK180": 384, "RDBLK400": 1024, "RDBLK8A": 1024, "RDBLK8B": 1024}.get(c.fn, 0)
    base = 1024 if c.fn == "RDBLK8B" else 0
    at = lambda o: file5(c.fn, base + o) if o < span else m2(n, o)
    return [at(i) for i in range(13)], [at(o) for o in SPOTS5]


H6, G6 = list(b"H       TXT"), list(b"G       TXT")


def m6(n, i):
    """XBBLK6's DTA byte i as case n filled it: no two sectors alike"""
    return (0x40 + n + (i & 0xFF) + (i >> 8) * 16) & 0xFF


def g6(j):
    """byte j of G.TXT as XBBLK6 leaves it"""
    if j >= 1801:
        return 0                               # past the end: the read zero-fills
    if j == 1800:
        return m6(11, 0)                       # the byte WRBLK RR 1800 wrote
    if j >= 1536:
        return g6(512 + j - 1536)              # the DOS's buffer: the LAST sector transferred, G's sector 1
    if j >= 1024:
        return m6(3, j - 1024)                 # the new cluster's skipped sector: the deleted H.TXT's bytes
    if j < 384 or j >= 768:
        return m6(7, j)                        # case 7's bytes (768 .. 1023: older bytes past every later end)
    if j >= 640:
        return m6(10, j - 640)                 # WRBLK 1 x 128 at RR 5
    return m6(8, j - 384)                      # WRBLK 1 x $0180 at RR 1, kept past the shrink to 384


def expect6(c):
    n = c.num - 500
    span, base = {"RDBLK6A": (1024, 0), "RDBLK6B": (896, 1024)}.get(c.fn, (0, 0))
    at = lambda o: g6(base + o) if o < span else m6(n, o)
    return [at(i) for i in range(13)], [at(o) for o in SPOTS6]


def expect2(c):
    """(DTA's first 13, spots +72 / +128 / +511) after case c of XBBLK2; +512 is checked against the residue"""
    n = c.num - 100
    untouched = ([m2(n, i) for i in range(13)], [m2(n, 72), m2(n, 128), m2(n, 511)])
    return {"RDBLKFO": ([data(i) for i in range(13)], [data(72), data(128), 0]),
            "RDBLKPART2": ([data(128 + i) for i in range(13)], [0, m2(n, 128), m2(n, 511)]),
            "RDBLK4": ([data(i) for i in range(13)], [data(72), 0, m2(11, 127)]),
            "RDABS2": (BOOT512[:13], [BOOT512[72], BOOT512[128], BOOT512[511]])}.get(c.fn, untouched)
F = lambda *names: (lambda c: c.fn in names)          # noqa: E731
S1 = "1. The block functions through $F37D"
RULES = [
    Rule("R-BK-WRBLK", S1, "WRBLK ($26) with record size 1 (+14) and RR 0 writes HL = 200 records of 1 byte from the "
         "DTA: A 0, HL 200 (the records written), the size 200, RR 200, +24's bit 6 cleared, the clusters 2; FCLOSE "
         "answers A 0 and leaves the FCB. FOPEN then shows +14 0 and +15 2 (records of 128, rounded up) -- the "
         "word the block functions read as the record size: $0200 (R-BK-ROUND2).",
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
         "bytes, rounded up) and CLEARS +14 (+15 was 0 here; round 4 shows it kept). It reads the DIRECTORY: the 512 bytes WRZER wrote "
         "(no FCLOSE) are not counted yet.", F("FSIZERS1", "FSIZERS128"),
         lambda c: c.a == 0 and c.dta == mark(c.num) and c.fcb == fcb(B, b24=0, date=0, rr=2)),
    Rule("R-BK-WRZER", S1, "WRZER ($28) with RR 3 on that FCB (not opened: FSIZE's) answers A 0 and writes record 3 "
         "(size 512, CR 3, RR 3, clusters 3), +14 then 0; HL 0.", F("WRZER3"),
         lambda c: (c.a, c.hl) == (0, 0) and c.dta == mark(10)
         and c.fcb == fcb(B, size=512, b24=0, c1=3, c2=3, cr=3, rr=3)),
    Rule("R-BK-RDABS", S1, "RDABS ($2F) with DE 0, H 1, L 0 reads sector 0 of drive A into the DTA (the generated "
         "image's boot sector) and answers A 0, HL 0. (DE is the sector; it takes no FCB).", F("RDABS0"),
         lambda c: (c.a, c.hl) == (0, 0) and c.dta == BOOT and c.fcb == fcb(B, b24=0, date=0, rr=2)),
    Rule("R-BK-ROUND2", S1, "Round 2 (the DTA filled for 512 bytes): FOPEN leaves +14 0 and +15 the records of 128 (2 for "
         "200 bytes), so the record-size word is $0200 -- 512 -- and RDBLK HL 1 straight after it reads one 512-byte record: B.TXT's 200 bytes, then ZEROS (+511 0; A 0, HL 1, RR 1). RDBLK at the end (RS 1, RR 200, HL 5) reads nothing: A 1, HL 0, RR and the DTA left. "
         "The partial record (RS 128, RR 1) puts bytes 128 .. 199 in the DTA and zeros after them (+72: byte 200). "
         "WRBLK with HL 0 sets the file's size to RR x the record size (128) and writes nothing. WRZER ignores the "
         "record size (RS 1 at RR 3 writes 128-byte record 3: the size 512), zero-fills the records it skips "
         "(record 1 reads 0) and leaves +14 / +15 0. RDABS reads all 512 bytes of the sector (+511: the boot "
         "signature's $AA) and not one more. Nothing writes past what it transfers (DTA+512 keeps its byte).",
         lambda c: c.src == "XK2",
         lambda c: (c.dta, c.spots[:3]) == expect2(c) and c.spots[3] == c.res
         and (c.fn == "FCLOSE2B" or (c.a, c.hl) == {"RDBLKFO": (0, 1), "RDBLKEND": (1, 0), "RDBLKPART2": (0, 1),
                                                    "WRBLK0": (0, 0), "WRZERRS1": (0, 0), "RDBLK4": (0, 4),
                                                    "RDABS2": (0, 0), "WRBLK2": (0, 200)}.get(c.fn, (0, c.hl)))
         and c.fcb == {
             "FMAKE2": fcb(B), "WRBLK2": rs(fcb(B, size=200, b24=0, rr=200, **O), 1),
             "FCLOSE2A": rs(fcb(B, size=200, b24=0, rr=200, **O), 1), "FOPEN2A": fcb(B, rc=2, size=200, **O),
             "RDBLKFO": fcb(B, rc=2, size=200, rr=1, **O), "RDBLKEND": rs(fcb(B, size=200, rr=200, **O), 1),
             "RDBLKPART2": rs(fcb(B, size=200, rr=2, **O), 128), "WRBLK0": rs(fcb(B, size=128, b24=0, rr=1, **O), 128),
             "FCLOSE2B": rs(fcb(B, size=128, b24=0, rr=1, **O), 128), "FOPEN2B": fcb(B, rc=1, size=128, **O),
             "WRZERRS1": fcb(B, size=512, b24=0, cr=3, rr=3, **O), "FCLOSE2C": fcb(B, size=512, b24=0, cr=3, rr=3, **O),
             "FOPEN2C": fcb(B, rc=4, size=512, **O), "RDBLK4": rs(fcb(B, rc=4, size=512, rr=4, **O), 128),
             "RDABS2": rs(fcb(B, rc=4, size=512, rr=4, **O), 128)}[c.fn]),
    Rule("R-BK-FOPENRS", S1, "Round 3: FOPEN sets +14 0 and +15 the file's records of 128, rounded up (4 for 512 bytes, "
         "3 for 300), and the block functions read +14 / +15 as ONE record-size word -- so RDBLK HL 1 straight after "
         "FOPEN reads a record of +15 x 256 bytes: 1024 from the 512-byte file (its bytes, then zeros to +1023), 768 "
         "from the 300-byte one (zeros to +767), nothing past it; A 0, HL 1, RR 1. Not \"the record size is "
         "$0200\" (round 2's file could not tell). WRZER (RS 128, RR 3) on a freshly made FCB writes record 3 and "
         "zero-fills records 0 .. 2 (size 512, CR 3, RR 3, +14 cleared; +15 was 0 going in); WRBLK 300 x 1 keeps RS 1; FSIZE of a "
         "missing file answers A $FF and leaves the FCB and the DTA.",
         lambda c: c.src == "XK3",
         lambda c: (c.dta, c.spots) == expect3(c)
         and ((c.a, c.hl) == (0, 1) if c.fn.startswith("RDBLK") else c.a == (0xFF if c.fn == "FSIZEMISS" else 0))
         and c.fcb == {
             "FMAKEC": fcb(C), "WRZERC": fcb(C, size=512, b24=0, c1=2, c2=2, cr=3, rr=3),
             "FCLOSEC": fcb(C, size=512, b24=0, c1=2, c2=2, cr=3, rr=3), "FOPENC": fcb(C, rc=4, size=512, c1=2, c2=2),
             "RDBLKC": fcb(C, rc=4, size=512, c1=2, c2=2, rr=1), "FMAKED": fcb(D3, idx=1),
             "WRBLKD": rs(fcb(D3, size=300, b24=0, idx=1, c1=3, c2=3, rr=300), 1),
             "FCLOSED": rs(fcb(D3, size=300, b24=0, idx=1, c1=3, c2=3, rr=300), 1),
             "FOPEND": fcb(D3, rc=3, size=300, idx=1, c1=3, c2=3),
             "RDBLKD": fcb(D3, rc=3, size=300, idx=1, c1=3, c2=3, rr=1),
             "FSIZEMISS": fcb(MISS, b24=0, date=0)}[c.fn]),
    Rule("R-BK-ROUND4", S1, "Round 4. WRBLK sets the size to the larger of the old size and where it stopped (10 x 1 "
         "at RR 0 over 50 bytes: 50). WRBLK HL 0 sets the size to RR x the record size whichever way that moves it "
         "(RS 1, RR 50: 512 -> 50; RS 128, RR 3: 50 -> 384) and writes nothing: the bytes it takes in are whatever "
         "the sectors held (case 2's, read back at +50 .. +383). WRZER writes the DTA's record at RR, zero-fills the "
         "records between the old end and RR (+511 reads 0), ignores HL (HL 2: one record, size 768) and "
         "never shrinks the file (RR 1 under 768: the size stays). FSIZE and WRZER clear +14 and KEEP +15 (RS $0180 "
         "in: $0100 out). FSIZE reads the directory: 0 records before the first FCLOSE, then 1 for 50 bytes and 6 "
         "for exactly 768 (rounded up, not + 1). RDBLK 3 x 128 over the 50-byte file reads its one partial record: "
         "A 1, HL 1, RR 1, the 50 bytes then zeros -- not the older bytes still in the sector. RDBLK 8 x 128 over "
         "768 bytes: A 1, HL 6, RR 6, nothing past +767.",
         lambda c: c.src == "XK4",
         lambda c: (c.dta, c.spots) == expect4(c)
         and (c.fn.startswith("FCLOSE") or c.a == {"RDBLK3": 1, "RDBLK8": 1}.get(c.fn, 0))
         and (c.hl == {"RDBLK3": 1, "RDBLK8": 6, "WRBLKOVER": 10, "WRBLKE512": 512}[c.fn]
              if c.fn in ("RDBLK3", "RDBLK8", "WRBLKOVER", "WRBLKE512") else True)
         and c.fcb == {
             "FMAKEE": fcb(E), "WRBLKE512": rs(fcb(E, size=512, b24=0, rr=512, **O), 1),
             "FSIZE4A": rs(fcb(E, date=0, b24=0), 0x0100), "WRBLK0RS1": rs(fcb(E, size=50, b24=0, rr=50, **O), 1),
             "FSIZE4B": rs(fcb(E, date=0, b24=0), 0x0100), "FCLOSE4A": rs(fcb(E, size=50, b24=0, rr=50, **O), 1),
             "FSIZE4C": rs(fcb(E, date=0, b24=0, rr=1), 0x0100), "FOPEN4A": fcb(E, rc=1, size=50, **O),
             "RDBLK3": rs(fcb(E, size=50, rr=1, **O), 128), "WRBLKOVER": rs(fcb(E, size=50, b24=0, rr=10, **O), 1),
             "WRBLK0EXT": rs(fcb(E, size=384, b24=0, rr=3, **O), 128),
             "WRZERHL2": rs(fcb(E, size=768, b24=0, cr=5, rr=5, **O), 0x0100),
             "WRZERLOW": fcb(E, size=768, b24=0, cr=1, rr=1, **O), "FCLOSE4B": fcb(E, size=768, b24=0, cr=1, rr=1, **O),
             "FSIZE4D": rs(fcb(E, date=0, b24=0, rr=6), 0x0100), "FOPEN4B": fcb(E, rc=6, size=768, **O),
             "RDBLK8": rs(fcb(E, rc=6, size=768, rr=6, **O), 128)}[c.fn]),
    Rule("R-BK-ROUND5", S1, "Round 5. FOPEN overwrites +14 / +15 ($80 / $FF going in: 0 / 8 for 1024 bytes). The "
         "record size is ONE word: RS $0180 reads 384 bytes (+383 the file's, +384 left), not +14's 128. WRBLK "
         "writes at RR x RS (2 x 128 at RR 2: bytes 256 .. 511; RR 4, HL 2, the size kept). WRZER at RR 6 over a "
         "file shrunk from 1024 to 384 zero-fills 512 .. 767 although the sector still held the older bytes, and "
         "clears +14. A read of a 1024-byte record over the 384-byte file: the 384 bytes, then zeros to +1023 -- "
         "not the older sector bytes; A 0, HL 1. WRBLK 1 x 1 at RR 2000 sets the size 2001 and links a second "
         "cluster (+28 3, +30 1); what the gap reads: 896 .. 1023 the OLDER bytes still in that sector, the new "
         "cluster's first sector the blank image's zeros, and the sector the byte went into the DOS's sector "
         "buffer -- the file's sector 0 as it last transferred it -- with byte 2000 in it, then zeros past the "
         "end. FSIZE keeps +15 $FF (+14 cleared). RDBLK 8 x 128 twice: A 0, HL 8, RR 8 then 16 (the second ends "
         "in the partial record 15, which counts).",
         lambda c: c.src == "XK5",
         lambda c: (c.dta, c.spots) == expect5(c)
         and (c.fn.startswith("FCLOSE") or c.a == 0)
         and (c.hl == {"RDBLK180": 1, "RDBLK400": 1, "WRBLKRR2": 2, "WRBLKGAP": 1, "RDBLK8A": 8, "RDBLK8B": 8,
                       "WRBLKF1024": 1024}[c.fn]
              if c.fn in ("RDBLK180", "RDBLK400", "WRBLKRR2", "WRBLKGAP", "RDBLK8A", "RDBLK8B", "WRBLKF1024")
              else True)
         and c.fcb == {
             "FMAKEF": fcb(FT), "WRBLKF1024": rs(fcb(FT, size=1024, b24=0, rr=1024, **O), 1),
             "FCLOSE5A": rs(fcb(FT, size=1024, b24=0, rr=1024, **O), 1), "FOPENF80": fcb(FT, rc=8, size=1024, **O),
             "RDBLK180": rs(fcb(FT, size=1024, rr=1, **O), 0x0180),
             "WRBLK0SHR": rs(fcb(FT, size=384, b24=0, rr=3, **O), 128),
             "RDBLK400": rs(fcb(FT, size=384, b24=0, rr=1, **O), 0x0400),
             "WRZER6": fcb(FT, size=896, b24=0, cr=6, rr=6, **O),
             "WRBLKRR2": rs(fcb(FT, size=896, b24=0, cr=6, rr=4, **O), 128),
             "WRBLKGAP": rs(fcb(FT, size=2001, b24=0, c1=2, c2=3, c3=1, cr=6, rr=2001), 1),
             "FCLOSE5B": rs(fcb(FT, size=2001, b24=0, c1=2, c2=3, c3=1, cr=6, rr=2001), 1),
             "FSIZE5": rs(fcb(FT, date=0, b24=0, rr=16), 0xFF00), "FOPEN5": fcb(FT, rc=16, size=2001, **O),
             "RDBLK8A": rs(fcb(FT, size=2001, rr=8, **O), 128),
             "RDBLK8B": rs(fcb(FT, size=2001, c1=2, c2=3, c3=1, rr=16), 128)}[c.fn]),
    Rule("R-BK-ROUND6", S1, "Round 6 (the fill differs in every sector). WRBLK and WRBLK HL 0 read +14 / +15 as one "
         "word too: 1 x $0180 at RR 1 writes bytes 384 .. 767 (RR 2, HL 1), and HL 0 at RR 1 sets the size 384. "
         "Past the end, nothing is zeroed: after the shrink to 384, bytes 384 .. 639 keep what case 8 wrote and "
         "768 .. 1023 what case 7 did; WRBLK 1 x 1 at RR 1800 links a new cluster whose first sector keeps the "
         "deleted H.TXT's bytes (the DISK's, not zeros) and builds the sector it writes into from the DOS's buffer "
         "-- the LAST sector transferred (G's sector 1, as case 10 left it), not the file's first -- with byte 1800 "
         "in it. RDBLK 8 x 128 from RR 8 over 1801 bytes: A 1, HL 7, RR 15 (record 14, partial, counts; record 15 "
         "is past the end). FDEL leaves the FCB; G takes H's directory entry 0 and cluster 2 again.",
         lambda c: c.src == "XK6",
         lambda c: (c.dta, c.spots) == expect6(c)
         and (c.fn.startswith("FCLOSE") or c.a == (1 if c.fn == "RDBLK6B" else 0))
         and (c.hl == {"WRBLKH1": 1024, "WRBLKH2": 1024, "WRBLKG": 1024, "WRBLK180": 1, "WRBLK0180": 0,
                       "WRBLKRR5": 1, "WRBLK1800": 1, "RDBLK6A": 8, "RDBLK6B": 7}.get(c.fn, c.hl))
         and c.fcb == {
             "FMAKEH": fcb(H6), "WRBLKH1": rs(fcb(H6, size=1024, b24=0, rr=1024, **O), 1),
             "WRBLKH2": rs(fcb(H6, size=2048, b24=0, c1=2, c2=3, c3=1, rr=2048), 1),
             "FCLOSE6A": rs(fcb(H6, size=2048, b24=0, c1=2, c2=3, c3=1, rr=2048), 1),
             "FDELH": fcb(H6, b24=0, date=0), "FMAKEG": fcb(G6),
             "WRBLKG": rs(fcb(G6, size=1024, b24=0, rr=1024, **O), 1),
             "WRBLK180": rs(fcb(G6, size=1024, b24=0, rr=2, **O), 0x0180),
             "WRBLK0180": rs(fcb(G6, size=384, b24=0, rr=1, **O), 0x0180),
             "WRBLKRR5": rs(fcb(G6, size=768, b24=0, rr=6, **O), 128),
             "WRBLK1800": rs(fcb(G6, size=1801, b24=0, c1=2, c2=3, c3=1, rr=1801), 1),
             "FCLOSE6B": rs(fcb(G6, size=1801, b24=0, c1=2, c2=3, c3=1, rr=1801), 1),
             "FOPEN6": fcb(G6, rc=15, size=1801, **O), "RDBLK6A": rs(fcb(G6, size=1801, rr=8, **O), 128),
             "RDBLK6B": rs(fcb(G6, size=1801, c1=2, c2=3, c3=1, rr=15), 128)}[c.fn]),
    Rule("R-BK-WORK", S1, "A, F and HL are the same on both references in every case but the FCLOSEs declared UNSTABLE "
         "below (HL is a working value after the non-block functions); SETDTA answers A $08 and leaves the DTA.",
         lambda c: True,
         lambda c: (c.fn in ("FCLOSE2B", "FCLOSE4A", "FCLOSE4B") or (lambda o: (c.a, c.f, c.hl) == (o.a, o.f, o.hl))(other_ref(c)))
         and (c.fn != "SETDTA6" or (c.dta, c.spots) == ([m6(0, i) for i in range(13)], [m6(0, o) for o in SPOTS6]))
         and (c.fn != "SETDTA5" or (c.dta, c.spots) == ([m2(0, i) for i in range(13)], [m2(0, o) for o in SPOTS5]))
         and (c.fn != "SETDTA4" or (c.dta, c.spots) == ([m2(0, i) for i in range(13)], [m2(0, o) for o in SPOTS4]))
         and (c.fn not in ("SETDTA", "SETDTA2", "SETDTA3") or c.dta == (mark(0) if c.fn == "SETDTA" else
                                                                         [m2(0, i) for i in range(13)]))
         and (c.fn != "SETDTA3" or c.spots == [m2(0, o) for o in SPOTS3])
         and (c.fn != "SETDTA2" or (c.spots[:3] == [m2(0, 72), m2(0, 128), m2(0, 511)] and c.spots[3] == c.res))),
]
