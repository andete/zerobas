#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-MIDSPACE — a SPACE around a separator: the axis no probe in this tree varies.

Picked by reading `ex_mid_stmt` (basic/str-engine.asm), a verb whose coverage is
inherited from the concluded string-engine arc. Its argument DOMAINS are already
right -- `eval_pos_arg` (1..255) for n, `eval_byte_arg` (0..255) for m, with
D-MISS-2's note recording that `MID$(A$,1,256)="X"` once assigned silently.

\U0001f3af WHAT THE READ FLAGS IS THE SEPARATORS. Every one of them is a bare

    ld   a,(hl)
    cp   ','
    jp   nz,stmt_error

with NO `skip_spaces` -- where `expect_comma_eval` (basic/save.asm), doing the
same job for BSAVE, calls `skip_spaces` first. The MSX tokeniser preserves spaces
in program text, so `MID$(A$ ,2)="X"` reaches that `cp` with $20 in A.

Three axes have now produced findings on three different verbs -- the TAIL
(D-MAXFTAIL, D-FMTTAIL, D-FLOWTAIL), the ARGUMENT POSITION (D-RAWVAL), and
whether a failure RAISES (D-SAVETRAP). This asks a fourth, and it is asked of the
verb whose source shows the asymmetry rather than of a list of verbs picked by
name.

The witness is the STRING, not the error code: a row that silently does nothing
and a row that assigns are both `ERR 0`.
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
    ("ctl",     'MID$(A$,2)="X"',    "CONTROL: no spaces -- must give AXCDE"),
    ("m.tgt",   'MID$(A$ ,2)="X"',   "space BEFORE the first comma"),
    ("m.n",     'MID$(A$, 2)="X"',   "space AFTER the first comma"),
    ("m.m",     'MID$(A$,2 ,1)="X"', "space before the SECOND comma"),
    ("m.close", 'MID$(A$,2 )="X"',   "space before the close paren"),
    ("m.eq",    'MID$(A$,2) ="X"',   "space before the ="),
]


def main() -> int:
    out = {}
    for tag, stmt, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ["10 ON ERROR GOTO 900", '20 A$="ABCDE"', f"30 {stmt}",
                 '40 PRINT"ZQ";0;",";A$;"QZ":END',
                 '900 PRINT"ZQ";ERR;",";A$;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*,\s*([A-Z]*)\s*QZ', raw)
                 if not any(ch in "".join(g) for ch in '"$;')]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  f"ERR={row[s_][0]} A$={row[s_][1] or '(empty)'}")
             for s_ in SIDES}
        vd = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[vd]
        print(f"  {tag:8s} {stmt:20s} vg={f['vg8020']:20s} cf={f['cf3300']:20s} "
              f"zb={f['zb']:20s}{mark}", flush=True)

    ctl = out.get("ctl", {})
    if any(ctl.get(s_) != ("0", "AXCDE") for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL DID NOT PRODUCE ERR 0 / AXCDE ({ctl}) -- the "
              f"assignment is not happening or the string is not being read, and "
              f"no row above means anything.")
        return 2
    dis = [t for t in out
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print("=== the STRING is the witness: a silent no-op and an assignment are "
          "both ERR 0 ===")
    for t in out:
        print(f"   {t:8s} vg {out[t]['vg8020']}   cf {out[t]['cf3300']}   "
              f"zb {out[t]['zb']}")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
