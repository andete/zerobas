#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-EXTRAARG — one argument TOO MANY. The mirror of D-OMITARG.

D-OMITARG swept the omission shapes and found `COLOR` accepting a trailing comma
that every other verb rejects; D-BAREFIX had found its BARE form wrong six hours
before that. Two defects in one verb's argument handling, both in shapes nobody
had swept. This is the remaining axis: a comma followed by a further VALUE.

\U0001f3af IT IS A DIFFERENT PARSE PATH FROM D-TAILJUNK. That sweep appended a bare
name (`POKE x,0 ZZ`) with no separator, which every verb rejected. Here the
separator is present and well-formed, so a verb that counts its arguments by
"is there another comma?" rather than by position will keep going.

  x.ctl   the fully-specified legal form -- must be `no error` everywhere, or the
          rows below are measuring the verb rather than the extra argument

Machine facts from probes/lib/probe_sides.py: the VG-8020 has no drive, the
CF-3300 is the oracle where they disagree, and a disagreement is a REFS-SPLIT.
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
    ("x.ctl",    "COLOR 15,4,4",       "CONTROL: the legal form, nothing extra"),
    ("color",    "COLOR 15,4,4,1",     "a 4th argument"),
    ("locate",   "LOCATE 0,0,0,1",     "a 4th argument"),
    ("sound",    "SOUND 0,0,0",        "a 3rd argument"),
    ("poke",     "POKE&HC000,0,0",     "a 3rd argument"),
    ("vpoke",    "VPOKE 0,0,0",        "a 3rd argument"),
    ("out",      "OUT &HA0,0,0",       "a 3rd argument"),
    ("width",    "WIDTH 40,40",        "a 2nd argument"),
    ("screen",   "SCREEN 0,0,0,0,0,0", "a 6th argument (MSX1 SCREEN takes up to 5)"),
    ("pset",     "PSET(0,0),1,1",      "a further value after the colour"),
    ("maxfiles", "MAXFILES=1,1",       "a 2nd value"),
    ("time",     "TIME=0,0",           "a 2nd value"),
    ("beep",     "BEEP,1",             "an argument on a no-argument verb"),
    ("cls",      "CLS,1",              "an argument on a no-argument verb"),
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
                  ("ACCEPTED" if row[s_] == 0 else f"ERR {row[s_]}")) for s_ in SIDES}
        v = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[v]
        print(f"  {tag:9s} {stmt:20s} vg={f['vg8020']:9s} cf={f['cf3300']:9s} "
              f"zb={f['zb']:9s}{mark}", flush=True)

    if any(out.get("x.ctl", {}).get(s_) != 0 for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL ERRORED ({out.get('x.ctl')}) -- the legal "
              f"form is not accepted, so every row is measuring the verb.")
        return 2
    vd = {k: probe_sides.verdict(v["vg8020"], v["cf3300"], v["zb"])
          for k, v in out.items()}
    dis = [k for k, x in vd.items() if x == "DIFF"]
    split = [k for k, x in vd.items() if x == "REFS-SPLIT"]
    both = [k for k, v in out.items()
            if k != "x.ctl" and v["vg8020"] == v["cf3300"] == v["zb"] == 0]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print(f"    REFS-SPLIT ({len(split)}): {split or 'none'}")
    if both:
        print(f"    \U0001f7e2 {both} ACCEPT the extra argument on ALL THREE -- the "
              f"reference's own sloppiness, which a faithful reimplementation must "
              f"KEEP. Written down so it is not 'fixed' later.")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
