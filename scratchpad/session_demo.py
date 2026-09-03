#!/usr/bin/env python3
r"""Closing demo 2026-09-03 — the two defects fixed today, as MSX BASIC a user types.

Both rows are ordinary programs, run on the Philips VG-8020, the National CF-3300
and zerobas. The `before` column is what zerobas printed BEFORE today's commits
(445d318 / 4df7a34); it is quoted from the recorded probe runs, not re-measured
here, and is labelled as such.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# D-GICINI: a program whose music must stop when it breaks.
#   10 PLAY"T32L1CDEFGAB"   start ~60 s of music
#   20 STOP                 Break in 20 -> back to Ok
#   PRINT PEEK(&HFB3F)      MUSICF: 0 = the queue is gone, 1 = still playing
D.DIRECT['demo.gicini'] = ['10 PLAY"T32L1CDEFGAB"', '20 STOP', 'RUN',
                           'CLS:PRINT"[";PEEK(&HFB3F);"]"']
ORDER.append('demo.gicini')

# D-FACZERO: the four stored bytes of a single-precision variable, after the
# same variable has held 1.5. The reference stores a canonical zero.
#   10 A!=1.5 : A!=0
#   PRINT the 4 bytes at VARPTR(A!)
add('demo.faczero', ['A!=1.5', 'A!=0'],
    ";".join(f"PEEK(VARPTR(A!)+{i})" for i in range(4)))
# 🟢 and the same slot holding a NONZERO value, which never diverged
add('demo.ctl', ['A!=0', 'A!=1.5'],
    ";".join(f"PEEK(VARPTR(A!)+{i})" for i in range(4)))

BEFORE = {                       # zerobas, quoted from the pre-fix probe runs
    'demo.gicini':  '1  (the music played on for ~60 s at the Ok prompt)',
    'demo.faczero': '0 21 0 0  (21 = 1.5\'s own leftover mantissa byte)',
    'demo.ctl':     '65 21 0 0  (unchanged -- it never diverged)',
}

D.CASES.update(CASES)
sides = ["vg8020", "cf3300", "zb"]
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>12}" for s in sides) + "   verdict")
for l in ORDER:
    vals = [str(res[s].get(l)) for s in sides]
    same = len(set(vals)) == 1
    print(f"{l:<{w}}  " + "  ".join(f"{v:>12}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print("\nzerobas BEFORE today (quoted from the recorded pre-fix runs):")
for l in ORDER:
    print(f"  {l:<{w}}  {BEFORE[l]}")
print("done")
