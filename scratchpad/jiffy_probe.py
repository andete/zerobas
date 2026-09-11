#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Does the BIOS on each machine actually ADVANCE JIFFY ($FC9E)?

INTFLG ($FC9B) was measured DEAD on the zerobas target (C-BIOS's ISR writes it
once, at boot), which is why the run loop cannot use the reference's break
mechanism. JIFFY is the other per-frame byte. Measure it, do not assume it.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides

PROG = ['10 A=PEEK(&HFC9E)',
        '20 FOR I=1 TO 400:NEXT',
        '30 B=PEEK(&HFC9E)',
        '40 PRINT"[J ";A;B;"]"',
        'RUN']

def face(c):
    c = c or ""
    i = c.rfind("[J ")
    if i < 0: return None
    j = c.find("]", i)
    return " ".join(c[i+3:j].split()) if j > 0 else None

for s in ("vg8020", "cf3300", "zb"):
    cfg = probe_sides.sides(s)[s]
    cap = omsx_repl.run_cases(cfg["machine"], [("j", PROG)], batch=False,
                              boot=cfg["boot"], reset=cfg["reset"], run_gap=20.0)[0]
    f = face(cap)
    print(f"  {s:8} JIFFY before/after 400-iter loop: {f!r}")
