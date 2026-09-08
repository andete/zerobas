#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PARTIAL — when a statement FAILS, what did it already do? Starting with my own fix.

The argument surface is exhausted (8 axes, 175 rows, 5 defects). The one SERIOUS
defect in it was not about what a verb accepts but about what it LEAVES BEHIND:
`MAXFILES=1 ZZ` ran its `CLEAR` before rejecting the tail, wiping the user's
variables and disarming the trap that would have caught the error (D-MAXFTAIL).
This sweep is that question asked deliberately.

\U0001f534 AND THE FIRST ROW IS A CHECK ON MY OWN WORK FROM AN HOUR AGO. D-DOMAIN
gave `COLOR` a per-component validator (`clr_eval`), which by construction stores
the FOREGROUND before it evaluates -- and rejects -- the background. So
`COLOR 7,99` now sets FORCLR=7 and then raises ERR 5. If the references reject
the statement ATOMICALLY, that fix traded a domain divergence for a partial-
execution one, and the rows would still read green because D-DOMAIN only asked
for the error CODE.

The readout is the sysvar itself, PEEKed after the trap:
    FORCLR $F3E9   BAKCLR $F3EA   BDRCLR $F3EB

  p.ctl     a fully legal COLOR -- FORCLR must become 7 everywhere, or the probe
            is not reading the cell it thinks it is
  col.fgok  `COLOR 7,99`: fg legal, bg illegal. 7 => the fg was applied before the
            failure; 15 => the statement was rejected as a whole
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
# every case starts from a known state: fg 15, bg 4, border 4
SETUP = ["10 ON ERROR GOTO 900", "20 COLOR 15,4,4"]
CASES = [
    ("p.ctl",     "COLOR 7,4,4",  "CONTROL: fully legal -- FORCLR must read 7"),
    # --- the four ways a COLOR statement can fail AFTER storing something ------
    ("col.fgok",  "COLOR 7,99",   "bg out of range   -> clr_ill"),
    ("col.bgok",  "COLOR 7,8,99", "border out of range -> clr_ill"),
    ("col.tail",  "COLOR 7,8,",   "trailing comma    -> clr_missing (ERR 24)"),
    ("col.type",  'COLOR 7,"A"',  "type mismatch     -> raised inside eval"),
    # --- and one that must be clean on any reading ----------------------------
    ("col.fgbad", "COLOR 99,8",   "fg ILLEGAL -- nothing stored on any reading"),
]


def main() -> int:
    out = {}
    for tag, stmt, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = SETUP + [f"30 {stmt}",
                         '40 PRINT"ZQ";PEEK(&HF3E9);",";PEEK(&HF3EA);",";0;"QZ":END',
                         '900 PRINT"ZQ";PEEK(&HF3E9);",";PEEK(&HF3EA);",";ERR;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=12.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = [g for g in re.findall(r"ZQ\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)\s*QZ", raw)
                 if not any(ch in "".join(g) for ch in '"$;')]
            row[side] = v[-1] if v else None
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  f"fg={row[s_][0]} bg={row[s_][1]} ERR={row[s_][2]}") for s_ in SIDES}
        v_ = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[v_]
        print(f"  {tag:10s} {stmt:13s} vg={f['vg8020']:22s} cf={f['cf3300']:22s} "
              f"zb={f['zb']:22s}{mark}", flush=True)

    ctl = out.get("p.ctl", {})
    if any(ctl.get(s_) is None or ctl[s_][0] != "7" for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL DID NOT SET FORCLR=7 ({ctl}) -- the probe is "
              f"not reading the cell it thinks it is, and no row below means "
              f"anything.")
        return 2
    vd = {k: probe_sides.verdict(
              f"{v['vg8020']}", f"{v['cf3300']}", f"{v['zb']}")
          for k, v in out.items()}
    dis = [k for k, x in vd.items() if x == "DIFF"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    ref = out.get("col.fgok", {}).get("cf3300")
    if ref:
        print("  \U0001f3af `COLOR 7,99` on the reference leaves FORCLR = " + ref[0] +
              ("  -> the foreground IS applied before the failure; a per-component"
               "\n     validator is FAITHFUL." if ref[0] == "7" else
               "  -> the statement is rejected ATOMICALLY, and a per-component"
               "\n     validator is NOT faithful."))
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
