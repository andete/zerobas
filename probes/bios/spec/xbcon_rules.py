#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/bdos/CONIN.md's EXECUTABLE RULES (docs/spec-method.md §3a): the BDOS's console INPUT functions through $F37D,
from the XBCON1 probe (probes/bios/spec/xbcon1.asm documents the 11 cases and the 24-byte record: A, F, H, L, CSRY,
CSRX, PUTPNT's and GETPNT's low bytes, BUFIN's 12-byte buffer, the screen's first row at name-table columns 2 .. 5) on
two reference rows: run 1 (scratchpad/XBCON1_run1.out, the VG-8020 + NMS 1200) and run 2 (XBCON1_run2.out, the
CF-3300). Before each case the BIOS key buffer is emptied (GETPNT = PUTPNT = KEYBUF, $FBF0) and the case's keys put
in it, so PUTPNT's low byte is $F0 + the keys given and GETPNT's tells how many the call took."""
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec_rules import Rule  # noqa: E402

PAGE = "docs/bdos/CONIN.md"
FN = ["CONST0", "CONSTX", "CONINA", "DIRIO0", "DIRIOB", "IN07C", "IN08D", "CONINCR", "CONINCA", "BUFINHI", "CONINE"]
RUNS = [("XBCON1_run1.out", "D"), ("XBCON1_run2.out", "C")]
OUTPUTS = {"XN": ["a", "f", "hl", "csr", "put", "get", "buf", "scr"]}
UNSTABLE = {}
_cache = {}


def cases():
    if "d" in _cache:
        return _cache["d"]
    d = {"ref": [], "zb": []}
    for run, row in RUNS:
        t = open(os.path.join(ROOT, "scratchpad", run)).read()
        for who, key in (("ref", "ref"), ("zb", "ours")):
            b = bytes.fromhex(re.search(rf"CAP {key}\s*:\s*([0-9a-fA-F]+)", t).group(1))
            b += bytes(max(0, 24 * len(FN) - len(b)))
            for i, fn in enumerate(FN):
                r = b[24 * i: 24 * (i + 1)]
                d[who].append(NS(src="XN", id=f"XN {row}{i:02}", row=row, num=i, fn=fn, a=r[0], f=r[1],
                                 hl=(r[2] << 8) | r[3], csr=(r[4], r[5]), put=r[6], get=r[7], buf=list(r[8:20]),
                                 scr=list(r[20:24])))
    _cache["d"] = d
    return d


SP = 0x20
BUF0 = [10] + [0xEE] * 11                               # BUFIN's buffer going in: max 10, the rest $EE
# per case: A, (CSRY, CSRX), PUTPNT / GETPNT low bytes after, the buffer, the first row's columns 2 .. 5
EXPECT = {
    "CONST0": (0x00, (1, 1), 0xF0, 0xF0, BUF0, [SP] * 4),
    "CONSTX": (0xFF, (1, 1), 0xF1, 0xF1, BUF0, [SP] * 4),         # the key LEAVES the BIOS buffer
    "CONINA": (0x58, (1, 2), 0xF1, 0xF1, BUF0, [0x58, SP, SP, SP]),  # CONST's 'X', echoed; 'A' taken too
    "DIRIO0": (0x41, (1, 2), 0xF0, 0xF0, BUF0, [0x58, SP, SP, SP]),  # the 'A' CONIN's echo took, no key waiting
    "DIRIOB": (0x42, (1, 2), 0xF1, 0xF1, BUF0, [0x58, SP, SP, SP]),
    "IN07C": (0x43, (1, 2), 0xF1, 0xF1, BUF0, [0x58, SP, SP, SP]),
    "IN08D": (0x44, (1, 2), 0xF1, 0xF1, BUF0, [0x58, SP, SP, SP]),
    "CONINCR": (0x0D, (1, 1), 0xF1, 0xF1, BUF0, [0x58, SP, SP, SP]),
    "CONINCA": (0x01, (1, 1), 0xF1, 0xF1, BUF0, [0x58, SP, SP, SP]),
    "BUFINHI": (0x0D, (1, 1), 0xF3, 0xF3, [10, 2, 0x48, 0x49, 0x0D] + [0xEE] * 7, [0x08, 0x49, SP, SP]),
    "CONINE": (0x45, (1, 2), 0xF1, 0xF1, BUF0, [0x45, 0x49, SP, SP]),
}


def holds(c):
    a, csr, put, get, buf, scr = EXPECT[c.fn]
    return (c.a, c.csr, c.put, c.get, c.buf, c.scr) == (a, csr, put, get, buf, scr)


def other_ref(c):
    return next(o for o in cases()["ref"] if o.num == c.num and o.row != c.row)


F = lambda *names: (lambda c: c.fn in names)          # noqa: E731
S1 = "1. The console input functions through $F37D"
RULES = [
    Rule("R-BC-CONST", S1, "CONST ($0B) answers A 0 with no key waiting and A $FF with one -- and TAKES that key out of "
         "the BIOS key buffer (GETPNT moves up to PUTPNT) into the DOS's own one-key hold: the next input call "
         "returns it. Nothing is echoed.", F("CONST0", "CONSTX"), holds),
    Rule("R-BC-HOLD", S1, "A held key comes first. CONIN after CONST returns CONST's 'X' though 'A' was put in the "
         "BIOS buffer for it; echoing 'X', CONIN takes the waiting 'A' into the hold too (the buffer is empty after "
         "it), and DIRIO with E $FF then returns that 'A' although the BIOS buffer is empty -- not A 0.",
         F("CONINA", "DIRIO0"), holds),
    Rule("R-BC-RAW", S1, "DIRIO ($06) with E $FF, $07 and $08 return the waiting key in A and take it from the "
         "buffer, with NO echo: the cursor and the screen stay.", F("DIRIOB", "IN07C", "IN08D"), holds),
    Rule("R-BC-ECHO", S1, "CONIN ($01) returns the key and echoes it through the console: 'E' is written at the "
         "cursor (column 1 -> 2). Return ($0D) echoes as a carriage return ALONE: the cursor goes to column 1 of "
         "the SAME row. CTRL+A ($01) is echoed raw -- no '^A': nothing appears and the cursor stays, but it is the "
         "graphic-character prefix, so the NEXT character printed shows as a graphic (BUFIN's 'H' -> $08).",
         F("CONINCR", "CONINCA", "CONINE"), holds),
    Rule("R-BC-BUFIN", S1, "BUFIN ($0A) at DE with 'HI' + Return and a maximum of 10: +1 the count 2, +2 'HI', then "
         "the $0D STORED after the text; the rest of the buffer untouched. It echoes 'HI' at the cursor and ends "
         "with a carriage return alone (column 1, the same row: no line feed). A $0D.", F("BUFINHI"), holds),
    Rule("R-BC-WORK", S1, "F and HL are working values; the two references give the same ones in every case "
         "(e.g. HL $3C00 / $3CFF after CONST, H 0 L $0D after BUFIN, L = the key after the others).",
         lambda c: True, lambda c: (lambda o: (c.f, c.hl) == (o.f, o.hl))(other_ref(c))),
]
