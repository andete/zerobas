#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FLOWTAIL — the tail sweep covers 20 verbs and NOT ONE of them branches.

From auditing `ex_gosub`, the review-tier entry that flags its own limit:
"NOT reviewed line-by-line ... Recorded as covered, not as audited."

`scratchpad/tailjunk_probe.py` sweeps a trailing `ZZ` across POKE, VPOKE, OUT,
LOCATE, COLOR, SCREEN, WIDTH, SOUND, CLS, TRON, TROFF, BEEP, MOTOR, KEY, CLOSE,
CLEAR, RESTORE, DEFINT, MAXFILES, TIME, PSET, PRESET, ERASE and SWAP. **Every one
of them falls through to the next statement.** GOTO, GOSUB, RETURN and ON..GOSUB
do not, and none of them is in that list -- so the class that produced D-MAXFTAIL,
D-DEFCORNER, D-FMTTAIL and D-OMITARG has never been asked of a branching verb.

\U0001f3af AND A BRANCHING VERB MAKES THE QUESTION SHARPER, NOT WEAKER. The tail of
`GOSUB 100 ZZ` sits exactly where RETURN resumes, so "rejected while parsing" and
"branched, then failed on the way back" BOTH end in ERR 2 and an error code alone
cannot tell them apart. Every row therefore carries a witness variable the
subroutine sets:

    A = 0  ->  the statement was refused BEFORE branching
    A = 7  ->  it branched, ran the target, and failed afterwards (or not at all)

That is the same lesson as `i.byte` and the D-RAWVAL prime-and-PEEK rows: witness
the EFFECT, because the error code is the half both stories share.
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
TAIL = '40 PRINT"ZQ";0;",";A;"QZ":END'
TRAP = '900 PRINT"ZQ";ERR;",";A;"QZ":END'
CASES = [
    ("ctl",    ["20 A=0", "30 GOSUB 100", TAIL, "100 A=7:RETURN", TRAP],
     "CONTROL: a clean GOSUB -- must read ERR 0 / A=7"),
    ("g.tail", ["20 A=0", "30 GOSUB 100 ZZ", TAIL, "100 A=7:RETURN", TRAP],
     "GOSUB <line> ZZ"),
    ("t.tail", ["20 A=0", "30 GOTO 100 ZZ", TAIL, "100 A=7:GOTO 40", TRAP],
     "GOTO <line> ZZ"),
    ("r.tail", ["20 A=0", "30 GOSUB 100", TAIL, "100 A=7:RETURN ZZ", TRAP],
     "RETURN ZZ -- RETURN <line> is a real form (D-RETLN)"),
    ("o.tail", ["20 A=0", "30 ON 1 GOSUB 100 ZZ", TAIL, "100 A=7:RETURN", TRAP],
     "ON n GOSUB <line> ZZ"),
    ("g.comma", ["20 A=0", "30 GOSUB 100,", TAIL, "100 A=7:RETURN", TRAP],
     "a trailing SEPARATOR rather than an operand"),
    # --- WHICH mechanism? Two fit every row above, and they differ on ONE case.
    # The reference accepts `GOSUB 100 ZZ` and never executes the ZZ, so either
    #   (a) GOSUB skips to the END OF THE STATEMENT before saving the resume
    #       point -- then a `:`-separated statement after the junk STILL RUNS, or
    #   (b) it skips to the end of the LINE -- then that statement is skipped too.
    # A=17 says (a), A=7 says (b). Naming both before picking one, because a fix
    # written against the rows above alone could implement either
    # [[two-rules-that-coincide-on-every-row-you-have]].
    ("ctl.col", ["20 A=0", "30 GOSUB 100:A=A+10", TAIL, "100 A=7:RETURN", TRAP],
     "CONTROL: ordinary mid-line resume -- A must reach 17"),
    ("g.col",   ["20 A=0", "30 GOSUB 100 ZZ:A=A+10", TAIL, "100 A=7:RETURN", TRAP],
     "17 = resumed after the STATEMENT, 7 = after the LINE"),
]


def main() -> int:
    out = {}
    for tag, body, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ["10 ON ERROR GOTO 900"] + body
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*,\s*([0-9]+)\s*QZ', raw)
                 if not any(ch in "".join(g) for ch in '"$;')]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  f"ERR={row[s_][0]} A={row[s_][1]}") for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        stmt = next(l for l in body if l.startswith("30 "))[3:]
        print(f"  {tag:8s} {stmt:20s} vg={f['vg8020']:15s} cf={f['cf3300']:15s} "
              f"zb={f['zb']:15s}{mark}", flush=True)

    ctl = out.get("ctl", {})
    if any(ctl.get(s_) != ("0", "7") for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL DID NOT READ ERR 0 / A=7 ({ctl}) -- the "
              f"subroutine did not run or the witness is not being read, and no "
              f"row above means anything.")
        return 2
    dis = [t for t in out
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print("=== the witness is the point: A=0 refused before branching, "
          "A=7 branched first ===")
    for t in out:
        r = out[t]
        print(f"   {t:8s} vg {r['vg8020']}   cf {r['cf3300']}   zb {r['zb']}")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
