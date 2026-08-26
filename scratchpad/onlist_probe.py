#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ONLIST — `ON n GOTO` with no target list SILENTLY COMPLETES.

D-MISSOP3 found `ON 1 GOTO` and `ON 1 GOSUB` reading 0 where both references say
2. The root is `eon_seek_nth` (basic/program.asm:2083): `esn_nocf` is a SHARED
TAIL with FIVE incoming `jr nz` instructions, and they do not mean the same
thing --

    :2091  esn_p1     `cp LINENO_TOKEN` fails   -> NO LIST AT ALL, or a comma
                                                   followed by a non-lineno
    :2104  esn_p1     no comma after an entry   -> list SHORTER than N: LEGAL
    :2129  esn_scan   no entries at all (N=0)   -> NO LIST AT ALL
    :2138  esn_scan_lp no more commas           -> end of list: LEGAL
    :2143  esn_scan_lp comma then non-lineno    -> malformed

...so "an empty list" and "N is past the end of a real list" arrive at one
`or a / ret` and become the same silent fall-through. Only the second is
documented MSX behaviour. This is the same shape as D-EVFERR's `ev_f_err` and
D-MISSOPFIX's, and the same discipline applies: 🔴 ENUMERATE THE JUMPS AS
INSTRUCTIONS AND MEASURE EACH SITE BEFORE SITING ANYTHING.

🎯 THE READOUT HAS TO TELL *BRANCHED* FROM *FELL THROUGH*, which an ERR code
cannot: `ON 5 GOTO 40` and `ON 1 GOTO 40` both end at ERR 0. So the program puts
a flag line BETWEEN the statement and its target:

    [ERR F]   F=0 aborted before line 25 | F=1 fell through | F=2 branched

Predictions pinned in scratchpad/onlist_predictions.md before this ran once.
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


def case(stmt):
    return probe_signal.mark_ends([
        "10 ONERRORGOTO900",
        f"20 {stmt}",
        "25 F=1",                       # reached only by FALLING THROUGH
        "30 GOTO 50",
        "40 F=2",                       # reached only by BRANCHING
        '50 SCREEN0:CLS:PRINT"[";ERR;F;"]":END',
        '900 SCREEN0:CLS:PRINT"[";ERR;F;"]":END'])


CASES = {
    # --- the two rows D-MISSOP3 found, plus their N variants ------------------
    'o.nolist':     case('ON 1 GOTO'),        # :2091, first iteration
    'o.nolistsub':  case('ON 1 GOSUB'),
    'o.zeronolist': case('ON 0 GOTO'),        # :2129 -- the N=0 short circuit
    'o.overnolist': case('ON 5 GOTO'),        # :2091 with N past the (empty) end
    # --- the LEGAL fall-throughs that must NOT move ---------------------------
    'o.short':      case('ON 5 GOTO 40'),     # :2104 -- list shorter than N
    'o.zero':       case('ON 0 GOTO 40'),     # :2138 -- N=0 with a real list
    # --- malformed TAILS: does a list that STARTS well have to END well? ------
    'o.trail1':     case('ON 1 GOTO 40,'),    # Nth found, then a dangling comma
    'o.trail0':     case('ON 0 GOTO 40,'),    # :2143
    'o.badafter':   case('ON 1 GOTO 40,X'),   # comma then a non-lineno
    # --- ROUND 2: the N-DISCRIMINATION rows the baseline demanded -------------
    # `ON 1 GOTO` is ERR 2 and `ON 5 GOTO` is SILENT -- the SAME zerobas
    # instruction (:2091, first iteration) on both. So the reference is not
    # validating the list; it demands a line number ONLY at the position it is
    # actually about to USE. These rows test that as a rule:
    #   ERR 2 iff the Nth position is REACHED and what is there is not a lineno.
    'o.n2trail':    case('ON 2 GOTO 40,'),    # comma CONSUMED, position 2 demanded
    'o.n5trail':    case('ON 5 GOTO 40,'),    # comma consumed, position 5 unreachable
    'o.n2short':    case('ON 2 GOTO 40'),     # no comma -> list shorter, legal
    'o.n2ok':       case('ON 2 GOTO 50,40'),  # control: position 2 exists
    # --- controls -------------------------------------------------------------
    'o.ok':         case('ON 1 GOTO 40'),
    'o.gosubok':    case('ON 1 GOSUB 40'),
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
    faces, tally = {}, probe_signal.Tally()
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
            print(f"  ran {s:7s} {l:<13s} -> {faces[s][l]!r}", flush=True)
    print()
    W = max(len(l) for l in labels)
    ndiff = nmeas = 0
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        line = f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
        if not refs:
            print(line + "   (zb only)"); continue
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
