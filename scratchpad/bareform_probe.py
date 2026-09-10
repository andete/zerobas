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

# 🔴 THE FIRST CUT RAN ONE REFERENCE AND IT WAS THE WRONG ONE FOR HALF THE
# LIST. The VG-8020 is DISKLESS. `basic_probe_kwsweep.py` says what that costs, in
# as many words: "the default reference is a DISKLESS VG-8020, while the zerobas
# side is C-BIOS_MSX1_EU_REPACK_DISK, so every Disk-BASIC row was comparing 'no
# disk ROM' against 'disk ROM' and attributing the difference to zerobas." I read
# that file the same evening and made the mistake anyway: D-BAREFORM's first table
# reported KILL/NAME/FIELD/LSET/RSET as zerobas divergences when the CF-3300
# AGREES with zerobas on them.
# 🎯 SO BOTH REFERENCES RUN ON EVERY ROW NOW, and a row where they disagree is
# reported as REFS-SPLIT rather than scored against zerobas.
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
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


# --- D-FACEPIN: the FACE, not just the row label, AND ONLY THE HALF THAT IS A
# --- MEASUREMENT -------------------------------------------------------------
# 🔴 A FILED FACE ROTS WITHOUT THE ROW CEASING TO DIVERGE. Same shape as
# `basic_probe_nodisk.PINNED`: pin the VALUES, RED on drift in EITHER direction.
# 🎯 BUT `CLOAD`'s REFERENCE SIDES ARE AN ABSENCE, NOT A READING. Both read
# `<none>` because `CLOAD` WAITS FOR TAPE and the capture window closes on a
# machine that is still blocked -- this probe says so itself, two lines below
# the table: "produced NO reading on a side -- an absence, not agreement".
# Pinning `<none>` would assert that the HARNESS goes on failing to read, which
# is a claim about the apparatus and not about the machine
# [[an-unnamed-outcome-reads-as-no-outcome]].
# 🟢 THE `zb` SIDE *IS* A MEASUREMENT: zerobas answers `legal` where the
# references cannot be read at all. So this row is HALF-PINNED -- which the
# per-side pin format allows and which is the honest shape for it. If zerobas
# ever starts blocking too, this goes red and somebody looks.
PINNED = {
    "CLOAD": {"zb": "legal"},        # measured 2026-09-10; refs deliberately unpinned
}


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
        f = {s_: ("<none>" if row[s_] is None else
                  ("legal" if row[s_] == 0 else f"ERR {row[s_]}")) for s_ in SIDES}
        if f["vg8020"] != f["cf3300"]:
            mark = "   \U0001f7e1 REFS-SPLIT"
        elif f["zb"] != f["cf3300"]:
            mark = "   \U0001f534 DIFF"
        else:
            mark = ""
        print(f"  {verb:9s} vg={f['vg8020']:9s} cf={f['cf3300']:9s} "
              f"zb={f['zb']:9s}{mark}", flush=True)

    if out.get("REM", {}).get("vg8020") != 0 or out.get("REM", {}).get("zb") != 0:
        print(f"\n\U0001f534 THE `REM` CONTROL DID NOT READ 0 ({out.get('REM')}) -- "
              f"the fence or the typing is broken and no row is a reading.")
        return 2
    split = [k for k, v in out.items() if v["vg8020"] != v["cf3300"]]
    dis = [k for k, v in out.items()
           if v["vg8020"] == v["cf3300"] and v["zb"] != v["cf3300"]]
    blank = [k for k, v in out.items() if any(v[s_] is None for s_ in SIDES)]
    drift = []
    for lbl, want in PINNED.items():
        for side, face in want.items():
            if lbl not in out or side not in out[lbl]:
                continue                  # row or side not run; not a drift
            v = out[lbl][side]
            got = "<none>" if v is None else ("legal" if v == 0 else f"ERR {v}")
            if got != face:
                drift.append(f"{lbl}[{side}]: pinned {face!r}, measured {got!r}")
    if drift:
        print("\n\U0001f534 PINNED FACE DRIFT -- the row may still diverge, but "
              "NOT to the face this tree has filed:")
        for d in drift:
            print(f"     {d}")
        print("  Re-read the owning entry: either the behaviour moved, or the "
              "filing was wrong when it was written.")
        return 2

    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    print(f"    REFS-SPLIT ({len(split)}): {split or 'none'} -- the two references "
          f"disagree, so\n    zerobas cannot be scored on these. Most are "
          f"Disk-BASIC verbs and the VG-8020\n    has no disk ROM.")
    if blank:
        print(f"    \U0001f534 {blank} produced NO reading on a side -- an absence, not "
              f"agreement, and each needs a reason "
              f"[[an-unnamed-outcome-reads-as-no-outcome]].")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
