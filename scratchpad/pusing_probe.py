#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PUSING — PRINT USING has TWO defects, and one of them is silent.

D-MISSOP3 measured `PRINT USING` at 24/24/2 and `PRINT USING"##"` at 2/2/0.
Different sites, different shapes:

  * the FORMAT operand reaches `jp nc,stmt_error` (printusing.asm:51) from TWO
    entry conditions -- nothing at all, and something that is not a string;
  * a format CONTAINING A FIELD with no value list reaches `pu_endlist` and
    COMPLETES, where both references raise.

Readout `[ERR L]` -- L is CSRLIN after the statement, with the cursor parked at
row 5 first, because an ERR code cannot tell a silent no-op from a silent print.

Predictions pinned in scratchpad/pusing_predictions.md before this ran once.
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
    """Park the cursor at row 5, run `stmt`, then read CSRLIN before anything
    clears the screen.

    🎯 AN ERR CODE ALONE CANNOT TELL A SILENT NO-OP FROM A SILENT PRINT, and
    this verb's whole job is printing. `PRINT USING"##"` completes with ERR 0
    here and ERR 2 on both references -- but "completes" covers both "emitted
    nothing" and "emitted a line", and the fix is a different shape depending on
    which. L=5 is nothing printed, L=6 is one line.
    """
    return probe_signal.mark_ends([
        "10 ONERRORGOTO900",
        "15 SCREEN0:CLS:LOCATE0,5",
        f"20 {stmt}",
        "25 L=CSRLIN",
        '50 SCREEN0:CLS:PRINT"[";ERR;L;"]":END',
        '900 L=CSRLIN:SCREEN0:CLS:PRINT"[";ERR;L;"]":END'])


CASES = {
    # --- defect 1: the FORMAT operand. printusing.asm:51 `jp nc,stmt_error` is
    # reached both when there is NOTHING here and when there is something that
    # is not a string -- one instruction, two meanings.
    'u.none':     case('PRINT USING'),
    'u.colon':    case('PRINT USING:PRINT1'),
    'u.num':      case('PRINT USING 5'),
    'u.numsemi':  case('PRINT USING 5;1'),
    # --- defect 2: a format that CONTAINS A FIELD with no value list ---------
    'u.fmtonly':  case('PRINT USING"##"'),
    'u.fmtsemi':  case('PRINT USING"##";'),
    # --- the rows that keep defect 2 NARROW: a field-less format is complete
    # on its own, and zerobas already distinguishes that at pu_has_field.
    'u.lit':      case('PRINT USING"abc"'),
    'u.litsemi':  case('PRINT USING"abc";'),
    # --- ROUND 2: the row that decides whether pu_literal_only is DEAD -------
    # pu_literal_only (printusing.asm:139) has exactly ONE incoming jump. If a
    # field-less format errors in every case, that block goes unreachable and
    # `make deadcode` refuses the build -- so the fix would also be a carve.
    'u.litval':   case('PRINT USING"abc";5'),
    'u.comma':    case('PRINT USING"##",5'),
    'u.emptyonly': case('PRINT USING""'),
    'u.emptysemi': case('PRINT USING"";5'),
    'u.strfield': case('PRINT USING"!";"AB"'),
    'u.numnosemi': case('PRINT USING"##"5'),
    # --- ROUND 3: two rows that BOUND the fix --------------------------------
    # `,` is rejected as the FORMAT separator (u.comma). pu_msep_chk accepts it
    # between VALUES too, which is a DIFFERENT grammatical position and was not
    # measured -- do not carry one row's answer into the other.
    'u.valcomma': case('PRINT USING"##";1,2'),
    # ex_print_using is shared by PRINT, LPRINT and PRINT# -- the fix serves all
    # three, so at least one non-PRINT entry needs a row.
    'u.chan':     case('OPEN"CRT:"FOROUTPUTAS#1:PRINT#1,USING"##";5'),
    # --- controls ------------------------------------------------------------
    'u.ok':       case('PRINT USING"##";5'),
    'u.ok2':      case('PRINT USING"###";12'),
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
