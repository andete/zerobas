#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWDRAWX: `DRAW`'s ANGLE and SCALE persist across PROGRAMS, and a batched
sweep carries them from one case to the next.

Three cases in ONE batch, in order: a case that sets `A1`, then a plain `R5` with
no reset, then the same `R5` behind an `A0S4`. The middle one reads the
BACKGROUND -- it drew rotated -- and that is what made `drawkw_j`/`drawkw_k` look
like forms the machine does not have. Faithful MSX behaviour, and an apparatus
hazard: every DRAW row in the sweep now opens with `A0S4`.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl
from omsx_repl import as_stored
BODIES = [
 ('a_sets_angle', 'SCREEN2:PSET(10,50),15:DRAW"A1R5":A=POINT(10,47):SCREEN0:PRINT"[p1";A;"]"'),
 ('b_plain_R5',   'SCREEN2:PSET(10,10),15:DRAW"R5":A=POINT(14,10):SCREEN0:PRINT"[p2";A;"]"'),
 ('c_reset_R5',   'SCREEN2:PSET(10,10),15:DRAW"A0S4R5":A=POINT(14,10):SCREEN0:PRINT"[p3";A;"]"'),
]
for mach in ("Philips_VG_8020",):
    print("===", mach, "BATCHED (one boot, in order)")
    specs=[("stored", as_stored(b)) for _,b in BODIES]
    for (name,_), raw in zip(BODIES, omsx_repl.run_cases(mach, specs, batch=True)):
        txt=" ".join("".join(raw or "").split()); i=txt.find("[p")
        print(f"  {name:14} {(txt[i:i+16] if i>=0 else txt[:40])!r}")
