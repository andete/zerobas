#!/usr/bin/env python3
"""D-CIRCMISS sibling sweep -- is the dangling comma one rule at MORE than CIRCLE?

D-MISSOP's whole lesson was that a filed one-verb defect was one rule at sixteen
slots. CIRCLE's hole (mechanism 2: the VERB'S OWN GRAMMAR swallows the dangling
comma, so `eval` is never called and the evaluator fix cannot see it) is not
obviously CIRCLE-specific.

A tree-wide scan of every `cp COLON` site whose jump target is NOT an error
routine finds exactly two other statement-grammar candidates with CIRCLE's
shape -- an optional-argument slot entered AFTER its comma has been consumed:

  basic/graphics.asm:708  PAINT's C slot  -> ep_default_b
  basic/graphics.asm:727  PAINT's B slot  -> ep_default_b
  basic/clear.asm:49      CLEAR's 2nd arg -> clr_done

⚠️ SHAPE IS NOT A VERDICT. D-LINERR measured LINE's colour slot as ERR 24 and
LINE's BOX slot -- one field along, same statement -- as ERR 2, and D-MISSOP
measured `COLOR 15,` as COMPLETING on all three machines. Every slot is its own
question. This probe asks it.

Readout `[ERR R]`, R = POINT(50,50) = the PAINT seed, inside a 15-coloured box
drawn by the setup line. Background 4, FORCLR 15. So R=4 means nothing painted.
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


def gcase(stmt, read="R=POINT(50,50)"):
    return ["10 ONERRORGOTO900",
            "15 SCREEN2:LINE(40,40)-(60,60),15,B",
            f"20 {stmt}",
            f'30 {read}:SCREEN0:CLS:PRINT"[";ERR;R;"]":END',
            f'900 {read}:SCREEN0:CLS:PRINT"[";ERR;R;"]":END']


def tcase(stmt, read="R=0"):
    return ["10 ONERRORGOTO900",
            f"20 {stmt}",
            f'30 {read}:PRINT"[";ERR;R;"]":END',
            f'900 {read}:PRINT"[";ERR;R;"]":END']


CASES = {
    # --- PAINT: the same shape as CIRCLE, at two slots ---------------------
    'p.colour':  gcase("PAINT(50,50),"),
    'p.b':       gcase("PAINT(50,50),5,"),
    'p.kcolour': gcase("PAINT(50,50),:A=1"),
    'p.kb':      gcase("PAINT(50,50),5,:A=1"),
    # --- PAINT: the legitimate omission, and the control -------------------
    'p.omit':    gcase("PAINT(50,50),,15"),
    'p.ok':      gcase("PAINT(50,50),5,15"),
    # --- CLEAR: the third candidate ----------------------------------------
    'q.trail':   tcase("CLEAR 200,"),
    'q.kcolon':  tcase("CLEAR 200,:A=1"),
    'q.ok':      tcase("CLEAR 200"),
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
