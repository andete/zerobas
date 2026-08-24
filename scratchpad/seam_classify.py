#!/usr/bin/env python3
"""Seam classification -- ONE differential pass over the remaining candidate
verbs of the generic error-layer seam (TODO.md "the generic error-layer seam").

The user's efficiency point: batch the MEASUREMENT, not the edits. This probe
classifies each candidate trailing-token site as
  DELETABLE   -- reference does the EFFECT then raises ERR 2, and the resident
                 guards the cursor + jp exec_stmt (SWAP / PAINT shape), so
                 deleting the bespoke check delegates to exec_stmt's boundary;
  KEEP        -- reference raises BEFORE the effect (incomplete arg list), so
                 the check is correct as-is;
  RESTRUCTURE -- effect issued by a sub-ROM tenant whose result the resident
                 tests BEFORE the draw op (CIRCLE) -- a second flag, not a delete.

Each row reads an EFFECT column so "did it happen before the raise?" is measured,
not assumed:
  SPRITE  VPEEK(&H1B00)   sprite-0 Y attribute (SCREEN 2 attr table) -- placed?
  CIRCLE  POINT(30,50)    the left cardinal of a circle at (50,50) r=20 -- drawn?
  PLAY    PLAY(0)         notes queued in voice 0 -- did the voices start?

READOUT `[ERR EFFECT]` under ON ERROR GOTO 900. 🔴 THE REFERENCES DECIDE.
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


def prog(setup, stmt, read):
    p = ["10 ONERRORGOTO900"]
    if setup:
        p.append(f"15 {setup}")
    p += [f"20 {stmt}",
          f'30 P={read}:SCREEN0:CLS:PRINT"[";ERR;P;"]":END',
          f'900 P={read}:SCREEN0:CLS:PRINT"[";ERR;P;"]":END']
    return p


SPR_SETUP = "SCREEN2:SPRITE$(0)=STRING$(8,255)"
SPR_READ = "VPEEK(&H1B00)"          # sprite-0 Y attribute
CIR_READ = "POINT(30,50)"           # on the circle outline
PLAY_READ = "PLAY(0)"               # notes queued, voice 0

CASES = {
    # --- SPRITE (PUT SPRITE), candidate site :1250 (5th arg after complete) ---
    'sp.ok':    prog(SPR_SETUP, "PUTSPRITE0,(20,30),1,0", SPR_READ),   # placed
    'sp.none':  prog(SPR_SETUP, "PUTSPRITE1,(0,0),1,0", "VPEEK(&H1B00)"),  # sprite0 untouched
    'sp.5comma':prog(SPR_SETUP, "PUTSPRITE0,(20,30),1,0,", SPR_READ),  # trailing comma
    'sp.5arg':  prog(SPR_SETUP, "PUTSPRITE0,(20,30),1,0,9", SPR_READ), # real 5th arg
    'sp.incomp':prog(SPR_SETUP, "PUTSPRITE0,", SPR_READ),             # incomplete (KEEP?)
    # --- CIRCLE, the filed x.extra2 restructure candidate ---------------------
    'ci.ok':    prog("SCREEN2", "CIRCLE(50,50),20", CIR_READ),        # drawn -> on circle
    'ci.none':  prog("SCREEN2", "X=0", CIR_READ),                     # nothing drawn
    'ci.trail': prog("SCREEN2", "CIRCLE(50,50),20,15,0.1,6.2,1,", CIR_READ),  # trailing comma
    # --- PLAY, 4th voice (:73). effect = notes queued -------------------------
    'pl.ok':    prog(None, 'PLAY"cde"', PLAY_READ),                   # queued
    'pl.none':  prog(None, "X=0", PLAY_READ),                         # nothing queued
    'pl.4voice':prog(None, 'PLAY"cde","fga","bcd","efg"', PLAY_READ), # 4 voices
}

BR = re.compile(r"\[([^\]]*)\]")
NUM = re.compile(r"^[-0-9. ]*$")
ERRMSG = re.compile(r"(Missing operand|Syntax error|Illegal function call|"
                    r"Type mismatch|Overflow|Out of memory|Undefined line number|"
                    r"Division by zero|Bad file mode|File not found)\s+in\s+(\d+)")


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    txt = "".join(cap)
    for m in BR.finditer(txt):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split()) or "<EMPTY>"
    m = ERRMSG.search(txt)
    if m:
        return f"UNTRAPPED {m.group(1)} in {m.group(2)}"
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
                batch=False, boot=cfg["boot"], step=6.0, cap_gap=12.0,
                timeout=400.0)
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l:9s} {faces[s][l]!r}", flush=True)
    print()
    W = max(len(l) for l in labels)
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        line = f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
        if not refs:
            print(line + "   (zb only)"); continue
        if len(refs) != 1:
            print(line + "   !! REFS DISAGREE"); continue
        if any("<NO" in v for v in vals.values()):
            print(line + "   .... NOT MEASURED"); continue
        print(line + ("   *** DIFF" if vals["zb"] not in refs else ""))


if __name__ == "__main__":
    main()
