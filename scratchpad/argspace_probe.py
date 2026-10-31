#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ARGSPACE, measure first (2026-10-31): a space AFTER a string function's
comma or open paren, in front of a STRING argument (D-REREAD batch 7 reviewer:
STRING$ does `inc hl / call str_eval`, and str_eval_one does not skip spaces).
D-FNSPACE (2026-09-09) measured spaces BEFORE `(` and before a comma, never this
position. Same harness as scratchpad/fnspace_probe.py; every row yields a string.
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
    ("f.ctl",    'LEFT$("ABCDE",2)',      "CONTROL: no spaces -- must give AB"),
    ("a.strn",   'STRING$(2, "AB")',      "space after STRING$'s comma, string x$"),
    ("a.strnv",  'STRING$(2, R$)',        "the same with a variable"),
    ("a.strnn",  'STRING$(2, 65)',        "space after the comma, numeric (control)"),
    ("a.left",   'LEFT$( "ABCDE",2)',     "space after LEFT$'s ("),
    ("a.mid",    'MID$( "ABCDE",2,2)',    "space after MID$'s ("),
    ("a.right",  'RIGHT$( "ABCDE",2)',    "space after RIGHT$'s ("),
    ("a.instr",  'CHR$(64+INSTR("AB", "B"))', "space after INSTR's comma"),
    ("a.instr3", 'CHR$(64+INSTR(1, "AB","B"))', "space after INSTR's first comma"),
    ("a.len",    'CHR$(64+LEN( "AB"))',   "space after LEN's ("),
    ("a.asc",    'CHR$(ASC( "A"))',       "space after ASC's ("),
    ("a.val",    'CHR$(64+VAL( "2"))',    "space after VAL's ("),
]


def main() -> int:
    out = {}
    for tag, expr, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ["10 ON ERROR GOTO 900", '20 R$="-"', f"30 R$={expr}",
                 '40 PRINT"ZQ";0;",";R$;"QZ":END',
                 '900 PRINT"ZQ";ERR;",";R$;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*,\s*([A-Z\-]*)\s*QZ', raw)
                 if not any(ch in "".join(g) for ch in '"$;')]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  f"ERR={row[s_][0]} R$={row[s_][1] or '(empty)'}") for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        print(f"  {tag:8s} {expr:20s} vg={f['vg8020']:17s} cf={f['cf3300']:17s} "
              f"zb={f['zb']:17s}{mark}", flush=True)

    ctl = out.get("f.ctl", {})
    if any(ctl.get(s_) != ("0", "AB") for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL DID NOT READ ERR 0 / AB ({ctl}) -- no row "
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
