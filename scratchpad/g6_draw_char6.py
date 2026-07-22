#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G6 DRAW char round 6: is DRAW's colour the SHARED graphics attribute cell?

Rounds 2/4/5 showed: C persists into the next DRAW in the same run, but a later
colourless LINE draws in FORCLR, and after SCREEN 2 (new run) DRAW is back to
FORCLR. That is all explained if DRAW's C writes the SHARED graphics attribute
that every colourless graphics statement re-stamps with FORCLR -- rather than a
DRAW-private colour. Decisive tests (each a single RUN, one boot per case):

  T1  LINE ...,4  then plain DRAW   -> fg 4 = shared cell; fg 15 = DRAW-private default
  T2  DRAW"C6.."  then SCREEN2 then plain DRAW  -> does SCREEN 2 re-stamp it?
  T3  DRAW"C6.."  then plain PSET   -> does PSET inherit 6?
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
    ("T1_line4_then_draw", ['COLOR15,4,7:SCREEN2',
                            'LINE(100,100)-(108,100),4:PSET(100,140):DRAW"R8"', 'GOTO 30'], (100, 140)),
    ("T2_c6_screen2_draw", ['COLOR15,4,7:SCREEN2',
                            'PSET(100,100):DRAW"C6R8":SCREEN2:PSET(100,140):DRAW"R8"', 'GOTO 30'], (100, 140)),
    ("T3_c6_then_pset",    ['COLOR15,4,7:SCREEN2',
                            'PSET(100,100):DRAW"C6R8":PSET(100,140)', 'GOTO 30'], (100, 140)),
]
for label, prog, (x, y) in CASES:
    raw = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                              capture=("vram_segs", seg_at(x, y)), cart=None)[0]
    print(f"  {label:22s} @({x},{y}) -> {raw}")
