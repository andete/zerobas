#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KEYSTR scout — WHERE does `KEY n,"str"` put the string, and what shape?

TODO.md files `KEY n,"str"` / `KEY LIST` as unimplemented: `KEY1,"X"` reads
0 / 0 / 2 (both references complete it, basic/screen.asm:294 is `jp stmt_error`).
That is an ERROR-CODE reading and it says nothing about what the statement is
supposed to DO, which is what any implementation has to match.

🔴 THE ADDRESS IS NOT ASSUMED. zerobas has no FNKSTR equate at all -- the name
appears only in comments (basic/keytrap.asm) -- so this probe PLANTS a distinctive
string and SEARCHES for it rather than PEEKing a guessed address. A guessed
address that reads plausible bytes is exactly the shape that gets believed.

Readout `[ERR B T]`:
  ERR  0 if the statement completed, else the MSX error code
  B    the address where the planted string was found, 0 if it was not
  T    the byte immediately AFTER the planted string (the terminator/pad question)

On zerobas every KEY-assignment row aborts, so its search runs via `RESUME` and
is expected to find nothing -- B=0 there is the divergence restated, and the
REFERENCE columns are the specification this slice needs.
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


def case(stmt, addr):
    """Plant `stmt`, then read FOUR bytes at `addr` -- no loop at all.

    🔴 THE LOOP WAS THE INSTRUMENT FAULT, AND IT COST THREE RUNS. A BASIC scan of
    $F800..$FFF0 never reached its END on any machine: every row came back
    `<NO OUTPUT>` with `0 on signal, N fell back`, which is the harness saying
    "the program never got there" and NOT "the machine disagreed". A no-loop
    smoke row (`k.smoke`) returned `0 1234 7` captured on signal, which is what
    separated the SCAFFOLD from the SEARCH. Two real faults were found and fixed
    on the way -- `RESUME 30` pointed the handler INTO the code that could fail
    (an error inside the scan resumed back into the scan, forever), and the
    decimal bound 63488 promoted the whole loop to single precision -- and the
    loop STILL did not finish, so the strategy went rather than the details.

    🎯 SO THE ADDRESS IS A HYPOTHESIS AND THE PLANT IS THE TEST. `KEY n,"ZQX"`
    writes three bytes that do not occur together by accident; reading back
    90,81,88 at a named address is a MEASUREMENT of that address, not an
    assumption about it. A control row plants nothing and must NOT read them.
    """
    return probe_signal.mark_ends([
        "10 ONERRORGOTO900",
        f"20 {stmt}",
        f"30 E=ERR:P={addr}",
        "40 A=PEEK(P):B=PEEK(P+1):C=PEEK(P+2):D=PEEK(P+3)",
        '60 SCREEN0:CLS:PRINT"[";E;A;B;C;D;"]":END',
        "900 RESUME 30"])


# FNKSTR is documented at $F87F in the MSX system-variable map, 10 slots of 16
# bytes. Both halves of that -- the base AND the stride -- are hypotheses here,
# and each has a row that can refute it.
F1, F2, F10 = 0xF87F, 0xF87F + 16, 0xF87F + 9 * 16

CASES = {
    'k.slot1':  case('KEY 1,"ZQX"', F1),
    'k.slot2':  case('KEY 2,"ZQX"', F2),
    'k.slot10': case('KEY 10,"ZQX"', F10),
    'k.s1at2':  case('KEY 1,"ZQX"', F2),    # refutes the STRIDE if it hits
    'k.none':   case('E=0', F1),            # control: nothing planted
}

# 🔴 INSTRUMENT FIRST -- the row that proved the scaffold when everything else
# was <NO OUTPUT>. Kept, because a probe that once lied should keep its control.
CASES['k.smoke'] = probe_signal.mark_ends([
    "10 ONERRORGOTO900",
    "20 E=0:A=1:B=2:C=3:D=4",
    '60 SCREEN0:CLS:PRINT"[";E;A;B;C;D;"]":END',
    "900 RESUME 60"])


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
                batch=False, boot=cfg["boot"], step=3.0,
                cap_gap=float(os.environ.get("KEYSTR_GAP", "20")),
                timeout=300.0, **probe_signal.kwargs(out))
            tally.add(out, label=f"{s}/{l}")
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l:<9s} -> {faces[s][l]!r}", flush=True)
    print()
    W = max(len(l) for l in labels)
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        line = f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
        if len(refs) != 1:
            line += "   ⚠️ THE REFERENCES DISAGREE — not a want"
        elif any("<NO" in v for v in vals.values()):
            line += "   .... NOT MEASURED"
        elif vals["zb"] not in refs:
            line += "   🔴 DIFF"
        else:
            line += "   ✅"
        print(line)
    print()
    print(tally.line())
    return 0


if __name__ == "__main__":
    sys.exit(main())
