#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LISTCOMMA — a TRAILING SEPARATOR on a verb that takes a LIST.

D-OMITARG measured that `COLOR 15,4,` is `Missing operand` on both references and
was silently ACCEPTED here — a trailing comma on an OPTIONAL-argument verb. The
verbs that take a LIST (`DIM a,b`, `ERASE a,b`, `DEFINT a-b,c`, `READ a,b`,
`ON n GOTO l1,l2`) have never been asked the same question.

\U0001f3af IT IS A DIFFERENT SHAPE FROM THE TAIL SWEEP. `tailjunk_probe` appends a
bare NAME (`ZZ`) — chosen there precisely because no statement can legitimately
consume one — and covers `ERASE Q ZZ`. A trailing SEPARATOR is the opposite case:
the verb genuinely accepts more items, so "another one is coming" is a legal
parse state right up until the line ends. That is why COLOR got it wrong.

The witness is a marker variable set AFTER the statement, because "accepted
silently" and "raised" are not distinguishable from the error code alone when the
expected answer is itself an error:

    M = 5  ->  the statement was accepted and execution carried on
    M = 0  ->  it raised, and the trap reports which

\U0001f534 EXCEPT ON `l.ongoto`, WHERE M=0 MEANS SOMETHING ELSE. `ON 1 GOTO 60,`
BRANCHES to line 60, which prints and ENDs, so M is never set and ERR is 0 —
"branched" not "raised". The row is still a valid comparison (all three machines
do the same thing) but the legend above does not describe it, and a reader
scanning the M column would mis-read that one. Recorded rather than papered over.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_sides                                                # noqa: E402

SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
CASES = [
    ("ctl",     [],                  "DIM Z(5)",      "CONTROL: a clean list"),
    ("l.dim",   [],                  "DIM Z(5),",     "DIM with a trailing comma"),
    ("l.erase", ["15 DIM Z(5)"],     "ERASE Z,",      "ERASE with a trailing comma"),
    ("l.defint", [],                 "DEFINT A,",     "DEFINT with a trailing comma"),
    ("l.read",  ["15 DATA 1,2"],     "READ A,",       "READ with a trailing comma"),
    ("l.ongoto", [],                 "ON 1 GOTO 60,", "ON..GOTO with a trailing comma"),
    ("l.dim2",  [],                  "DIM Z(5),Y(5)", "CONTROL: a TWO-item list is legal"),
]


def main() -> int:
    out = {}
    for tag, extra, stmt, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ["10 ON ERROR GOTO 900"] + extra + ["20 M=0", f"30 {stmt}", "40 M=5",
                 '50 PRINT"ZQ";0;",";M;"QZ":END',
                 '60 PRINT"ZQ";0;",";M;"QZ":END',
                 '900 PRINT"ZQ";ERR;",";M;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*,\s*([0-9]+)\s*QZ', raw)
                 if not any(ch in "".join(g) for ch in '"$;')]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  f"ERR={row[s_][0]} M={row[s_][1]}") for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        print(f"  {tag:9s} {stmt:16s} vg={f['vg8020']:15s} cf={f['cf3300']:15s} "
              f"zb={f['zb']:15s}{mark}", flush=True)

    for ctl in ("ctl", "l.dim2"):
        r = out.get(ctl, {})
        if any(r.get(s_) != ("0", "5") for s_ in SIDES):
            print(f"\n\U0001f534 CONTROL {ctl} DID NOT READ ERR 0 / M=5 ({r}) -- a "
                  f"legal list is not being accepted, and no row above means "
                  f"anything.")
            return 2
    dis = [t for t in out
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print("=== M=5 accepted-and-carried-on · M=0 raised ===")
    for t in out:
        print(f"   {t:9s} vg {out[t]['vg8020']}   cf {out[t]['cf3300']}   "
              f"zb {out[t]['zb']}")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
