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

# D-MKSD: the four random-access float conversions, which did not exist here.
#   10 A$=MKS$(1.5) : PRINT LEN(A$)          -> 4 (was 0: parsed as an ARRAY)
#   10 PRINT CVS(MKS$(1.5))                  -> 1.5 (was Type mismatch)
add('demo.mkslen', [], 'LEN(MKS$(1.5))')
add('demo.mksbytes', [], ";".join(f"ASC(MID$(MKS$(1.5),{i},1))" for i in range(1, 5)))
add('demo.cvsround', [], 'CVS(MKS$(1.5))')
add('demo.mkdround', [], 'CVD(MKD$(1/3))')
# 🟢 and the zero case, which D-FACZERO had to fix FIRST for this to be right
add('demo.mkszero', [], ";".join(f"ASC(MID$(MKS$(0),{i},1))" for i in range(1, 5)))

BEFORE = {                       # zerobas, quoted from the pre-fix probe runs
    'demo.gicini':  '1  (the music played on for ~60 s at the Ok prompt)',
    'demo.faczero': '0 21 0 0  (21 = 1.5\'s own leftover mantissa byte)',
    'demo.ctl':     '65 21 0 0  (unchanged -- it never diverged)',
    'demo.mkslen':   '0        (MKS$(1.5) parsed as the string ARRAY MKS$(1))',
    'demo.mksbytes': 'ERR 5    (an array subscript error, not a verb)',
    'demo.cvsround': 'ERR 13   Type mismatch',
    'demo.mkdround': 'ERR 13   Type mismatch',
    'demo.mkszero':  'ERR 5    -- and once MKS$ worked it would have been'
                     ' 0 255 255 255 until D-FACZERO',
}

D.CASES.update(CASES)
sides = ["vg8020", "cf3300", "zb"]
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>12}" for s in sides) + "   verdict")
# 🔴 THE MK/CV VERBS ARE DISK BASIC, SO THE CASSETTE VG-8020 ANSWERS ERR 5 TO ALL
# OF THEM. Scoring those rows three-way prints DIFF on a slice that is byte-for-byte
# correct -- a readout that reads like a regression because it is comparing MACHINES
# and not LANGUAGES. Their oracle is the CF-3300 (the D-LSETREF disposition); the
# VG-8020 column stays PRINTED, and is marked `n/a` rather than dropped.
DISK_ROWS = {'demo.mkslen', 'demo.mksbytes', 'demo.cvsround', 'demo.mkdround',
             'demo.mkszero'}
for l in ORDER:
    vals = [str(res[s].get(l)) for s in sides]
    if l in DISK_ROWS:
        same, tag = vals[1] == vals[2], "SAME (vg8020 n/a: no disk ROM)"
    else:
        same, tag = len(set(vals)) == 1, "SAME"
    print(f"{l:<{w}}  " + "  ".join(f"{v:>16}" for v in vals)
          + f"   {tag if same else 'DIFF'}")
print("\nzerobas BEFORE today (quoted from the recorded pre-fix runs):")
for l in ORDER:
    print(f"  {l:<{w}}  {BEFORE[l]}")
print("done")
