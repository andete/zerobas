#!/usr/bin/env python3
r"""D-PUT1AFTER — after ONE `PUT`, WHICH operations die?

D-PUT3CONSUME (2026-09-02) found that `DSKF(0)` after a SINGLE `PUT` dies on
zerobas, and dies INSIDE `DSKF` (the row prints `[` and stops), while `LOF(1)`
after two PUTs is fine. So one write already breaks something, and the break is
narrow enough that LOF steps over it.

🎯 THE QUESTION THIS ANSWERS: is the fault specific to `fat_count_free` (which
`DSKF` is the only caller of), or general to the SUB-ROM CALL PATH that `PUT`
and `DSKF` both use? One row per operation, every one after exactly ONE `PUT`,
every one printing a marker so a blank means "died here" and a marker means
"survived".

🔴 PREDICTIONS, BEFORE THE RUN:
  P1  `DSKF` dies. (Re-measurement of the known row, as the arm's own control:
      if THIS goes green the fixture changed and nothing else here is readable.)
  P2  `LOF` survives -- known from d.lof1/d.lof2.
  P3  The interesting one. If EOF/LOC/GET/CLOSE also die, the fault is the
      shared sub-ROM path and `DSKF` is merely its first victim. If DSKF is the
      ONLY casualty, it is `fat_count_free`'s own body -- a much smaller haystack
      (it rides its result back over FAT_WRTMP2 rather than a Cy contract, which
      is the one thing about it that is unusual).

⚠️ Every row is ONE channel and no MAXFILES -- both fixture faults D-PUT3 names.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_fldwidth as F                                  # noqa: E402

OPEN = ['CLEAR 1000', 'OPEN"TS.DAT"AS #1 LEN=128', 'FIELD#1,128 AS A$']
PUT1 = ['PUT#1,1']
OK = 'PRINT"[OK]"'

CASES = [
    # --- 🟢 CONTROLS: the same operations with NO put in front --------------
    ("n.dskf",  "dsk", OPEN + ['X=DSKF(0)', OK]),
    ("n.lof",   "dsk", OPEN + ['X=LOF(1)', OK]),
    ("n.loc",   "dsk", OPEN + ['X=LOC(1)', OK]),
    ("n.eof",   "dsk", OPEN + ['X=EOF(1)', OK]),
    ("n.close", "dsk", OPEN + ['CLOSE', OK]),
    ("n.get",   "dsk", OPEN + ['GET#1,1', OK]),
    # --- the same seven, each after EXACTLY ONE PUT -------------------------
    ("a.dskf",  "dsk", OPEN + PUT1 + ['X=DSKF(0)', OK]),
    ("a.lof",   "dsk", OPEN + PUT1 + ['X=LOF(1)', OK]),
    ("a.loc",   "dsk", OPEN + PUT1 + ['X=LOC(1)', OK]),
    ("a.eof",   "dsk", OPEN + PUT1 + ['X=EOF(1)', OK]),
    ("a.close", "dsk", OPEN + PUT1 + ['CLOSE', OK]),
    ("a.get",   "dsk", OPEN + PUT1 + ['GET#1,1', OK]),
    ("a.put",   "dsk", OPEN + PUT1 + ['PUT#1,1', OK]),
    # --- 🎯 ONE PROGRAM, BOTH SIDES OF THE PUT. The strongest form: if the
    # --- first DSKF prints and the second does not, the PUT is what changed.
    ("b.both",  "dsk", OPEN + ['X=DSKF(0)', 'PRINT"[A]";',
                               'PUT#1,1', 'Y=DSKF(0)', 'PRINT"[B]"']),
    # --- does CLOSE (which D-PUT3 says does NOT reset the 3-PUT counter)
    # --- reset THIS one? A different question from the same clue.
    ("b.reopen","dsk", OPEN + PUT1 + ['CLOSE', 'OPEN"TS.DAT"AS #1 LEN=128',
                                      'X=DSKF(0)', OK]),
]

F.CASES = CASES
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
res = {s: F.run_side(s, []) for s in sides}
w = max(len(l) for l, _, _ in CASES)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>24}" for s in sides))
print("-" * (w + 2 + 26 * len(sides)))
for label, _, _ in CASES:
    print(f"{label:<{w}}  " + "  ".join(f"{str(res[s].get(label)):>24}" for s in sides))
