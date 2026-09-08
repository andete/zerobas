#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ATTRFN — ATTR$ is the fourth do-nothing word, and it is a FUNCTION.

`SET`, `IPL` and `CMD` shipped as three `stmt_table` rows (D-DONOTHING3). `ATTR$`
is the one left, and it needs a different shape: it is a function, so it costs a
`cp ATTR_TOKEN / jp z,...` arm inside `ev_f` (basic/expr.asm) -- 5 B of main
page 1 -- rather than a table row.

\U0001f534 AND THE THING TO MEASURE IS NOT ONLY THE ERROR CODE. Untokenised,
`ATTR$` is a perfectly good STRING VARIABLE NAME, so zerobas today does not raise
anything at all: `PRINT ATTR$` prints the empty string. The rows therefore ask
for BOTH the error and what a print produced, because "ERR 5" alone cannot
distinguish "raised on sight" from "raised later for some other reason".

\U0001f534 AND THE VG-8020 IS CARRIED ON PURPOSE. D-DONOTHING3 predicted `SET`,
`IPL` and `CMD` would need a disk-equipped oracle and be a diskless divergence;
measured, the DISKLESS VG-8020 reserves all three, so they were never Disk-BASIC
words. Whether `ATTR$` is the same is a question, not an inference from its three
neighbours [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_sides                                                # noqa: E402

SIDES = probe_sides.sides("vg8020", "cf3300", "zb", "zb_nodisk")
CASES = [
    ("a.ctl",   'A$="Y"',        "CONTROL: a legal string assignment"),
    ("a.print", "PRINT ATTR$",   "bare use of the word"),
    ("a.asg",   "A$=ATTR$",      "as an r-value"),
    ("a.call",  "A$=ATTR$(0)",   "with an argument, function-style"),
    ("a.var",   'ATTR$="Z"',     "as a VARIABLE name -- 0 means not reserved"),
]


def main() -> int:
    out = {}
    for tag, stmt, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ["10 ON ERROR GOTO 100", f"20 {stmt}",
                 '30 PRINT"ZQ";0;"QZ":END',
                 '100 PRINT"ZQ";ERR;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*QZ', raw)
                 if '"' not in g and ';' not in g]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else f"ERR={row[s_]}")
             for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        print(f"  {tag:9s} {stmt:14s} vg={f['vg8020']:8s} cf={f['cf3300']:8s} "
              f"zb={f['zb']:8s} nodisk={f['zb_nodisk']:8s}{mark}", flush=True)

    ctl = out.get("a.ctl", {})
    if any(ctl.get(s_) != "0" for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL DID NOT READ ERR 0 ({ctl}) -- no row above "
              f"means anything.")
        return 2
    refs_agree = all(out[t]["vg8020"] == out[t]["cf3300"] for t in out)
    print(f"\n=== the two references agree on every row: {refs_agree} ===")
    print("=== per row: vg / cf / zb / nodisk ===")
    for t in out:
        print(f"   {t:9s} {out[t]['vg8020']} / {out[t]['cf3300']} / "
              f"{out[t]['zb']} / {out[t]['zb_nodisk']}")
    dis = [t for t in out
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"=== {len(dis)} divergence(s): {dis or 'none'} ===")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
