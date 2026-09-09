#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LVSPACE — a space before an ARRAY SUBSCRIPT on the LEFT of an assignment.

D-FNSPACE fixed nine `inc hl / ld a,(hl) / cp '('` sites in the string functions;
D-NUMSPACE then measured the numeric and array R-VALUE paths clean — `Q (3)` reads
fine on all three machines, because `ev_f` reaches its paren through `ev_sp`.

🎯 THE L-VALUE PATH IS A DIFFERENT SITE AND WAS NOT IN EITHER SWEEP. `ex_let`
(basic/interp.asm) tests for a subscript with a bare

    ld   a,(hl)
    cp   '('

with nothing skipping spaces in front — while the `=` three lines below IS guarded
by `call skip_spaces`. One statement, two separator tests, one of them protected.
That asymmetry inside a single handler is what makes this worth a row rather than
a guess.

⚠️ AND THE GUESS WOULD PROBABLY BE WRONG ANYWAY. D-MIDSPACE predicted four failures
from exactly this source pattern and got all four wrong: the sites were guarded by
their NEIGHBOURS, because `var_name_key` and `eval` leave HL past trailing spaces.
`var_name_key` runs immediately before this test too.

The witness is the VALUE read back, not the error code: an assignment that silently
lands in the wrong place and one that raises are different failures.
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
    ("ctl",    "Q(3)=7",      "CONTROL: no space -- must read back 7"),
    ("a.sp",   "Q (3)=7",     "space before the SUBSCRIPT, l-value"),
    ("a.let",  "LET Q (3)=7", "the same with an explicit LET"),
    ("a.eq",   "Q(3) =7",     "space before the `=` -- that site IS guarded"),
    ("a.both", "Q (3) =7",    "both"),
]


def main() -> int:
    out = {}
    for tag, stmt, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ["10 ON ERROR GOTO 900", "20 DIM Q(5):V=999", f"30 {stmt}",
                 "40 V=Q(3)",
                 '50 PRINT"ZQ";0;",";V;"QZ":END',
                 '900 PRINT"ZQ";ERR;",";V;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*,\s*([0-9]+)\s*QZ', raw)
                 if not any(ch in "".join(g) for ch in '"$;')]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  f"ERR={row[s_][0]} Q3={row[s_][1]}") for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        print(f"  {tag:7s} {stmt:14s} vg={f['vg8020']:16s} cf={f['cf3300']:16s} "
              f"zb={f['zb']:16s}{mark}", flush=True)

    ctl = out.get("ctl", {})
    if any(ctl.get(s_) != ("0", "7") for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL DID NOT READ BACK 7 ({ctl}) -- the array "
              f"assignment is not working at all, and no row means anything.")
        return 2
    dis = [t for t in out
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print("=== Q3=7 the assignment landed · Q3=0 it went elsewhere · Q3=999 never ran ===")
    for t in out:
        print(f"   {t:7s} vg {out[t]['vg8020']}   cf {out[t]['cf3300']}   "
              f"zb {out[t]['zb']}")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
