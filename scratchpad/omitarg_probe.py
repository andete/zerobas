#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-OMITARG — the OMITTED-argument forms of the comma-separated statements.

D-BAREFORM found bare `COLOR` succeeding where both references raise Missing
operand, and `missing.asm` records the design question those verbs share:
*"an OMITTED argument KEEPS the current value ... ex_color's bare form re-applies,
LOCATE's simply does not move that axis"*. That note was written about ONE axis of
ONE verb. The class — every comma-omission shape across every verb that takes
optional positional arguments — has never been swept, and the bare form of one of
them was wrong until last night.

\U0001f3af THE SHAPES, and each is a different question:
    COLOR ,4        leading omission   -- is a leading comma legal at all?
    COLOR 15,,4     interior omission  -- the documented "keep current" case
    COLOR 15,4,     TRAILING comma     -- a separator with nothing after it
    COLOR ,,4       two omissions
so a verb can be right about the interior case and wrong about the edges.

⚠️ THIS IS A FACE SWEEP, NOT A SEMANTIC ONE. It asks whether the form is ACCEPTED
and with what error, not whether the omitted axis kept its value -- that needs a
readback per verb and is the next probe if a row moves.

The machine facts come from probes/lib/probe_sides.py: the VG-8020 has no disk
drive, the CF-3300 is the oracle where they disagree, and a disagreement is a
REFS-SPLIT rather than a zerobas defect.
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
    ("o.ctl",      "COLOR 15,4,4",  "CONTROL: nothing omitted -- must be no error"),
    ("col.lead",   "COLOR ,4",      "fg omitted"),
    ("col.mid",    "COLOR 15,,4",   "bg omitted -- the documented keep-current case"),
    ("col.trail",  "COLOR 15,4,",   "TRAILING comma, border missing"),
    ("col.two",    "COLOR ,,4",     "fg and bg both omitted"),
    ("col.onlyc",  "COLOR ,,",      "every axis omitted, commas only"),
    ("loc.lead",   "LOCATE ,5",     "column omitted"),
    ("loc.mid",    "LOCATE 0,,1",   "row omitted, cursor given"),
    ("loc.trail",  "LOCATE 0,5,",   "TRAILING comma, cursor missing"),
    ("scr.lead",   "SCREEN ,1",     "mode omitted, sprite size given"),
    ("scr.trail",  "SCREEN 0,",     "TRAILING comma"),
    ("pset.col",   "PSET(0,0),",    "TRAILING comma, colour missing"),
    ("snd.trail",  "SOUND 0,",      "TRAILING comma on a 2-arg verb"),
    ("poke.trail", "POKE&HC000,",   "TRAILING comma on a 2-arg verb"),
    ("wid.trail",  "WIDTH 40,",     "TRAILING comma on a 1-arg verb"),
]


def value(scr):
    if scr is None:
        return None
    for g in reversed(re.findall(r"ZQ\s*([0-9]+)\s*QZ", scr)):
        if any(ch in g for ch in '"$;'):
            continue
        return int(g)
    return None


def main() -> int:
    out = {}
    for tag, stmt, note in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ['10 ON ERROR GOTO 900', f'20 {stmt}',
                 '30 PRINT"ZQ";0;"QZ":END', '900 PRINT"ZQ";ERR;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=12.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            row[side] = value(raw)
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  ("no error" if row[s_] == 0 else f"ERR {row[s_]}")) for s_ in SIDES}
        v = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[v]
        print(f"  {tag:10s} {stmt:15s} vg={f['vg8020']:9s} cf={f['cf3300']:9s} "
              f"zb={f['zb']:9s}{mark}", flush=True)

    if any(out.get("o.ctl", {}).get(s_) != 0 for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL ERRORED ({out.get('o.ctl')}) -- the fully "
              f"specified form is not accepted, so every omission row below is "
              f"measuring the verb and not the omission.")
        return 2
    vd = {k: probe_sides.verdict(v["vg8020"], v["cf3300"], v["zb"])
          for k, v in out.items()}
    dis = [k for k, x in vd.items() if x == "DIFF"]
    split = [k for k, x in vd.items() if x == "REFS-SPLIT"]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print(f"    REFS-SPLIT ({len(split)}): {split or 'none'}")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
