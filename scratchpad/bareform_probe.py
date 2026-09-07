#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-BAREFORM — what does every argument-taking statement do with NO argument?

D-MERGEXPR found `MERGE` bare answering `Syntax error` where the CF-3300 answers
`ERR 24 Missing operand`, and fixed that one verb. `ex_locate` already carries the
same measured face ("a bare `LOCATE` is Missing operand (ERR 24), not a no-op and
not a Syntax error"). Two verbs, same shape, found eleven days apart and never
swept.

\U0001f3af THE METHOD IS D-MERGEXPR's AND D-COLONTAIL's: ask a rule that should hold
across a whole CLASS, then check every member. Here: **a statement that REQUIRES
an operand must say which error it is**, and `Syntax error` vs `Missing operand`
is a distinction the reference draws and a reimplementation can easily flatten.

    10 ON ERROR GOTO 900
    20 <VERB>                 <- bare, no arguments at all
    30 PRINT"ZQ";0;"QZ":END   <- reached only if the verb did NOT error
    900 PRINT"ZQ";ERR;"QZ":END

A row reads 0 if the bare form is LEGAL, or the trapped error code.

⚠️ WHAT IS DELIBERATELY NOT IN THE LIST, and why -- each of these would blank or
destroy rather than answer, and a blank row is not a reading:
  INPUT / LINE INPUT / RANDOMIZE   block waiting for the keyboard (D-COLONTAIL
                                   established RANDOMIZE never returns)
  AUTO                             enters auto-line-number mode and swallows
                                   everything after it (D-AUTO)
  NEW                              deletes the program, fence lines included
  RUN / END / STOP / CONT          end or restart the program, so line 30 is
                                   unreachable for reasons that are not an error
No row here touches the disk: a bare file verb fails on its missing operand long
before any drive is selected.
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
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=10.0, reset=("NEW",)),
}
VERBS = [
    "REM",          # CONTROL: a bare form that is unambiguously legal -> 0
    "POKE", "VPOKE", "OUT", "WAIT", "LOCATE", "SOUND", "PSET", "PRESET",
    "LINE", "CIRCLE", "PAINT", "DRAW", "PLAY", "DIM", "ERASE", "SWAP",
    "DEFINT", "GOTO", "GOSUB", "RESUME", "READ", "WIDTH", "LPRINT",
    "CALL", "BLOAD", "BSAVE", "SAVE", "LOAD", "MERGE", "KILL", "NAME",
    "OPEN", "FIELD", "GET", "PUT", "LSET", "RSET", "CLOAD", "CSAVE",
    "DELETE", "SCREEN", "COLOR", "KEY", "MOTOR", "CLOSE", "BEEP", "CLEAR",
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
    # `--only A,B,C` re-runs a subset. A divergence is one measurement until it is
    # taken twice, and re-running 49 verbs to confirm 8 is 82 wasted boots.
    only = None
    for i, a in enumerate(sys.argv):
        if a == "--only" and i + 1 < len(sys.argv):
            only = {v.strip().upper() for v in sys.argv[i + 1].split(",")}
    verbs = [v for v in VERBS if only is None or v in only or v == "REM"]
    out = {}
    for verb in verbs:
        p = ['10 ON ERROR GOTO 900', f'20 {verb}',
             '30 PRINT"ZQ";0;"QZ":END', '900 PRINT"ZQ";ERR;"QZ":END']
        row = {}
        for side, c in SIDES.items():
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0,
                run_gap=12.0, cap_gap=4.0, timeout=420.0)[0] or "")
            row[side] = value(raw)
        out[verb] = row
        f = {s: ("<none>" if row[s] is None else
                 ("legal" if row[s] == 0 else f"ERR {row[s]}")) for s in SIDES}
        mark = "" if f["vg8020"] == f["zb"] else "   \U0001f534 DIFF"
        print(f"  {verb:9s} vg={f['vg8020']:9s} zb={f['zb']:9s}{mark}", flush=True)

    if out.get("REM", {}).get("vg8020") != 0 or out.get("REM", {}).get("zb") != 0:
        print(f"\n\U0001f534 THE `REM` CONTROL DID NOT READ 0 ({out.get('REM')}) -- "
              f"the fence or the typing is broken and no row is a reading.")
        return 2
    dis = [k for k, v in out.items() if v["vg8020"] != v["zb"]]
    blank = [k for k, v in out.items() if v["vg8020"] is None or v["zb"] is None]
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    if blank:
        print(f"    \U0001f534 {blank} produced NO reading on a side -- that is an "
              f"absence, not agreement, and each needs a reason before it is read "
              f"as anything [[an-unnamed-outcome-reads-as-no-outcome]].")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
