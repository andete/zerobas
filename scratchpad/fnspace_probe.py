#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FNSPACE — is `LEFT$ ("ABC",2)`, with a space before the paren, accepted?

D-MIDSPACE found the SPACE axis on `MID$ =` and fixed one site. A source sweep for
its signature -- `ld a,(hl)` immediately before a separator test, with nothing
skipping spaces in front -- reports FORTY-ONE more.

\U0001f534 BUT THAT SIGNATURE OVER-REPORTS, AND D-MIDSPACE IS THE PROOF. Four of its
five separator tests have exactly this shape and all four PASS, because
`str_target_parse` and `eval` leave HL past trailing spaces: the sites are guarded
by their NEIGHBOURS rather than by themselves. Reading predicted four failures and
got none of them right.

\U0001f3af SO THE SUBSET WORTH MEASURING IS THE ONE THAT MATCHES THE SHAPE THAT
ACTUALLY FAILED: `inc hl` (which skips nothing) immediately before the test. Ten
sites have it, and every one is a string function's opening paren -- so the
question is whether a space between a function's NAME and its `(` is accepted.

Every row yields a STRING, printed as the witness, because a function that
silently returns something wrong and one that errors are not the same failure and
`ERR` alone shows only the second.
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
    ("f.ctl",   'LEFT$("ABCDE",2)',   "CONTROL: no spaces -- must give AB"),
    ("f.left",  'LEFT$ ("ABCDE",2)',  "space before ( -- LEFT$"),
    ("f.mid",   'MID$ ("ABCDE",2,2)', "space before ( -- MID$ (function form)"),
    ("f.right", 'RIGHT$ ("ABCDE",2)', "space before ( -- RIGHT$"),
    ("f.strn",  'STRING$ (2,65)',     "space before ( -- STRING$"),
    ("f.chr",   'CHR$ (65)',          "space before ( -- CHR$"),
    ("f.close", 'LEFT$("ABCDE",2 )',  "space before the CLOSE paren"),
    ("f.comma", 'LEFT$("ABCDE" ,2)',  "space before the comma"),
    # --- widen: the same question in the other functions and positions -------
    ("f.mid2",  'MID$("ABCDE",2 ,2)', "space before MID$'s SECOND comma"),
    ("f.strn2", 'STRING$(2 ,65)',     "space before STRING$'s comma"),
    ("f.rgt2",  'RIGHT$("ABCDE" ,2)', "space before RIGHT$'s comma"),
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
