#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-SAVETRAP — are the SAVE/BSAVE/BLOAD PARSE failures TRAPPABLE?

Auditing the review-tier entry that flags its own limit: "Coverage verified by
READING what each probe exercises; the handlers themselves were not re-read line
by line." Two suspicious mechanisms turned up in the read, and both are already
owned:

  * filename-as-expression -- closed by D-FNEXPR2 (`SAVE A$`) and D-FNEXPR.
  * printed-vs-raised errors -- D-LOADERR-FIX converted the MISSING-FILE class at
    five verbs to a raised ERR 53, and measured that the reference raises.

\U0001f3af WHAT NEITHER COVERS IS THE **PARSE** FAILURES. `do_save`'s trailing-junk
arm is `jp nz,load_error`, and `load_error` (basic/bload.asm) does
`ld (ERRMARK),a / jp print_msg` -- it PRINTS and does not raise. A syntax
condition reported through an I/O message is odd on its face; whether it is also
UNTRAPPABLE is the property no row asks, and D-MAXFTAIL is this tree's precedent
for an untrappable error being the serious half of a defect.

Every row therefore sets a witness inside the handler:

    A = 9  ->  ON ERROR caught it (trappable)
    A = 0  ->  the program ran ON to line 40 (printed, not raised)
    <none> ->  neither line printed: it stopped the program without trapping

\U0001f534 ONLY PARSE-STAGE ROWS ARE USED, and deliberately: each must fail BEFORE
any device is touched, so nothing here spins a tape motor or writes a disk image.
`CSAVE` with no name is NOT among them -- on the reference that is a legal
unnamed save and would start the tape.
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
    ("ctl",     "A=1/0",           "CONTROL: a plainly trappable error -- A must be 9"),
    ("s.bare",  "SAVE",            "SAVE with no filename at all"),
    ("b.noargs", 'BSAVE"CAS:X"',   "BSAVE without ,start,end"),
    ("b.noend", 'BSAVE"CAS:X",0',  "BSAVE without ,end"),
    ("l.bare",  "BLOAD",           "BLOAD with no filename"),
]


def main() -> int:
    out = {}
    for tag, stmt, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ["10 ON ERROR GOTO 900", "20 A=0", f"30 {stmt}",
                 '40 PRINT"ZQ";0;",";A;"QZ":END',
                 '900 A=9:PRINT"ZQ";ERR;",";A;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*,\s*([0-9]+)\s*QZ', raw)
                 if not any(ch in "".join(g) for ch in '"$;')]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none: stopped, untrapped>" if row[s_] is None else
                  f"ERR={row[s_][0]} A={row[s_][1]}") for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        print(f"  {tag:9s} {stmt:16s} vg={f['vg8020']:26s} cf={f['cf3300']:26s} "
              f"zb={f['zb']:26s}{mark}", flush=True)

    ctl = out.get("ctl", {})
    if any(ctl.get(s_) is None or ctl[s_][1] != "9" for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL WAS NOT TRAPPED ({ctl}) -- the harness's own "
              f"ON ERROR is not working, and no row above means anything.")
        return 2
    dis = [t for t in out
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print("=== A=9 trapped · A=0 printed-and-continued · <none> stopped untrapped ===")
    for t in out:
        print(f"   {t:9s} vg {out[t]['vg8020']}   cf {out[t]['cf3300']}   "
              f"zb {out[t]['zb']}")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
