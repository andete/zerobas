#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The closing demo for 2026-08-30's SECOND half — real MSX BASIC, both machines.

The first demo (scratchpad/valstr_demo.py) covered the VAL/STR$ arc. Everything
below shipped after it: D-ARGOPEN, D-DEVBARE and D-RECLEN2's face.

The BEFORE column is a RECORDED reading, not a guess -- each row was measured on
this tree before its fix landed.

⚠️ ONE REFERENCE for the disk rows: a diskless VG-8020 cannot express them, and
this arc retired a filed "divergence" that was exactly that mistake (D-FIELDCH).
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_fldwidth as F                                  # noqa: E402

OK = 'PRINT"[";"OK";"]"'
# label, what it shows, lines, the RECORDED pre-fix zb reading
CASES = [
    ("dev.bare",  "D-DEVBARE: a device channel needs no FOR clause",
     ['OPEN"CRT:"AS #1', OK], "Syntax error"),
    ("dev.write", "...and the channel then WORKS",
     ['OPEN"CRT:"AS #1', 'PRINT#1,"x"', OK], "Syntax error"),
    ("dev.len",   "🟢 ...while LEN= on a device stays refused, as on the reference",
     ['OPEN"CRT:"AS #1 LEN=128', OK], "Syntax error"),
    ("len.257",   "D-RECLEN2: an out-of-range LEN= is ERR 5, not ERR 2",
     ['OPEN"TS.DAT"AS #1 LEN=257', OK], "Syntax error"),
    ("len.0",     "...and so is LEN=0",
     ['OPEN"TS.DAT"AS #1 LEN=0', OK], "Syntax error"),
    ("len.128",   "🟢 ...while a legal length still opens",
     ['OPEN"TS.DAT"AS #1 LEN=128', OK], "same"),
    ("arg.left",  "D-ARGOPEN: LEFT$ through the shared prologue",
     ['A$="ABCDE"', 'PRINT"[";LEFT$(A$,2);"]"'], "same"),
    ("arg.mid",   "...MID$, the site the byte-level ranking could not see",
     ['A$="ABCDE"', 'PRINT"[";MID$(A$,2,3);"]"'], "same"),
    ("arg.bad",   "...and a malformed call still declines at the VERB's depth",
     ['PRINT LEFT$("AB")'], "same"),
    ("arg.tm",    "...a non-string argument is still Type mismatch",
     ['PRINT LEFT$(5,2)'], "same"),
]
F.CASES = [(l, "dsk", p) for l, _, p, _ in CASES]
res = {s: F.run_side(s, []) for s in ("cf3300", "zb")}
same = agree = 0
w = max(len(l) for l, _, _, _ in CASES)
for label, what, _, before in CASES:
    cf, zb = str(res["cf3300"].get(label)), str(res["zb"].get(label))
    ok = cf == zb
    same += ok
    print(f"  {label:<{w}}  {'zb=same' if ok else 'zb=DIFF':8s}  "
          f"before={before!r:16s} cf={cf!r:26s} zb={zb!r:26s}  [{what}]")
print(f"\n  {same} of {len(CASES)} zerobas readings match the CF-3300")
