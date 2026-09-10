#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-NMFAIL — the no-disk disposition of NAME/KILL/FILES, on the machine.

`nm_fail` is one of the four D-DUPOBS2 canonicals no behavioural gate reaches.
It is the `fat_mount` failure exit of NAME (`basic/files.asm:1799`) and it is a
bare `jp load_error`. `basic/files.asm` says out loud what is missing:

    "The mount keeps load_error (the quarantined no-disk / mount / I-O class,
     UNMEASURED ON THE REFERENCE)"

\U0001f3af SO ONE RUN DISCHARGES TWO THINGS AT ONCE: a site nothing exercises, and
a written "unmeasured" that has been standing since D-DKNAME. The lever needs no
fixture -- it is the ABSENCE of one. A machine with a drive and NO image mounted
is exactly the state `fat_mount` fails in.

⚠️ THE VG-8020 IS NOT A SIDE HERE and that is the point of `probe_sides`: it has
no drive at all, so `NAME` on it is a different statement, not a no-disk NAME.
The oracle is the CF-3300 with an empty drive. Scoring the VG here is the exact
mistake D-BAREFORM published five times.

Each row traps with ON ERROR so the reading is the ERROR NUMBER and the LINE --
that is what says whether the disposition is trappable at all, which is the half
`load_error` has historically got wrong (D-DSKMSG, R-DK1/R-DK2).
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                              # noqa: E402
import probe_sides                                            # noqa: E402

STMTS = {
    "n.name":   'NAME "A.BAS" AS "B.BAS"',
    "k.kill":   'KILL "A.BAS"',
    "f.files":  'FILES',
    "l.load":   'LOAD "A.BAS"',          # the sibling that already uses load_error
    "s.save":   'SAVE "A.BAS"',
}


# \U0001f3af THE FENCE CARRIES ITS OWN ROW NAME, and that is not decoration.
# These programs `CLS` before printing, so the `RUN` echo an anchored readout
# would key on is GONE -- there is no anchor row on the glass at all. A case that
# fails to print therefore leaves the PREVIOUS case's fence sitting there looking
# like an answer, which is how the first cut of this probe reported an identical
# `[NO ERROR]` on all five rows. A self-identifying fence makes a stale read
# NAME ITSELF, and the probe refuses instead of adjudicating
# [[an-unnamed-outcome-reads-as-no-outcome]].
def prog(tag, stmt):
    return ["10 ON ERROR GOTO 900",
            f"20 {stmt}",
            f'30 CLS:PRINT"[{tag} NO ERROR]":END',
            f'900 CLS:PRINT"[{tag} ERR";ERR;"AT";ERL;"]":END',
            "RUN"]


CASES = [(k, prog(k, v)) for k, v in STMTS.items()]


def fence(cap):
    """The `[...]` fence the program prints, from a flat 40-column dump.

    \\u26a0\\ufe0f ANCHORED ON THE FENCE, NOT ON A SEARCH OF THE WHOLE SCREEN --
    the batch-mode readout that scans the entire dump reads the PREVIOUS case's
    text, which cost D-FNNEST three withdrawn readings on 2026-09-10.
    """
    c = cap or ""
    if not c:
        return "<NO DUMP>"
    # \U0001f534 `c.rfind("[")` WAS THE FIRST CUT AND IT IS THE WHOLE-SCREEN
    # SEARCH THIS DOCSTRING WARNS ABOUT -- written the same day. A case that
    # never prints its own fence then reports the PREVIOUS case's, and five rows
    # came back with an identical `[NO ERROR]` that belonged to row 1.
    tail = c
    i = tail.find("[")
    j = tail.find("]", i + 1)
    if i < 0 or j < 0:
        return "<NO FENCE AFTER RUN: " + tail.strip()[:30] + ">"
    return " ".join(tail[i:j + 1].split())


def main() -> int:
    SIDES = probe_sides.sides("cf3300", "zb")     # NO vg8020: it has no drive
    out = {}
    for name, m in SIDES.items():
        out[name] = omsx_repl.run_cases(m["machine"], CASES, batch=True,
                                        boot=m["boot"], reset=m["reset"],
                                        diska=probe_sides.diska(name, None))
    print("D-NMFAIL: a drive with NO image mounted; ON ERROR reports "
          "ERR and ERL\n")
    diff, stale = [], []
    for i, (nm, _) in enumerate(CASES):
        vals = {s: fence(out[s][i]) for s in SIDES}
        for s, v in vals.items():
            if v.startswith("[") and not v.startswith("[" + nm + " "):
                stale.append(f"{nm}/{s} read {v!r}")
        tag = "ok  " if len(set(vals.values())) == 1 else "DIFF"
        if tag == "DIFF":
            diff.append(nm)
        cells = "  ".join(f"{s}={vals[s]:24}" for s in SIDES)
        print(f"  {tag} {nm:8} {STMTS[nm]:24} {cells}")
    if stale:
        print(f"\n\U0001f534 {len(stale)} READING(S) BELONG TO ANOTHER ROW -- "
              "the case did not print its own fence, so NOTHING above is "
              "adjudicated:")
        for x in stale:
            print(f"     {x}")
        return 2
    print(f"\n=== {len(diff)} row(s) where zerobas differs from the "
          f"CF-3300: {diff or 'none'} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
