#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PUTCOST — what a random-record `PUT` actually COSTS, on the machine's own clock.

The `PUT` item says what is owed in one sentence: *"the per-`PUT` cost, measured
rather than bounded, against the reference's."* D-PUT3SLOW bounded it at
**>2.5 s and <5 s** by finding which harness `step` a row survives — which
measures the HARNESS, not the machine, and cannot separate a fixed per-statement
overhead from a per-`PUT` one.

🎯 SO ASK THE MACHINE. `TIME` is the VBlank counter both references and this
ROM maintain, so `T=TIME : <N PUTs> : PRINT TIME-T` is a reading in the guest's
own ticks — 50 Hz on these PAL machines — taken identically on every side and
immune to how long the harness waits before typing the next line.

    N = 1, 2, 4, 8       the slope is the per-PUT cost; the intercept is the
                         fixed part, and separating them is the whole point
    c.none               🔴 CONTROL: the SAME loop with the PUT removed. Without
                         it the reading is "PUT plus FOR/NEXT plus TIME's own
                         granularity" and no row says which
    c.tick               🔴 CONTROL: `FOR I=1 TO 1000:NEXT` — proves TIME
                         advances at all and that the two machines' ticks are
                         comparable before any PUT figure is believed

⚠️ ONE REFERENCE. `PUT` is Disk BASIC; a diskless VG-8020 cannot express it, so
the CF-3300 is the only oracle and the VG-8020 is not asked.

