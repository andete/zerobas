#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ARGTYPE — does every statement answer Type mismatch for a WRONG-TYPE argument?

Two members of this class have been found one at a time and never swept:
  * `FILES 5` -> `Type mismatch` with ZERO entries listed (D-FILESIDE)
  * `LSET A$=5` -> ERR 2 here against ERR 13 on the reference (D-LSETTM, fixed +4 B)
and D-MERGEXPR added a third hours ago (`MERGE 5`: ERR 2 -> ERR 13).

\U0001f3af THE RULE: a statement handed an argument of the wrong TYPE says
`Type mismatch` (13), not `Syntax error` (2). A reimplementation flattens that
distinction easily -- the parser rejects the token before anything asks what type
it is, and ERR 2 looks like a perfectly reasonable answer.

Each row passes the wrong type deliberately: a NUMBER where a string belongs, or a
STRING where a number belongs.

\U0001f534 BOTH REFERENCES ON EVERY ROW, AND A SPLIT REPORTS AS A SPLIT. D-BAREFORM
published five false divergences last night by asking a DISKLESS VG-8020
Disk-BASIC questions; the item above says the rule outright -- "zerobas ships a
disk ROM => the CF-3300 is the oracle, the cassette machines have no vote".

  a.ctl   a CORRECTLY typed argument -- must read `no error` on all three, or the
          rows below are measuring the FORM rather than the type
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

SRC = os.path.join(ROOT, "disk", "test720.dsk")
# 🔴 `disk` IS PER-SIDE AND THE VG-8020's IS FALSE. It has NO DRIVE, and
# openMSX refuses the machine outright rather than ignoring the image:
# "Fatal error: No disk drive A present to put image ... in." The first cut mounted
# the fixture on every side, so every VG row came back <none> and the CONTROL
# caught it. That is the same diskless machine that produced D-BAREFORM's five
# false divergences the night before.
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",), disk=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW"), disk=True),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=10.0, reset=("NEW",), disk=True),
}
CASES = [
    ("a.ctl",    'POKE&HC000,0',       "CONTROL: correctly typed -- must be no error"),
    # a NUMBER where a STRING belongs
    ("kill",     'KILL 5',             "number for a filename"),
    ("name",     'NAME 5 AS "X"',      "number for the old name"),
    ("save",     'SAVE 5',             "number for a filename"),
    ("load",     'LOAD 5',             "number for a filename"),
    ("bload",    'BLOAD 5',            "number for a filename"),
    ("open",     'OPEN 5 AS #1',       "number for a filename"),
    ("files",    'FILES 5',            "D-FILESIDE's own row, re-taken"),
    ("play",     'PLAY 5',             "number for an MML string"),
    ("draw",     'DRAW 5',             "number for a DRAW string"),
    ("lset",     'LSET A$=5',          "D-LSETTM's own row, re-taken"),
    # a STRING where a NUMBER belongs
    ("poke",     'POKE "A",0',         "string for an address"),
    ("vpoke",    'VPOKE "A",0',        "string for an address"),
    ("out",      'OUT "A",0',          "string for a port"),
    ("locate",   'LOCATE "A",0',       "string for a column"),
    ("sound",    'SOUND "A",0',        "string for a register"),
    ("width",    'WIDTH "A"',          "string for a width"),
    ("screen",   'SCREEN "A"',         "string for a mode"),
    ("color",    'COLOR "A"',          "string for a colour"),
    ("maxfiles", 'MAXFILES="A"',       "string for a channel count"),
    ("time",     'TIME="A"',           "string for a tick count"),
    ("pset",     'PSET("A",0)',        "string for a coordinate"),
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
            dsk = None
            if c["disk"]:
                dsk = os.path.join(tempfile.gettempdir(), f"zb_at_{tag}_{side}.dsk")
                shutil.copy(SRC, dsk)
            p = ['10 ON ERROR GOTO 900', f'20 {stmt}',
                 '30 PRINT"ZQ";0;"QZ":END', '900 PRINT"ZQ";ERR;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=14.0,
                cap_gap=4.0, timeout=420.0, diska=dsk)[0] or "")
            row[side] = value(raw)
        out[tag] = row
        f = {s_: ("<none>" if row[s_] is None else
                  ("no error" if row[s_] == 0 else f"ERR {row[s_]}")) for s_ in SIDES}
        if f["vg8020"] != f["cf3300"]:
            mark = "   \U0001f7e1 REFS-SPLIT"
        elif f["zb"] != f["cf3300"]:
            mark = "   \U0001f534 DIFF"
        else:
            mark = ""
        print(f"  {tag:9s} {stmt:16s} vg={f['vg8020']:9s} cf={f['cf3300']:9s} "
              f"zb={f['zb']:9s}{mark}", flush=True)

    if any(out.get("a.ctl", {}).get(s_) != 0 for s_ in SIDES):
        print(f"\n\U0001f534 THE CONTROL ERRORED ({out.get('a.ctl')}) -- the rows "
              f"below are measuring the form, not the type.")
        return 2
    split = [k for k, v in out.items() if v["vg8020"] != v["cf3300"]]
    dis = [k for k, v in out.items()
           if v["vg8020"] == v["cf3300"] and v["zb"] != v["cf3300"]]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print(f"    REFS-SPLIT ({len(split)}): {split or 'none'} -- scored against the "
          f"CF-3300 only,\n    since zerobas ships a disk ROM and the cassette "
          f"machine has no vote on these.")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
