#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-OPEN2 — TWO DISK CHANNELS cannot be open at once; the refusal is `Syntax error`.

Found 2026-08-30 while trying to answer a D-PUT3 question (is the third-PUT
counter per-channel or global?). The two-channel fixture kept failing; three
rounds of blaming the fixture were wrong -- it is the machine.

🔴 THE FIRST WRITE-UP OF THIS SAID "only ONE file may be open at a time" AND THAT
WAS AN OVER-CLAIM. Multi-channel WORKS: device+device, device+disk and
disk+device are all fine. Every row in the first pass opened two DISK channels --
`A.TXT` and `B.TXT` are disk files too -- so no device channel was ever in the
comparison, and "every shape" was one shape. It is TWO DISK CHANNELS.

🎯 THE CEILING IS HONOURED; CONCURRENCY IS NOT. `a.ch2only` opens channel #2 on
its own after `MAXFILES=2` and succeeds on both sides -- so the table DOES raise
the ceiling and channel 2 is reachable. What fails is having TWO channels open at
the same time, and that is the whole finding.

Every candidate cause is separated by its own row rather than argued:
  channel NUMBER      a.ch2only / c.2then1
  FILENAME            d.ts2ch1
  file MODE           t.seq2 (two sequential), t.seq1rnd2, t.rnd1seq2
  `LEN=`              g.nolen2
  the MAXFILES VALUE  h.mf3
None of them is it. The reference accepts all of them, and even diagnoses the
same-file case properly (`File already open`) where zerobas says `Syntax error`
-- so the FACE is wrong as well as the behaviour.

⚠️ ONE REFERENCE: Disk BASIC. A diskless VG-8020 cannot express these rows.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_fldwidth as F                                  # noqa: E402

OK = 'PRINT"[";"OK";"]"'
M = 'MAXFILES=2'
R1 = 'OPEN"TS.DAT"AS #1 LEN=128'
LPT1 = 'OPEN"LPT:"FOR OUTPUT AS #1'

CASES = [
    # --- 🟢 CONTROLS: one channel, every shape, must pass on both ------------
    ("a.ch2only",  "dsk", [M, 'OPEN"TS.DAT"AS #2 LEN=128', OK]),
    ("d.ts2ch1",   "dsk", [M, 'OPEN"TS2.DAT"AS #1 LEN=128', OK]),
    ("t.seq1",     "dsk", [M, 'OPEN"A.TXT"FOR OUTPUT AS #1', OK]),
    # --- 🔴 TWO CHANNELS AT ONCE, in every shape -----------------------------
    ("b.1then2",   "dsk", [M, R1, 'OPEN"TS2.DAT"AS #2 LEN=128', OK]),
    ("c.2then1",   "dsk", [M, 'OPEN"TS.DAT"AS #2 LEN=128',
                              'OPEN"TS2.DAT"AS #1 LEN=128', OK]),
    ("g.nolen2",   "dsk", [M, R1, 'OPEN"TS2.DAT"AS #2', OK]),
    ("h.mf3",      "dsk", ['MAXFILES=3', R1, 'OPEN"TS2.DAT"AS #2 LEN=128', OK]),
    ("t.seq2",     "dsk", [M, 'OPEN"A.TXT"FOR OUTPUT AS #1',
                              'OPEN"B.TXT"FOR OUTPUT AS #2', OK]),
    ("t.seq1rnd2", "dsk", [M, 'OPEN"A.TXT"FOR OUTPUT AS #1',
                              'OPEN"TS.DAT"AS #2 LEN=128', OK]),
    ("t.rnd1seq2", "dsk", [M, R1, 'OPEN"A.TXT"FOR OUTPUT AS #2', OK]),
    ("t.seqwrite", "dsk", [M, 'OPEN"A.TXT"FOR OUTPUT AS #1',
                              'OPEN"B.TXT"FOR OUTPUT AS #2',
                              'PRINT#1,"x"', 'PRINT#2,"y"', OK]),
    # --- 🎯 THE FACE: the reference DIAGNOSES this one, zerobas does not ------
    ("e.same2",    "dsk", [M, R1, 'OPEN"TS.DAT"AS #2 LEN=128', OK]),
    # --- 🟢 and the row that says the fixture is sound without MAXFILES ------
    ("n.nomaxf",   "dsk", [R1, 'OPEN"TS2.DAT"AS #2 LEN=128', OK]),

    # === 🔴 THE ROWS THAT NARROWED THIS, AND REFUTED THE FIRST WRITE-UP ======
    # The first pass concluded "only ONE file may be open at a time". WRONG:
    # every row above opens two DISK channels -- `A.TXT` and `B.TXT` are disk
    # files too -- so a DEVICE channel was never in the comparison. It is
    # specifically TWO DISK CHANNELS that fail.
    ("v.1dev",     "dsk", [M, LPT1, OK]),                       # the control
    ("v.2dev",     "dsk", [M, LPT1, 'OPEN"CRT:"FOR OUTPUT AS #2', OK]),
    ("v.dev1dsk2", "dsk", [M, LPT1, 'OPEN"TS.DAT"AS #2 LEN=128', OK]),
    ("v.dsk1dev2", "dsk", [M, R1, 'OPEN"LPT:"FOR OUTPUT AS #2', OK]),
    # ⚠️ AND THE CONTROL THAT WAS MISSING THE FIRST TIME. `OPEN"LPT:"AS #1`
    # (a device with no FOR clause, i.e. RANDOM mode) is `Syntax error` here and
    # OK on the reference -- a SEPARATE divergence, and it voided a whole
    # discriminator run by failing as the baseline of a comparison.
    ("v.devbare",  "dsk", [M, 'OPEN"LPT:"AS #1', OK]),
]

F.CASES = CASES
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
res = {s: F.run_side(s, []) for s in sides}
w = max(len(l) for l, _, _ in CASES)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides))
diff = []
for label, _, _ in CASES:
    vals = [str(res[s].get(label)) for s in sides]
    same = len(set(vals)) == 1
    if not same:
        diff.append(label)
    print(f"{label:<{w}}  " + "  ".join(f"{v:>22}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF: {len(diff)}/{len(CASES)}  " + " ".join(diff))
print("🎯 a.ch2only / d.ts2ch1 / t.seq1 are the CONTROLS -- one channel, every"
      " shape,\n   green on both. n.nomaxf is `Bad file number` on both (the"
      " default ceiling is 1),\n   which is what says MAXFILES=2 is doing its"
      " job and the fixture is sound.")
