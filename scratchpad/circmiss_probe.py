#!/usr/bin/env python3
"""D-CIRCMISS -- CIRCLE's dangling-comma slots, and the LEGITIMATE omissions.

D-MISSOPFIX closed `Missing operand` at the evaluator (13 rows) and could not
touch CIRCLE: its grammar walk is a sub-ROM page-1 tenant (sub/circleparse.asm)
that decides for itself that an optional argument is absent, so `eval` is never
called and `ev_f_missop` never sees the slot. docs/spec-basic-missop.md Sec 16
measured four such slots, all `24` on both references and `0` here.

THIS PROBE EXISTS TO STOP THE OBVIOUS FIX FROM BREAKING THE LANGUAGE. An
omitted optional argument is LEGAL MSX BASIC in two shapes that must keep
drawing:

  o.none    CIRCLE(50,50),20              no optional fields at all
  o.*       CIRCLE(50,50),20,,0.1,6.2     a slot omitted BETWEEN commas

Sec 16's `c.ok` row covers neither, and the spec says so. Four `o.*` rows here do.

Readout is `[ERR R]`:
  ERR  0 = the statement COMPLETED, else the MSX error code it aborted with.
  R    POINT(30,50) -- the left cardinal point of the radius-20 circle, read
       BEFORE the exit line's SCREEN0:CLS (CLS wipes VRAM). SCREEN 2 background
       is BAKCLR=4 and FORCLR=15, so R separates "drew nothing" (4) from "drew
       in the default colour" (15) from "drew in the named colour" (5).
       Both arc boundaries used (0.1 and 6.2 rad) sit near angle 0, so angle pi
       -- the point read -- is deep inside every arc, never on a boundary.
  A non-numeric fence scores <NO OUTPUT> / NOT MEASURED, never agreement
  (trapsvc-echo-fence: a run that never reaches its PRINT reads the TYPED ECHO).
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

READ = "R=POINT(30,50)"


def case(stmt):
    return ["10 ONERRORGOTO900",
            "15 SCREEN2",
            f"20 {stmt}",
            f'30 {READ}:SCREEN0:CLS:PRINT"[";ERR;R;"]":END',
            f'900 {READ}:SCREEN0:CLS:PRINT"[";ERR;R;"]":END']


CASES = {
    # --- the class: a comma consumed, then end of statement -----------------
    'c.colour': case("CIRCLE(50,50),20,"),
    'c.start':  case("CIRCLE(50,50),20,5,"),
    'c.end':    case("CIRCLE(50,50),20,5,0.1,"),
    'c.aspect': case("CIRCLE(50,50),20,5,0.1,6.2,"),
    # --- the same four slots, the `cp COLON` arm (UNMEASURED before today) --
    'k.colour': case("CIRCLE(50,50),20,:A=1"),
    'k.start':  case("CIRCLE(50,50),20,5,:A=1"),
    'k.end':    case("CIRCLE(50,50),20,5,0.1,:A=1"),
    'k.aspect': case("CIRCLE(50,50),20,5,0.1,6.2,:A=1"),
    # --- THE TRAP: legitimate omissions that must keep drawing -------------
    'o.none':   case("CIRCLE(50,50),20"),
    'o.colour': case("CIRCLE(50,50),20,,0.1,6.2"),
    'o.start':  case("CIRCLE(50,50),20,5,,6.2"),
    'o.end':    case("CIRCLE(50,50),20,5,0.1,,1"),
    # --- the far edge of the grammar: one slot too many --------------------
    'x.extra':  case("CIRCLE(50,50),20,5,0.1,6.2,,"),
    'x.extra2': case("CIRCLE(50,50),20,5,0.1,6.2,1,"),
    # --- the MANDATORY radius: this one DOES go through the resident eval --
    'r.miss':   case("CIRCLE(50,50),"),
    'r.nocomma': case("CIRCLE(50,50)"),
    # --- control: every slot present ---------------------------------------
    'c.ok':     case("CIRCLE(50,50),20,5,0.1,6.2,1"),
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
    for s in sides:
        cfg = SIDES[s]
        faces[s] = {}
        for l in labels:
            caps = omsx_repl.run_cases(
                cfg["machine"],
                [("direct", list(cfg["reset"]) + CASES[l] + ["RUN"])],
                batch=False, boot=cfg["boot"], step=3.0, cap_gap=8.0,
                timeout=300.0)
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l:10s} {faces[s][l]!r}", flush=True)
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
            print(line + "   !! THE REFERENCES DISAGREE -- not a want")
            continue
        if any("<NO" in v for v in vals.values()):
            print(line + "   .... NOT MEASURED")
            continue
        nmeas += 1
        if vals["zb"] not in refs:
            ndiff += 1
            print(line + "   *** DIFF")
        else:
            print(line)
    print(f"\nROWS: {len(labels)} printed, {nmeas} scored -- {ndiff} DIFF")


if __name__ == "__main__":
    main()
