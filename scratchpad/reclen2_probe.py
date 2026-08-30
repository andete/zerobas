#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RECLEN2 — the `LEN=` domain is 1..256, and out of range is ERR 5, not ERR 2.

`oo_parse_reclen` required a POWER OF TWO in 1..256 "so records tile the
512-byte sector without straddling", and raised `Syntax error` otherwise. Both
halves are measured wrong:

  DOMAIN  the CF-3300 accepts LEN=1/100/128/255/256 -- any value in 1..256.
  FACE    LEN=0 / 257 / 512 answer `Illegal function call`, not `Syntax error`.

🎯 AND THE STRADDLE JUSTIFICATION IS FALSE FOR **BOTH** ENGINES. The reference
round-trips record 6 at LEN=100 -- bytes 500..599, across the boundary -- intact
(docs/spec-basic-put3.md §2). And so does THIS engine: with the power-of-two test
cut diagnostically, record 6 round-tripped here too. The validator was refusing
lengths its own FAT layer handles correctly.

🔴 THE ROW THAT UNBLOCKED IT NEEDED ONE `PUT`, NOT THREE. D-RECLEN sat blocked on
"zerobas's own straddling is unmeasured, because the rows need three PUTs and the
third hangs" (D-PUT3) -- but writing ONLY record 6 is a SINGLE put, and reading
it back is a GET. The blocker was a property of how the first rows were written,
not of the machine. [[a-coverage-row-whose-geometry-cannot-reach-the-case]]

⚠️ THE `FIELD`-WIDTH ROWS ARE CONTROLS, NOT SUBJECTS: `FIELD#1,256` is
`Illegal function call` on both sides (the width max is 255) and `FIELD#1,255` is
OK on both. An earlier note read `OPEN ... LEN=256` as refused when what was
refused was the FIELD behind it.

⚠️ ONE REFERENCE: Disk BASIC. A diskless VG-8020 cannot express these rows.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_fldwidth as F                                  # noqa: E402

OK = 'PRINT"[";"OK";"]"'
CASES = [
    # --- the DOMAIN: every value the reference accepts -----------------------
    ("m.open1",   "dsk", ['OPEN"TS.DAT"AS #1 LEN=1', OK]),
    ("m.open100", "dsk", ['OPEN"TS.DAT"AS #1 LEN=100', OK]),   # non-tiling
    ("m.open128", "dsk", ['OPEN"TS.DAT"AS #1 LEN=128', OK]),
    ("m.open255", "dsk", ['OPEN"TS.DAT"AS #1 LEN=255', OK]),   # non-tiling
    ("m.open256", "dsk", ['OPEN"TS.DAT"AS #1 LEN=256', OK]),
    # --- the FACE: out of range is ERR 5 -------------------------------------
    ("m.open0",   "dsk", ['OPEN"TS.DAT"AS #1 LEN=0', OK]),
    ("m.open257", "dsk", ['OPEN"TS.DAT"AS #1 LEN=257', OK]),
    ("m.open512", "dsk", ['OPEN"TS.DAT"AS #1 LEN=512', OK]),
    # --- 🔴 THE ROW A ROUND-TRIP PROBE CANNOT BE: ADJACENT RECORDS -----------
    # Writing record 6 and reading record 6 back proves NOTHING about the
    # offset, because PUT and GET share the arithmetic -- they agree on the same
    # wrong answer. `mul_reclen` really was wrong (a shift, i.e. *64 at r=100),
    # and the emulator rows said `SSS` anyway; tests/test_open_len.py caught it
    # by checking against an INDEPENDENTLY derived offset.
    # 🎯 THIS row is the emulator-side version of that check: at the correct
    # stride records 5 and 6 do not touch (400..499, 500..599), but at *64 they
    # OVERLAP (256..355, 320..419), so record 6's write would corrupt record 5.
    # Two PUTs, which stays under D-PUT3's third-PUT hang.
    ("x.adjacent", "dsk", ['OPEN"TS.DAT"AS #1 LEN=100', 'FIELD#1,100 AS A$',
                           'LSET A$=STRING$(100,"A"):PUT#1,5',
                           'LSET A$=STRING$(100,"B"):PUT#1,6', 'CLOSE',
                           'OPEN"TS.DAT"AS #1 LEN=100', 'FIELD#1,100 AS A$',
                           'GET#1,5:PRINT"[";LEFT$(A$,1);RIGHT$(A$,1);"]"']),

    # --- 🟢 CONTROLS: the FIELD width, which is a different rule -------------
    ("m.fld255",  "dsk", ['OPEN"TS.DAT"AS #1 LEN=256', 'FIELD#1,255 AS A$', OK]),
    ("m.fld256",  "dsk", ['OPEN"TS.DAT"AS #1 LEN=256', 'FIELD#1,256 AS A$', OK]),
    ("m.fldover", "dsk", ['OPEN"TS.DAT"AS #1 LEN=128', 'FIELD#1,256 AS A$', OK]),
]
F.CASES = CASES
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
res = {s: F.run_side(s, []) for s in sides}
w = max(len(l) for l, _, _ in CASES)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>24}" for s in sides))
diff = []
for label, _, _ in CASES:
    vals = [str(res[s].get(label)) for s in sides]
    same = len(set(vals)) == 1
    if not same:
        diff.append(label)
    print(f"{label:<{w}}  " + "  ".join(f"{v:>24}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF: {len(diff)}/{len(CASES)}  " + " ".join(diff))
