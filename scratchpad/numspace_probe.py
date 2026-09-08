#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-NUMSPACE — the space axis, asked of the NUMERIC functions.

D-FNSPACE fixed nine sites where `inc hl / ld a,(hl) / cp '('` rejected a space
between a STRING function's name and its paren -- `LEFT$ ("ABC",2)` was a Syntax
error on both counts where both references accept. Those sites were all in
str-engine.asm and strvar.asm.

\U0001f3af THE NUMERIC AND USER-DEFINED FUNCTIONS LIVE ELSEWHERE (expr.asm,
deffn.asm, interp.asm) AND WERE NEVER ASKED. The source sweep flagged
`interp.asm:878`, `interp.asm:920`, `expr.asm:597` and `missing.asm:459` with the
same `cp '('` shape but a DIFFERENT preceding instruction, so the D-FNSPACE
conversion did not touch them -- and whether their neighbours guard them is
exactly the thing reading cannot settle. D-MIDSPACE predicted four failures from
the source and got all four wrong.

The witness is the VALUE, not the error code: every row is arranged to yield a
small non-negative integer, and 999 means the assignment never happened.
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
    ("n.ctl",   [], "ABS(-7)",              "CONTROL: no space -- must give 7"),
    ("n.abs",   [], "ABS (-7)",             "space before ( -- ABS"),
    ("n.int",   [], "INT (7.9)",            "space before ( -- INT"),
    ("n.sgn",   [], "SGN (7)",              "space before ( -- SGN"),
    ("n.len",   [], 'LEN ("ABCDEFG")',      "space before ( -- LEN"),
    ("n.asc",   [], 'ASC ("A")',            "space before ( -- ASC"),
    ("n.val",   [], 'VAL ("7")',            "space before ( -- VAL"),
    ("n.instr", [], 'INSTR ("ABCDE","C")',  "space before ( -- INSTR"),
    ("n.deffn", ["15 DEF FNQ(X)=X*2"], "FNQ (3)", "space before ( -- a DEF FN call"),
    ("n.array", ["15 DIM Q(5):Q(3)=7"], "Q (3)",  "space before ( -- an ARRAY subscript"),
]


def main() -> int:
    out = {}
    for tag, extra, expr, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ["10 ON ERROR GOTO 900"] + extra + ["20 V=999", f"30 V={expr}",
                 '40 PRINT"ZQ";0;",";V;"QZ":END',
                 '900 PRINT"ZQ";ERR;",";V;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*,\s*(-?[0-9]+)\s*QZ', raw)
                 if not any(ch in "".join(g) for ch in '"$;')]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  f"ERR={row[s_][0]} V={row[s_][1]}") for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        print(f"  {tag:8s} {expr:22s} vg={f['vg8020']:16s} cf={f['cf3300']:16s} "
              f"zb={f['zb']:16s}{mark}", flush=True)

    ctl = out.get("n.ctl", {})
    if any(ctl.get(s_) != ("0", "7") for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL DID NOT READ ERR 0 / V=7 ({ctl}) -- no row "
              f"above means anything.")
        return 2
    dis = [t for t in out
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    for t in out:
        print(f"   {t:8s} vg {out[t]['vg8020']}   cf {out[t]['cf3300']}   "
              f"zb {out[t]['zb']}")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
