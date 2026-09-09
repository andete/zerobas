#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-BARERUN — does a bare `RUN` inside a running program re-enter the loop NESTED?

`basic/cload.asm`'s `dr_stored` is the one arm D-RUNTAIL did not convert:
`jp run_prog` where every sibling uses `jp run_prog_top`. The 0-byte fix has been
written, shipped and BACKED OUT once, and the item has stood ⛔ BLOCKED since
2026-08-22 with the reason *"needs a fixture"* -- because a bare `RUN` CLEARS
VARIABLES, so the program restarts forever on the references too and there is no
value to read back.

\U0001f3af THE FIXTURE THAT WORKS IS SELF-CONTROLLING: MAKE THE CORRECT BEHAVIOUR
VISIBLE. An endless `PRINT "X";` before the `RUN` means the reference's "restarts
forever, silently" shows up as a SCREEN FULL OF X, while the defect --
`run_prog` nested inside the enclosing loop, overwriting CURLINE until the return
path walks off into garbage -- shows up as an ERROR MESSAGE among them. One row
separates "hangs correctly" from "prints a bogus error and stops", which is
exactly what the item said the hard part was.

⚠️ AND THE `<NO OUTPUT>` TRAP IS WHY `c.goto` EXISTS. A blank screen means "the
program never printed" and "the harness never captured" equally well. `c.goto` is
the SAME infinite loop reached by `GOTO` instead of `RUN`: it must fill the
screen with X and show no error on every machine. If it does not, nothing in this
run is readable [[an-unnamed-outcome-reads-as-no-outcome]].
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
    ("s.bare", ['10 PRINT "X";', "20 RUN"],
     "THE SUBJECT: a bare RUN inside a running program"),
    ("c.goto", ['10 PRINT "X";', "20 GOTO 10"],
     "CONTROL: the same endless loop reached by GOTO -- must be X's, no error"),
]

# Any of these words on the screen means the machine STOPPED with a message.
ERRW = re.compile(r"(error|Error|ERROR|memory|Memory|overflow|Overflow)")


def main() -> int:
    out = {}
    for lab, prog, _why in CASES:
        out[lab] = {}
        for side, c in SIDES.items():
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + prog + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=6.0,
                run_gap=30.0, cap_gap=4.0, timeout=420.0)[0] or "")
            xs = raw.count("X")
            err = ERRW.search(raw)
            out[lab][side] = (xs, err.group(0) if err else None)
            print(f"  ran {lab:7s} {side:7s} -> X*{xs:<4d} "
                  f"{'ERROR: ' + err.group(0) if err else 'no error word'}",
                  flush=True)

    print()
    w = max(len(l) for l, _, _ in CASES)
    for lab, _p, why in CASES:
        cells = "  ".join(f"{s}={out[lab][s][0]:>4d}"
                          f"{'/' + out[lab][s][1] if out[lab][s][1] else ''}"
                          for s in SIDES)
        print(f"  {lab:<{w}}  {cells}\n      {why}")

    ctl = out["c.goto"]
    if any(v[0] < 20 or v[1] for v in ctl.values()):
        print("\n  \U0001f534 THE CONTROL DID NOT RUN CLEANLY on every machine -- an "
              "endless GOTO loop must fill the screen with X and raise nothing. "
              "Nothing in this run is readable.")
        return 2

    sub = out["s.bare"]
    print()
    refs_err = [s for s in ("vg8020", "cf3300") if sub[s][1]]
    if refs_err:
        print(f"  ⚠️ A REFERENCE RAISED on the subject ({refs_err}) -- then the "
              f"nesting is not the story and the filed reading is wrong.")
        return 1
    if sub["zb"][1]:
        print(f"  \U0001f534 DIVERGENCE CONFIRMED: both references loop silently on a bare "
              f"RUN; zerobas stops with {sub['zb'][1]!r}. That is `dr_stored`'s "
              f"`jp run_prog` entering the loop NESTED -- and `jp run_prog_top` is "
              f"the 0-byte fix the item has been holding.")
    else:
        print("  \U0001f7e2 NO DIVERGENCE: zerobas loops silently too. Either the arm was "
              "converted since, or the nesting does not reach a visible fault on "
              "this shape -- read before believing the filed defect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
