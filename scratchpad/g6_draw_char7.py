#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G6 DRAW char round 7: shared-attribute test, corrected.

Round 6's T1/T2 each had a COLOURLESS PSET between the colour-setting statement
and the measured DRAW -- and a colourless graphics statement re-stamps the
attribute with FORCLR, so those runs could not discriminate. Here the cursor is
moved with DRAW's own "BM" (blank move), so NOTHING between re-stamps:

  T1b  LINE ...,4  then DRAW"BM.. R8"            -> fg 4 = shared attribute cell
  T4   PSET ..,4   then DRAW"BM.. R8"            -> same question, other setter
  T2b  DRAW"C6R8" : SCREEN2 : DRAW"BM.. R8"      -> does SCREEN 2 re-stamp?
  T5   DRAW"C6R8" then LINE with NO colour       -> (control) expect FORCLR 15
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl
REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
CTAB = 0x2000

def seg_at(x, y):
    o = (y >> 3)*256 + (x >> 3)*8 + (y & 7)
    return [(o, 1), (CTAB + o, 1)]

CASES = [
    ("T1b_line4_draw",  ['COLOR15,4,7:SCREEN2',
                         'LINE(100,100)-(108,100),4:DRAW"BM100,140R8"', 'GOTO 30'], (100, 140)),
    ("T4_pset4_draw",   ['COLOR15,4,7:SCREEN2',
                         'PSET(100,100),4:DRAW"BM100,140R8"', 'GOTO 30'], (100, 140)),
    ("T2b_c6_scr2_draw",['COLOR15,4,7:SCREEN2',
                         'PSET(100,100):DRAW"C6R8":SCREEN2:DRAW"BM100,140R8"', 'GOTO 30'], (100, 140)),
    ("T5_c6_then_line", ['COLOR15,4,7:SCREEN2',
                         'PSET(100,100):DRAW"C6R8":LINE(100,140)-(108,140)', 'GOTO 30'], (100, 140)),
]
for label, prog, (x, y) in CASES:
    raw = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                              capture=("vram_segs", seg_at(x, y)), cart=None)[0]
    print(f"  {label:20s} @({x},{y}) -> {raw}")
