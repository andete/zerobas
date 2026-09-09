#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PARTSTATE — what did a failed LIST statement already do to the world?

Three axes of the ARGUMENT SURFACE came back empty in a row tonight (D-ARGPOS,
D-LISTCOMMA, D-VDPDOM), while all three of the evening's serious defects were
about RUN-TIME STATE: D-MAXFTAIL (a CLEAR that ran before the tail was rejected,
wiping variables AND disarming the trap), D-SAVETRAP (a parse failure that printed
instead of raising, so ON ERROR never saw it) and D-PARTIAL (COLOR storing each
component as it validated it). So this asks that question of the verbs that
mutate the world ITEM BY ITEM.

`partial_probe.py` asked it of COLOR only. `DIM a,b`, `ERASE a,b` and `READ a,b`
each act on the first item before they can discover the second is bad.

\U0001f3af THE WITNESS IS A SECOND STATEMENT, NOT A VALUE. Whether an array still
exists is not readable directly -- but `DIM P(3)` on an array that already exists
is **ERR 10, Redimensioned array**, and on one that does not it simply succeeds.
That turns "did the failed DIM allocate P?" into an error code:

    W = 10  ->  P EXISTS
    W = 0   ->  P DOES NOT

and the control row proves the witness can say both.
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
# (tag, setup line, the statement under test, the witness statement, note)
CASES = [
    ("w.ctl",   "25 DIM P(3)", "P(0)=0",        "DIM P(3)",
     "CONTROL: P exists -> the witness must read 10"),
    ("w.ctl2",  "25 REM",      "P(0)=0",        "DIM P(3)",
     "CONTROL: P auto-dimensioned by use -> witness reads 10 too"),
    ("d.part",  "25 REM",      "DIM P(3),Q(-1)", "DIM P(3)",
     "DIM list, second item ILLEGAL -- was P allocated first?"),
    ("e.part",  "25 DIM P(3)", "ERASE P,Q",      "DIM P(3)",
     "ERASE list, second item UNDEFINED -- was P erased first?"),
    ("e.ctl",   "25 DIM P(3)", "ERASE P",        "DIM P(3)",
     "CONTROL: a clean ERASE -> witness must read 0"),
]


def main() -> int:
    out = {}
    for tag, setup, stmt, wit, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ["10 ON ERROR GOTO 900", "20 S=0:W=0", setup,
                 f"30 {stmt}", "40 GOTO 100",
                 "900 S=ERR:RESUME 100",
                 "100 ON ERROR GOTO 200",
                 f"110 {wit}", "120 GOTO 300",
                 "200 W=ERR:RESUME 300",
                 '300 PRINT"ZQ";S;",";W;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=12.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*,\s*([0-9]+)\s*QZ', raw)
                 if not any(ch in "".join(g) for ch in '"$;')]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  f"ERR={row[s_][0]} W={row[s_][1]}") for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        print(f"  {tag:8s} {stmt:16s} vg={f['vg8020']:16s} cf={f['cf3300']:16s} "
              f"zb={f['zb']:16s}{mark}", flush=True)

    c1 = out.get("w.ctl", {}); c2 = out.get("e.ctl", {})
    if any(c1.get(s_) != ("0", "10") for s_ in SIDES):
        print(f"\n\U0001f534 CONTROL w.ctl DID NOT READ W=10 ({c1}) -- the witness "
              f"cannot see an array that EXISTS, so no row means anything.")
        return 2
    if any(c2.get(s_) != ("0", "0") for s_ in SIDES):
        print(f"\n\U0001f534 CONTROL e.ctl DID NOT READ W=0 ({c2}) -- the witness "
              f"cannot see an array that is GONE, so it can only ever say one "
              f"thing and the rows below are worthless.")
        return 2
    dis = [t for t in out
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print("=== W=10 the array EXISTS · W=0 it does NOT ===")
    for t in out:
        print(f"   {t:8s} vg {out[t]['vg8020']}   cf {out[t]['cf3300']}   "
              f"zb {out[t]['zb']}")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
