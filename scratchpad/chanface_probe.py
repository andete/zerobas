#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CHANFACE — what does a verb say about a channel that is not open?

The argument-SHAPE family closed at 123 rows and 4 defects (bare form, wrong type,
trailing junk, omitted args, one too many). This is the axis it did not cover: the
`#n` channel operand, which is neither a shape nor a type question. Every row here
names a channel that is **not open**, or one that cannot exist.

\U0001f3af THE FACES ARE THE INTERESTING PART. MSX BASIC distinguishes
`Bad file number` (52) from `File not open` (54) from `Illegal function call` (5),
and a reimplementation can easily answer one where the reference answers another --
`oo_fail_bfn` (ERR 52) already exists in this tree for OPEN alone.

  x.ctl        a plain assignment -- must be `no error` everywhere, or the rows
               below are measuring the harness
  ch.zero      `PRINT#0` -- channel 0 is the SCREEN on MSX, so this should WORK,
               and a verb that rejects it is over-strict rather than sloppy

⚠️ EVERY ROW RUNS ON BOTH REFERENCES AND REFS-SPLITS ARE REPORTED AS SUCH. The
VG-8020 has no disk ROM, so its channel handling may legitimately differ; the
CF-3300 is the oracle where they disagree (probes/lib/probe_sides.py).

⚠️ `ch.inputun` COULD BLOCK rather than answer -- INPUT# on a channel that is not
open might fall through to the keyboard. A `<none>` there is an absence, not an
answer, and is called out rather than scored.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_sides                                                # noqa: E402

SRC = os.path.join(ROOT, "disk", "test720.dsk")
SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
CASES = [
    ("x.ctl",       ["20 A=1"],                       "CONTROL: no channel at all"),
    ("ch.zero",     ['20 PRINT#0,"x"'],               "channel 0 is the SCREEN -- should WORK"),
    ("ch.unopened", ['20 PRINT#1,"x"'],               "PRINT# to a channel never opened"),
    ("ch.big",      ['20 PRINT#99,"x"'],              "a channel number past any ceiling"),
    ("ch.neg",      ['20 PRINT#-1,"x"'],              "a negative channel number"),
    ("ch.closeun",  ["20 CLOSE#1"],                   "CLOSE a channel never opened"),
    ("ch.eofun",    ["20 A=EOF(1)"],                  "EOF() on a channel never opened"),
    ("ch.lofun",    ["20 A=LOF(1)"],                  "LOF() on a channel never opened"),
    ("ch.getun",    ["20 GET#1"],                     "GET on a channel never opened"),
    ("ch.fieldun",  ["20 FIELD#1,10 AS A$"],          "FIELD on a channel never opened"),
    ("ch.inputun",  ["20 INPUT#1,A$"],                "INPUT# on a channel never opened"),
    # 🔴 THE ORDER HERE IS LOAD-BEARING, AND THE FIRST CUT HAD IT WRONG.
    # `MAXFILES` performs a CLEAR, and CLEAR DISARMS `ON ERROR` -- the same
    # mechanism D-MAXFTAIL measured hours earlier from the other direction. With
    # `MAXFILES=1` after the handler was installed, line 20's error was UNTRAPPED
    # on all three machines and the row blanked everywhere: agreement that
    # measured nothing. The handler is installed AFTER the MAXFILES now.
    ("ch.overmax",  ["5 MAXFILES=1", '20 PRINT#2,"x"'], "past the MAXFILES ceiling"),
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
    for tag, body, note in CASES:
        row = {}
        for side, c in SIDES.items():
            dsk = os.path.join(tempfile.gettempdir(), f"zb_cf_{tag}_{side}.dsk")
            if probe_sides.diska(side, dsk) is None:
                dsk = None
            else:
                shutil.copy(SRC, dsk)
            # a body line numbered BELOW 10 runs before the handler is armed;
            # everything else keeps the handler first.
            pre = [b for b in body if int(b.split()[0]) < 10]
            rest = [b for b in body if int(b.split()[0]) >= 10]
            p = pre + ['10 ON ERROR GOTO 900'] + rest + [
                '30 PRINT"ZQ";0;"QZ":END', '900 PRINT"ZQ";ERR;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=14.0,
                cap_gap=4.0, timeout=420.0, diska=dsk)[0] or "")
            row[side] = value(raw)
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  ("no error" if row[s_] == 0 else f"ERR {row[s_]}")) for s_ in SIDES}
        v = probe_sides.verdict(f["vg8020"], f["cf3300"], f["zb"])
        mark = {"SAME": "", "REFS-SPLIT": "   \U0001f7e1 REFS-SPLIT",
                "DIFF": "   \U0001f534 DIFF"}[v]
        print(f"  {tag:11s} vg={f['vg8020']:9s} cf={f['cf3300']:9s} "
              f"zb={f['zb']:9s}{mark}   {note}", flush=True)

    if any(out.get("x.ctl", {}).get(s_) != 0 for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL ERRORED ({out.get('x.ctl')}) -- the harness "
              f"is wrong and no row is a reading.")
        return 2
    vd = {k: probe_sides.verdict(v["vg8020"], v["cf3300"], v["zb"])
          for k, v in out.items()}
    dis = [k for k, x in vd.items() if x == "DIFF"]
    split = [k for k, x in vd.items() if x == "REFS-SPLIT"]
    blank = [k for k, v in out.items() if any(v[s_] is None for s_ in SIDES)]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print(f"    REFS-SPLIT ({len(split)}): {split or 'none'}")
    if blank:
        print(f"    \U0001f534 {blank} gave NO reading on a side -- an absence, not "
              f"agreement, and each needs a reason before it is read as anything.")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
