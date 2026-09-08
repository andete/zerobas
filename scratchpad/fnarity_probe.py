#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FNARITY — too few and too many arguments to the built-in FUNCTIONS.

Every sweep so far has been about STATEMENTS: shape (5 axes, 123 rows), channel,
domain. Functions are a different surface and a heavily used one, and the existing
coverage does not reach arity -- `kwsweep` exercises each function with ONE valid
usage, and `intarg-acceptance` covers numeric DOMAINS (`_neg`/`_ovf`/`_ill`) for
the raw-I/O family. Neither asks what happens when the argument COUNT is wrong.

\U0001f3af THE LEGAL ARITY IS PART OF THE ROW, not an assumption. `MID$` takes 2 OR
3 and `INSTR` takes 2 OR 3, so "one too few" and "one too many" are different
numbers per function; a sweep that tested a fixed count would report the optional
third argument as an error.

    function     legal      too few      too many
    LEFT$/RIGHT$ 2          1            3
    MID$         2 or 3     1            4
    INSTR        2 or 3     1            4
    STRING$      2          1            3
    CHR$/ASC/LEN/PEEK/VPEEK/ABS/INP/STICK/STRIG/PDL   1   0   2
    POINT        2          1            3

  f.ctl   a legal call -- must be `no error` everywhere, or the rows below are
          measuring the function rather than the arity
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
    ("f.ctl",      'A$=LEFT$("ab",1)',      "CONTROL: a legal 2-argument call"),
    ("left.few",   'A$=LEFT$("ab")',        "LEFT$ with 1 (needs 2)"),
    ("left.many",  'A$=LEFT$("ab",1,1)',    "LEFT$ with 3"),
    ("right.few",  'A$=RIGHT$("ab")',       "RIGHT$ with 1"),
    ("mid.few",    'A$=MID$("ab")',         "MID$ with 1 (takes 2 or 3)"),
    ("mid.many",   'A$=MID$("ab",1,1,1)',   "MID$ with 4"),
    ("instr.few",  'A=INSTR("ab")',         "INSTR with 1 (takes 2 or 3)"),
    ("instr.many", 'A=INSTR(1,"ab","b",1)', "INSTR with 4"),
    ("strng.few",  'A$=STRING$(3)',         "STRING$ with 1 (needs 2)"),
    ("strng.many", 'A$=STRING$(3,65,1)',    "STRING$ with 3"),
    ("chr.none",   'A$=CHR$()',             "CHR$ with none"),
    ("chr.many",   'A$=CHR$(65,1)',         "CHR$ with 2"),
    ("asc.many",   'A=ASC("a","b")',        "ASC with 2"),
    ("len.many",   'A=LEN("a",1)',          "LEN with 2"),
    ("peek.many",  'A=PEEK(0,1)',           "PEEK with 2"),
    ("abs.many",   'A=ABS(1,1)',            "ABS with 2"),
    ("point.few",  'A=POINT(0)',            "POINT with 1 (needs 2)"),
    ("stick.many", 'A=STICK(0,1)',          "STICK with 2"),
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
        print(f"  {tag:11s} {stmt:24s} vg={f['vg8020']:9s} cf={f['cf3300']:9s} "
              f"zb={f['zb']:9s}{mark}", flush=True)

    if any(out.get("f.ctl", {}).get(s_) != 0 for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL ERRORED ({out.get('f.ctl')}) -- a legal call "
              f"is rejected, so every row is measuring the function.")
        return 2
    vd = {k: probe_sides.verdict(v["vg8020"], v["cf3300"], v["zb"])
          for k, v in out.items()}
    dis = [k for k, x in vd.items() if x == "DIFF"]
    split = [k for k, x in vd.items() if x == "REFS-SPLIT"]
    acc = [k for k, v in out.items()
           if k != "f.ctl" and v["vg8020"] == v["cf3300"] == v["zb"] == 0]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print(f"    REFS-SPLIT ({len(split)}): {split or 'none'}")
    if acc:
        print(f"    \U0001f7e2 ACCEPTED on all three: {acc} -- the reference's own "
              f"tolerance, which a faithful reimplementation KEEPS.")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
