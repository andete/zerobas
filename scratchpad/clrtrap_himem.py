#!/usr/bin/env python3
"""D-CLRTRAP -- does `CLEAR 200,` STORE the silent 0 before it aborts?

`basic/clear.asm` clr_himem is `call eval` / `ld (HIMEM),de`, and it never tests
FPERR. D-MISSOPFIX made that eval DEFER ERR 24 rather than raise it, so the
store still happens with DE = 0. That is an ARGUMENT until HIMEM is read back --
D-MISSOP's four silent memory writes are the same class and they were only
believed once a row printed the byte.

HIMEM is the standard MSX system variable at $FC4A, so all three machines can
be asked the same question. The read is in DIRECT MODE, after the program has
finished or aborted, because on zerobas the abort is UNTRAPPED and no program
line runs after it.
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
    'h.trail': case("CLEAR 200,"),         # THE SUBJECT
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
    return "SAME" if before == after else f"{before}->{after}"


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
