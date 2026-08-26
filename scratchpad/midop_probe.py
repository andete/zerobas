#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-MIDOP — MID$()='s missing RHS, and whether D-PUSING's rule reaches a second verb.

`MID$(A$,2)=` is ERR 2 here and 24 on both references -- the last of the three
string rows D-MISSOP filed, and the one that survived D-MISSOP3's re-measurement.

`ex_mid_stmt` ends with `call str_eval / jr nc,ems_err_pop2`, which is the SAME
shared tail D-PUSING just split in `ex_print_using`: str_eval declines both for
"there is nothing here" and for "there is something and it is not a string", and
the references answered 24 and 13 to that pair. Whether MID$ follows is the
question -- and if it does NOT, that is worth more than the fix.

Readout `[ERR V]`: V = ASC(MID$(A$,2,1)) with A$="HELLO", so 69 is untouched and
81 is written. Predictions pinned in scratchpad/midop_predictions.md.
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
    """`A$="HELLO"` first; read ASC(MID$(A$,2,1)) after.

    69 (`E`) = untouched, 81 (`Q`) = the assignment happened. D-MISSOP's
    headline finding was that this class can COMPLETE AND WRITE -- `POKE` three
    ways and `VPOKE`, each turning a byte holding 99 into 0 -- so an ERR column
    alone is not enough for a statement whose whole job is a store.
    """
    return probe_signal.mark_ends([
        "10 ONERRORGOTO900",
        '15 A$="HELLO"',
        f"20 {stmt}",
        "25 V=ASC(MID$(A$,2,1))",
        '50 SCREEN0:CLS:PRINT"[";ERR;V;"]":END',
        '900 V=ASC(MID$(A$,2,1)):SCREEN0:CLS:PRINT"[";ERR;V;"]":END'])


CASES = {
    # --- the SAME shared tail D-PUSING split: str_eval declines both for
    # "nothing here" and for "not a string", and the references answered 24 and
    # 13 to that pair. Does MID$'s RHS follow?
    'm.none':     case('MID$(A$,2)='),
    'm.colon':    case('MID$(A$,2)=:PRINT1'),
    'm.num':      case('MID$(A$,2)=5'),
    'm.plus':     case('MID$(A$,2)=+'),
    # --- punctuation, which should stay ERR 2 --------------------------------
    'm.nocomma':  case('MID$(A$)="Q"'),
    'm.noclose':  case('MID$(A$,2="Q"'),
    'm.noeq':     case('MID$(A$,2)"Q"'),
    # --- controls: the write MUST still happen -------------------------------
    'm.ok':       case('MID$(A$,2)="Q"'),
    'm.ok3':      case('MID$(A$,2,1)="Q"'),
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
