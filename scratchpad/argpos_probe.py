#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ARGPOS — the LATER argument positions, at the cell that separates the domains.

Derived from D-NOFIND rather than from a suspicion. The raw-I/O trio was cleared
as a NO FINDING on a table whose row said `OUT p,v` **(both args)** and had ONE
`arg=` column; the value turned out to be a different domain from the port, and
two of that table's own probe values would have shown it.

\U0001f3af SO THE QUESTION IS NOT "is this verb checked" BUT "which POSITION did the
sweep vary". Applying it to what exists:

  * `intarg-acceptance` had eleven rows for POKE/VPOKE/OUT, all position 1  -> D-RAWVAL.
  * `tailjunk_probe` sweeps the TAIL of 20 verbs, including MOTOR/LOCATE/KEY, so
    the tail axis is covered and three no-findings survive that check.
  * `domain_probe` (D-DOMAIN) swept COLOR, LOCATE, SCREEN and SOUND -- but its
    later-position rows are `SOUND 0,999` and `LOCATE 0,99` only. **Every NEGATIVE
    it tests is in position 1** (`SOUND -1,0`, `LOCATE -1,0`, `SCREEN -1`,
    `COLOR -1`), and no THIRD argument appears anywhere.

That matters because a negative is exactly the cell that separated OUT's two
domains: `OUT -1,0` continues and `OUT 0,-1` raises ERR 5, the same literal in two
positions. A large value cannot separate them -- `999` is out of range for BOTH
the byte domain and any smaller one -- which is why `SOUND 0,999` agreeing proved
less than it looked.

Rows here are the cells that separate, in the positions nobody varied.
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
    ("ctl",      "SOUND 0,0",     "CONTROL: legal, ERR 0 everywhere"),
    # SOUND: D-DOMAIN has `SOUND -1,0` and `SOUND 0,999`; not `SOUND 0,-1`.
    ("s.vneg",   "SOUND 0,-1",    "value NEGATIVE -- the separating cell"),
    ("s.v256",   "SOUND 0,256",   "value just past a byte"),
    # LOCATE: D-DOMAIN has `LOCATE -1,0` and `LOCATE 0,99`; not `LOCATE 0,-1`,
    # and the THIRD argument appears in no sweep at all.
    ("l.rneg",   "LOCATE 0,-1",   "row NEGATIVE -- position 2"),
    ("l.cur2",   "LOCATE 0,0,2",  "cursor arg past 0..1 -- position 3"),
    ("l.curneg", "LOCATE 0,0,-1", "cursor arg NEGATIVE -- position 3"),
    # SCREEN: D-DOMAIN has `SCREEN -1` and `SCREEN 99`; position 2 is unswept.
    ("sc.sneg",  "SCREEN 0,-1",   "sprite-size NEGATIVE -- position 2"),
    ("sc.s99",   "SCREEN 0,99",   "sprite-size out of range -- position 2"),
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
        print(f"  {tag:9s} {stmt:15s} vg={f['vg8020']:9s} cf={f['cf3300']:9s} "
              f"zb={f['zb']:9s}{mark}   {note}", flush=True)

    ctl = out.get("ctl", {})
    if any(ctl.get(s_) != "0" for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL DID NOT READ ERR 0 ({ctl}) -- no row above "
              f"means anything.")
        return 2
    dis = [t for t in out
           if probe_sides.verdict(out[t]["vg8020"], out[t]["cf3300"],
                                  out[t]["zb"]) == "DIFF"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print("=== reference answers, for the record (vg / cf) ===")
    for t in out:
        print(f"   {t:9s} {out[t]['vg8020']} / {out[t]['cf3300']}")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
