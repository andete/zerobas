#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-MISSOP3 — the THREE string rows D-MISSOPFIX left, and the denominator
TODO.md:7215 (T-051734) says out loud is still a sample.

Two jobs, and the first one is the filed item's own justification:

  1. `KEY1,` / `A$=` / `MID$(A$,2)=` read ERR 2 where both references say 24.
     TODO.md justifies leaving them with: *"Predicted not to move under the
     evaluator fix, and they did not -- they reach an abort by ANOTHER ROUTE."*
     🔴 THAT SENTENCE HAS TO BE RE-RUN, NOT RE-READ. D-EVFERR (2026-08-26) has
     since changed which deferred code reaches the statement boundary at several
     factor sites, and its knife K-EV2 showed `A$=(1+2` moving to 24 when the
     paren site's code changed -- i.e. missing.asm's `els_tc_common` DOES read
     the deferred code. So "they reach an abort by another route" is a claim
     about today's tree that was measured on a different one.

  2. TODO.md:7215 (T-051734) names the verbs that are UNMEASURED, NOT GREEN: SWAP, ON n
     GOTO, FIELD, PRINT#, INPUT, PLAY, DRAW, OPEN, WIDTH and PRINT USING. Each
     gets the row where a REQUIRED slot ends where a value was needed, which is
     the exact shape the D-MISSOP rule calls ERR 24.

⚠️ NO BARE `INPUT` / `LINE INPUT` ROW. Those are VALID statements that prompt and
WAIT, so the row would hang rather than measure -- `INPUT#` (missing channel) is
the reachable parse error in that family, and the waiting forms are left named
rather than silently dropped.

Readout is `[ERR]`: 0 when the statement COMPLETED, else the MSX error code.
Predictions pinned in scratchpad/missop3_predictions.md before this ran once.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_signal                                               # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}


def case(stmt, setup=None):
    prog = ["10 ONERRORGOTO900"]
    if setup:
        prog.append(f"15 {setup}")
    prog += [f"20 {stmt}",
             '30 SCREEN0:CLS:PRINT"[";ERR;"]":END',
             '900 SCREEN0:CLS:PRINT"[";ERR;"]":END']
    return probe_signal.mark_ends(prog)


CASES = {
    # --- the three rows the filed item still carries, plus §6.1's fourth ------
    'r.key':      case('KEY1,'),
    'r.lets':     case('A$='),
    'r.letsp':    case('A$=+'),
    'r.midd':     case('MID$(A$,2)=', setup='A$="HELLO"'),
    'r.keyok':    case('KEY1,"X"'),
    'r.letsok':   case('A$="X"'),
    'r.middok':   case('MID$(A$,2)="Q"', setup='A$="HELLO"'),
    # --- the denominator TODO.md:7215 (T-051734) names as UNMEASURED, NOT GREEN -----------
    'd.swap':     case('SWAP A,'),
    'd.ongoto':   case('ON 1 GOTO'),
    'd.width':    case('WIDTH'),
    'd.draw':     case('DRAW'),
    'd.play':     case('PLAY'),
    'd.open':     case('OPEN'),
    'd.using':    case('PRINT USING'),
    'd.inputch':  case('INPUT#'),
    'd.field':    case('FIELD'),
    'd.printch':  case('PRINT#'),
    # --- ROUND 2 separators, added after the baseline refuted the rule -------
    # The baseline predicted "every required slot ending where a value was
    # needed is 24 on both references" as ONE RULE. `SWAP A,` is 2 and `DRAW`
    # is 5 on BOTH, so it is not. These rows ask what the true partition is.
    'd.swapblank': case('SWAP ,B', setup='B=2'),   # the missing thing is a NAME
    'd.drawscr2': case('SCREEN2:DRAW'),            # is DRAW's 5 a MODE artifact?
    'd.drawok2':  case('SCREEN2:DRAW"R10"'),
    'd.usingfmt': case('PRINT USING"##"'),         # format present, value absent
    'd.ongosub':  case('ON 1 GOSUB'),              # mirror of ON..GOTO
    'd.ongotook': case('ON 1 GOTO 30'),
    # KEY's assignment form -- the baseline's r.keyok CONTROL failed on zb
    'r.keylist':  case('KEY LIST'),
    'r.keyoff':   case('KEY OFF'),
    # --- controls: the same verbs, well formed -------------------------------
    'd.swapok':   case('SWAP A,B', setup='A=1:B=2'),
    'd.widthok':  case('WIDTH 32'),
    'd.playok':   case('PLAY"C"'),
}

BR = re.compile(r"\[([^\]]*)\]")
NUM = re.compile(r"^[-0-9. ]*$")


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    for m in BR.finditer("".join(cap)):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split()) or "<EMPTY>"
    return "<NO OUTPUT>"


def main():
    only, sides = None, ["vg8020", "cf3300", "zb"]
    for a in sys.argv[1:]:
        if a.startswith("--sides="):
            sides = [x for x in a.split("=", 1)[1].split(",") if x in SIDES]
        else:
            only = a.split(",")
    labels = [l for l in CASES if not only or any(o in l for o in only)]
    faces = {}
    tally = probe_signal.Tally()
    for s in sides:
        cfg = SIDES[s]
        faces[s] = {}
        for l in labels:
            out = {}
            caps = omsx_repl.run_cases(
                cfg["machine"],
                [("direct", list(cfg["reset"]) + CASES[l] + ["RUN"])],
                batch=False, boot=cfg["boot"], step=3.0, cap_gap=8.0,
                timeout=300.0, **probe_signal.kwargs(out))
            tally.add(out, label=f"{s}/{l}")
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l:<11s} -> {faces[s][l]!r}", flush=True)
    print()
    W = max(len(l) for l in labels)
    ndiff = nmeas = 0
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        line = f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
        if not refs:
            print(line + "   (zb only)")
            continue
        if len(refs) != 1:
            note = "   ⚠️ THE REFERENCES DISAGREE — not a want"
        elif any("<NO" in v for v in vals.values()):
            note = "   .... NOT MEASURED"
        elif vals["zb"] not in refs:
            note = "   🔴 DIFF"; ndiff += 1; nmeas += 1
        else:
            note = "   ✅"; nmeas += 1
        print(line + note)
    print(f"\n  {nmeas} scored, {ndiff} DIFF, {len(labels) - nmeas} not measured")
    print(tally.line())
    return 1 if nmeas != len(labels) else 0


if __name__ == "__main__":
    sys.exit(main())