⚠️ A LONG `step`. Each row must COMPLETE before the harness types the next line —
the whole finding behind D-PUT3SLOW is that it did not — so this runs at 60 s,
where the item's own ladder showed every row completing at 20.
"""
from __future__ import annotations

import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402
import basic_probe_fldwidth as F                                  # noqa: E402

STEP = 60.0
TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")

OPEN3 = ['CLEAR 2000',
         'OPEN"TS.DAT"AS #1 LEN=128',
         'FIELD#1,128 AS A$',
         'LSET A$=STRING$(128,"A")']


def puts(n):
    return OPEN3 + [f'T=TIME:FOR I=1 TO {n}:PUT#1,I:NEXT:PRINT"[";TIME-T;"]"']


def loops(n):
    """The same loop with the PUT taken out — the row that says how much of the
    figure is FOR/NEXT rather than the write."""
    return OPEN3 + [f'T=TIME:FOR I=1 TO {n}:NEXT:PRINT"[";TIME-T;"]"']


# 🎯 THE COMPONENT ROWS, ADDED AFTER THE FIRST RUN INVERTED THE QUESTION.
# The slope said a PUT costs ~1.7 ticks on zb against ~2.1 on the CF-3300 -- so
# the write is NOT what needs >2.5 s, and the >2.5 s bound D-PUT3SLOW measured
# has to live in the fixed part. These time each statement of the preamble on
# its own, so "PUT is slow" can be replaced by the name of whatever is.
FIXED = [
    ("f.open",  ['CLEAR 2000', 'T=TIME:OPEN"TS.DAT"AS #1 LEN=128:PRINT"[";TIME-T;"]"']),
    ("f.field", ['CLEAR 2000', 'OPEN"TS.DAT"AS #1 LEN=128',
                 'T=TIME:FIELD#1,128 AS A$:PRINT"[";TIME-T;"]"']),
    ("f.lset",  OPEN3[:3] + ['T=TIME:LSET A$=STRING$(128,"A"):PRINT"[";TIME-T;"]"']),
    ("f.close", OPEN3 + ['T=TIME:CLOSE:PRINT"[";TIME-T;"]"']),
    ("f.lof",   OPEN3 + ['PUT#1,1', 'T=TIME:L=LOF(1):PRINT"[";TIME-T;"]"']),
    ("f.dskf",  OPEN3 + ['PUT#1,1', 'T=TIME:D=DSKF(0):PRINT"[";TIME-T;"]"']),
    # 🎯 EXTENSION, WHICH THE ROWS ABOVE NEVER TOUCH. p.1..p.8 write records
    # 1..8 of a file that already exists in the fixture, so `frnd_locate` never
    # allocates. A PUT to a HIGH record has to extend the chain -- and that is
    # the only part of the write path whose cost can GROW with the file. If the
    # >2.5 s D-PUT3SLOW bounded is anywhere, it is here.
    ("x.far50", OPEN3 + ['T=TIME:PUT#1,50:PRINT"[";TIME-T;"]"']),
    ("x.far200", OPEN3 + ['T=TIME:PUT#1,200:PRINT"[";TIME-T;"]"']),
    # and the SECOND write to the same far record, with the chain already there:
    # the difference between this and x.far200 is the allocation alone.
    ("x.far2nd", OPEN3 + ['PUT#1,200',
                          'T=TIME:PUT#1,200:PRINT"[";TIME-T;"]"']),
    # \U0001f534 THE SHAPE THAT ACTUALLY FAILED, TIMED. Every row above is fast on
    # both machines, so whatever needs >2.5 s is not the write. The programs
    # D-PUT3SLOW measured were `write_three`: THREE `LSET A$=STRING$(n,..)`
    # temps against a `CLEAR 1000` pool. reclen_probe's own comment already
    # says the failure "needed all THREE" temps and was "the STRING POOL, not
    # the records" -- so time that exact sequence, and time it again with twice
    # the pool. A gap between these two names GARBAGE COLLECTION.
    ("g.three1k", ['CLEAR 1000', 'OPEN"TS.DAT"AS #1 LEN=128', 'FIELD#1,128 AS A$',
                   'T=TIME:LSET A$=STRING$(128,"A"):PUT#1,5:'
                   'LSET A$=STRING$(128,"B"):PUT#1,6:'
                   'LSET A$=STRING$(128,"C"):PUT#1,7:PRINT"[";TIME-T;"]"']),
    ("g.three4k", ['CLEAR 4000', 'OPEN"TS.DAT"AS #1 LEN=128', 'FIELD#1,128 AS A$',
                   'T=TIME:LSET A$=STRING$(128,"A"):PUT#1,5:'
                   'LSET A$=STRING$(128,"B"):PUT#1,6:'
                   'LSET A$=STRING$(128,"C"):PUT#1,7:PRINT"[";TIME-T;"]"']),
    # the same three temps with NO PUT at all -- separates the pool from the write
    ("g.str1k",   ['CLEAR 1000', 'OPEN"TS.DAT"AS #1 LEN=128', 'FIELD#1,128 AS A$',
                   'T=TIME:LSET A$=STRING$(128,"A"):'
                   'LSET A$=STRING$(128,"B"):'
                   'LSET A$=STRING$(128,"C"):PRINT"[";TIME-T;"]"']),
]

CASES = [
    ("c.tick",  ['T=TIME:FOR I=1 TO 1000:NEXT:PRINT"[";TIME-T;"]"']),
    ("c.none1", loops(1)),
    ("c.none8", loops(8)),
    ("p.1",     puts(1)),
    ("p.2",     puts(2)),
    ("p.4",     puts(4)),
    ("p.8",     puts(8)),
] + FIXED


def run(side, lines):
    cfg = F.SIDES[side]
    kw = {}
    if cfg["diska"]:
        dsk = probe_tmp.tmp(f"putcost_{side}.dsk")
        shutil.copy(TEST_DSK, dsk)
        kw["diska"] = dsk
    body = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(lines)]
    caps = omsx_repl.run_cases(
        cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
        batch=False, reset=(), boot=cfg["boot"], step=STEP, timeout=600.0, **kw)
    return F.bracket(caps[0])


def ticks(cell):
    m = re.fullmatch(r"<?\[?\s*(-?\d+)\s*\]?>?", str(cell).strip())
    return int(m.group(1)) if m else None


def main():
    sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
    res = {}
    w = max(len(l) for l, _ in CASES)
    print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>16}" for s in sides)
          + "   ticks (1/50 s)")
    for label, lines in CASES:
        row = {s: run(s, lines) for s in sides}
        res[label] = row
        print(f"{label:<{w}}  " + "  ".join(f"{str(row[s]):>16}" for s in sides))

    print()
    blind = [f"{lab}/{s}" for lab, r in res.items() for s in sides
             if ticks(r[s]) is None]
    if blind:
        # 🔴 A CELL THAT DID NOT PARSE IS THE INSTRUMENT, NOT A COST. Refusing
        # here is what stops a missing row being read as "infinitely slow".
        print(f"🔴 {len(blind)} cell(s) did not read as a number: {blind}")
        print("   That is the INSTRUMENT (a row that had not finished, or a "
              "machine with no disk), not a measurement. Run refused.")
        return 2

    print("per-PUT cost, from the SLOPE (p.8 - p.1) / 7 — the intercept is the")
    print("fixed OPEN/FIELD/LSET part and is deliberately not in it:")
    for s in sides:
        d = (ticks(res["p.8"][s]) - ticks(res["p.1"][s])) / 7.0
        loop = (ticks(res["c.none8"][s]) - ticks(res["c.none1"][s])) / 7.0
        print(f"  {s:<8} {d:7.2f} ticks/PUT = {d / 50.0:6.3f} s"
              f"   (bare FOR/NEXT: {loop:.2f} ticks — subtract it)")
    a, b = (ticks(res["p.8"][s]) - ticks(res["p.1"][s]) for s in sides[:2]) \
        if len(sides) >= 2 else (None, None)
    if a and b:
        print(f"\n  ratio {sides[1]}/{sides[0]} = {b / a:.2f}x per PUT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
