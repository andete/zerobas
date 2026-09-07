#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TAILJUNK — does a COMPLETE statement reject what follows it?

D-FMTTAIL (2026-09-01) found `CALL FORMAT`'s name-tail and argument skip
"sloppy-accept": after matching six characters everything up to ':'/EOL was
silently swallowed, so `CALL FORMATFOO` and `CALL FORMAT anything` both formatted.
The reference is strict on every count. **One verb was fixed; the class was never
swept.**

\U0001f3af THE RULE THIS TESTS: a statement whose arguments are COMPLETE must reject a
further operand. The test appends a bare name to a legal form --

    <VERB> <complete legal args> ZZ

-- and a verb that answers "no error" swallowed it.

\U0001f534 BOTH REFERENCES RUN ON EVERY ROW, AND A SPLIT IS REPORTED AS A SPLIT. That
is not caution for its own sake: D-BAREFORM published seven divergences earlier
tonight of which FIVE were the diskless VG-8020 being asked Disk-BASIC questions.
Nothing here needs a disk, but the default is now both machines regardless
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].

⚠️ THE TRAILING TOKEN IS `ZZ`, A BARE NAME, ON PURPOSE. A number could be read as
a further argument by a verb that takes a variable count (`COLOR fg,bg,bd`), and
then "accepted" would be correct rather than sloppy. `ZZ` is a variable reference,
which no statement in this list can legitimately consume.

  t.ctl    a legal form with NOTHING after it -- must read `no error` everywhere,
           or the rows below are measuring the form and not the tail
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=10.0, reset=("NEW",)),
}
# (tag, the COMPLETE legal statement; the probe appends " ZZ")
FORMS = [
    ("t.ctl",    "POKE&HC000,0"),      # CONTROL: the same form with no tail
    ("poke",     "POKE&HC000,0"),
    ("vpoke",    "VPOKE 0,0"),
    ("out",      "OUT &HA0,0"),
    ("locate",   "LOCATE 0,0"),
    ("color",    "COLOR 15,4,4"),
    ("screen",   "SCREEN 0"),
    ("width",    "WIDTH 40"),
    ("sound",    "SOUND 0,0"),
    ("cls",      "CLS"),
    ("tron",     "TRON"),
    ("troff",    "TROFF"),
    ("beep",     "BEEP"),
    ("motor",    "MOTOR OFF"),
    ("keyoff",   "KEY OFF"),
    ("close",    "CLOSE"),
    ("clear",    "CLEAR"),
    ("restore",  "RESTORE"),
    ("defint",   "DEFINT Q"),
    ("maxfiles", "MAXFILES=1"),
    ("time",     "TIME=0"),
    ("pset",     "PSET(0,0)"),
    ("preset",   "PRESET(0,0)"),
    ("erase",    "ERASE Q"),
    ("swap",     "SWAP A,B"),
]
PRE = {"erase": "5 DIM Q(2)", "swap": "5 A=1:B=2"}


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
    for tag, form in FORMS:
        stmt = form if tag == "t.ctl" else f"{form} ZZ"
        row = {}
        for side, c in SIDES.items():
            p = ([PRE[tag]] if tag in PRE else []) + [
                '10 ON ERROR GOTO 900', f'20 {stmt}',
                '30 PRINT"ZQ";0;"QZ":END', '900 PRINT"ZQ";ERR;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0,
                run_gap=12.0, cap_gap=4.0, timeout=420.0)[0] or "")
            row[side] = value(raw)
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  ("SWALLOWED" if row[s_] == 0 else f"ERR {row[s_]}"))
             for s_ in SIDES}
        if f["vg8020"] != f["cf3300"]:
            mark = "   \U0001f7e1 REFS-SPLIT"
        elif f["zb"] != f["cf3300"]:
            mark = "   \U0001f534 DIFF"
        else:
            mark = ""
        print(f"  {tag:9s} {stmt:16s} vg={f['vg8020']:10s} cf={f['cf3300']:10s} "
              f"zb={f['zb']:10s}{mark}", flush=True)

    ctl = out.get("t.ctl", {})
    if any(ctl.get(s_) != 0 for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL ERRORED ({ctl}) -- the legal form is not "
              f"legal, so every row below is measuring the FORM and not the tail.")
        return 2
    split = [k for k, v in out.items() if v["vg8020"] != v["cf3300"]]
    dis = [k for k, v in out.items()
           if v["vg8020"] == v["cf3300"] and v["zb"] != v["cf3300"]]
    both = [k for k, v in out.items()
            if k != "t.ctl" and v["vg8020"] == v["cf3300"] == v["zb"] == 0]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print(f"    REFS-SPLIT ({len(split)}): {split or 'none'}")
    if both:
        print(f"    \U0001f7e2 {both} swallow the tail on ALL THREE -- agreement, and "
              f"NOT a zerobas defect. Worth writing down as the reference's own "
              f"sloppiness, which a faithful reimplementation must KEEP.")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
