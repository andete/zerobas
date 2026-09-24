#!/usr/bin/env python3
r"""D-KWPAINT2 -- PAINT's fill-colour and border forms, measured with their own timing.

kwsweep's rows for these read `?nomarker` on BOTH machines: a flood outran the
capture window, so "the form fails" and "the capture came too early" were one
reading. Here the program announces its own completion (a program-written mark,
docs/spec-probe-mark.md, `sentinel_capture`), so the capture waits for the flood.

Readout per case: POINT inside the box (15,15) and OUTSIDE it (5,5).
  fill      box drawn in 11, PAINT(15,15),11      -> inside 11, outside 4
            (the border DEFAULTS to the fill colour, so the box stops it)
  border    box drawn in 15, PAINT(15,15),11,15   -> inside 11, outside 4
  leak      box drawn in 15, PAINT(15,15),11,7    -> the box is NOT the border:
            the flood passes it, outside 11 -- the proof the argument is READ
  control   box drawn in 15, no PAINT             -> inside 4, outside 4

NO-VERDICT (per-side readings); the rows it justifies go into kwsweep.
"""
import os, re, sys
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_R, "probes", "lib"), os.path.join(_R, "probes", "basic")]
import omsx_repl

MACHINES = ("Philips_VG_8020", os.environ.get("ZEROBAS_BASIC_MACHINE",
                                              "C-BIOS_MSX1_EU_REPACK_DISK"))
# 🔴 SCREEN 2 CANNOT CARRY THE BORDER FORM, measured: `PAINT(15,15),11,15` and
# `…,11,7` never finished on EITHER machine (no marker, no trapped error, in
# 120 s) -- in SCREEN 2 eight pixels share one colour pair, so painting 11
# recolours the box's own blocks, the 15-border ceases to exist and the flood
# runs away. SCREEN 3 (multicolour: each 4x4 block its own colour) is where a
# border that differs from the fill is a real boundary.
CASES = [
    ("control", ["SCREEN2", "LINE(10,10)-(20,20),15,B"]),
    ("fill",    ["SCREEN2", "LINE(10,10)-(20,20),11,B", "PAINT(15,15),11"]),
    ("s3-ctl",  ["SCREEN3", "LINE(40,40)-(80,80),15,B"]),
    ("s3-fill", ["SCREEN3", "LINE(40,40)-(80,80),11,B", "PAINT(60,60),11"]),
    ("s3-bord", ["SCREEN3", "LINE(40,40)-(80,80),15,B", "PAINT(60,60),11,15"]),
    ("s3-leak", ["SCREEN3", "LINE(40,40)-(80,80),15,B", "PAINT(60,60),11,7"]),
]
TAIL = ["A=POINT(15,15):B=POINT(5,5):IF PEEK(&HFCAF)=3 THEN A=POINT(60,60):B=POINT(20,20)", 'SCREEN0:PRINT"[P";A;B;"]"', "POKE&HE000,255"]

print(f"{'case':8} {'vg8020':14} {'zb':14}")
for name, body in CASES:
    got = []
    for m in MACHINES:
        raw = omsx_repl.run_case(m, "stored", body + TAIL, sentinel=(0xE000, 255),
                                 sentinel_capture=True, cap_gap=120.0,
                                 timeout=600.0) or ""
        f = re.findall(r"\[P([^\]]*)\]", raw)
        got.append(" ".join(f[-1].split()) if f else "<NO MARKER>")
    print(f"{name:8} {got[0]:14} {got[1]:14}", flush=True)
