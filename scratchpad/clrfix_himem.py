#!/usr/bin/env python3
"""D-CLRFIX -- does CLEAR's HIMEM slot WRITE before it aborts? Extended row set.

Round 1 (D-CLRTRAP) measured `CLEAR 200,` writing HIMEM = 0 on zerobas while
both references leave it alone. This adds the LEADING-comma form and the other
fault codes the same unguarded slot can carry, because a guard that fixes ERR 24
and leaves ERR 11 / ERR 13 / ERR 6 writing is a guard that fixed one row.

🔴 THE ABSOLUTE VALUE OF HIMEM IS MACHINE-SPECIFIC AND THEREFORE UNSCOREABLE --
the VG-8020 boots it at 62336 and the CF-3300 at 56951. Each case prints HIMEM
BEFORE and AFTER, in direct mode either side of the RUN, and the row scores the
DELTA. The read is in DIRECT MODE because on zerobas the abort is untrapped and
no program line runs after it.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}

READ = 'PRINT"[";PEEK(&HFC4A)+256*PEEK(&HFC4B);"]"'

# 🔴 THE ABSOLUTE VALUE OF HIMEM IS MACHINE-SPECIFIC AND THEREFORE UNSCOREABLE.
# Round 1 printed one fence and 3 of its 4 rows died as "THE REFERENCES
# DISAGREE" -- correctly, because the VG-8020 boots HIMEM at 62336 and the
# CF-3300 at 56951 (its disk ROM takes the RAM). The QUESTION was never the
# value, it was whether the statement WROTE. So each case now prints HIMEM
# BEFORE and AFTER, in direct mode either side of the RUN, and the row scores
# the DELTA -- which every machine can be compared on.


def case(stmt):
    if stmt is None:                       # no CLEAR at all: the control pair
        return [READ, READ]
    return [READ,                          # DIRECT MODE, before
            "10 ONERRORGOTO900",
            f"20 {stmt}",
            '30 END',
            '900 END',
            "RUN",
            READ]                          # DIRECT MODE, after the abort


CASES = {
    'h.none':  case(None),                 # baseline: HIMEM as the machine booted
    'h.ok':    case("CLEAR 200"),          # control: a CLEAR with no 2nd argument
    'h.set':   case("CLEAR 200,&H9000"),   # control: a REAL ceiling, so the row
                                           # can tell "HIMEM is writable here" from
                                           # "this machine ignores the argument"
    'h.trail': case("CLEAR 200,"),         # SUBJECT 1: the trailing comma
    'h.comma': case("CLEAR ,200"),         # SUBJECT 2: the LEADING comma -- a form
                                           # neither reference accepts, so on the
                                           # references nothing can be written
    # --- the SAME unguarded slot, other fault codes. A guard that closes ERR 24
    # and leaves these writing has closed a ROW, not the slot.
    'h.div':   case("CLEAR 200,1/0"),      # FPERR=2
    'h.str':   case('CLEAR 200,"x"'),      # a TYPE fault
    'h.ovf':   case("CLEAR 200,70000"),    # past int16
    'h.hd000': case("CLEAR ,&HD000"),      # the characterization's own form
    'h.neg':   case("CLEAR 200,-1"),       # the negative end of the slot
}

BR = re.compile(r"\[([^\]]*)\]")
NUM = re.compile(r"^[-0-9. ]*$")


def face(cap):
    """SAME, or `before->after`. Two fences are required; one is not a delta."""
    if cap is None:
        return "<NO CAPTURE>"
    vals = [" ".join(m.group(1).split())
            for m in BR.finditer("".join(cap)) if NUM.match(m.group(1))]
    vals = [v for v in vals if v]
    if len(vals) < 2:
        return "<NO OUTPUT>"               # one fence cannot answer "did it write"
    before, after = vals[0], vals[-1]
    # 🔴 THE *BEFORE* VALUE IS MACHINE-SPECIFIC AND MUST NOT ENTER THE FACE.
    # D-CLRTRAP got halfway here: it printed HIMEM before AND after (which is
    # what makes the delta knowable) but then put BOTH in the face, so `h.set`
    # read '62336->36864' on the VG-8020 and '56951->36864' on the CF-3300 and
    # scored "THE REFERENCES DISAGREE" -- an unscoreable positive control. The
    # question is "did it write, and to what", and only the AFTER value answers
    # it. 7 scored -> 8 for free ([[an-unnamed-outcome-reads-as-no-outcome]]).
    return "SAME" if before == after else f"->{after}"


def main():
    sides = ["vg8020", "cf3300", "zb"]
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--sides="):
            sides = [x for x in a.split("=", 1)[1].split(",") if x in SIDES]
        else:
            only = a.split(",")
    labels = [l for l in CASES if not only or any(o in l for o in only)]
    faces = {}
    for s in sides:
        cfg = SIDES[s]
        faces[s] = {}
        for l in labels:
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + CASES[l])],
                batch=False, boot=cfg["boot"], step=3.0, cap_gap=8.0,
                timeout=300.0)
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l:9s} {faces[s][l]!r}", flush=True)
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
            print(line + "   !! THE REFERENCES DISAGREE -- not a want"); continue
        if any("<NO" in v for v in vals.values()):
            print(line + "   .... NOT MEASURED"); continue
        nmeas += 1
        if vals["zb"] not in refs:
            ndiff += 1; print(line + "   *** DIFF")
        else:
            print(line)
    print(f"\nROWS: {len(labels)} printed, {nmeas} scored -- {ndiff} DIFF")


if __name__ == "__main__":
    main()
