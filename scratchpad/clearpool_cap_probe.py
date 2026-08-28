#!/usr/bin/env python3
r"""D-POOLCAP scout: zerobas exhausts a CLEAR 100 pool the references survive.

Filed 2026-08-27 by D-FNGCROOT §3, found by a CONTROL rather than a subject:

    CLEAR 100 : B$="12345"+"67890" : A$="AB"+"CD" : B$=""
    X$="ABCDEFGHIJ"+"KLMNOPQRST"
    PRINT LEFT$(STR$(FRE(""))+X$+X$,0)+A$

vg8020 and CF-3300 answer ABCD; zerobas raises Out of string space. No DEF FN
anywhere in it. Green from CLEAR 150 up.

Rather than bisect pass/fail first, ASK EACH MACHINE WHAT IT THINKS IT HAS.
`FRE("")` reports the bytes still allocatable, so two readings settle most of it:

  c.pool   what `CLEAR n` actually granted, before anything is allocated
  c.after  what survives the SAME allocations on each side

If zerobas simply grants less for the same n, the divergence is the grant, not
the spending -- and no bisect is needed to say so.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

HOLE = 'B$="12345"+"67890":A$="AB"+"CD":B$=""'
BIG  = 'X$="ABCDEFGHIJ"+"KLMNOPQRST"'
NEW = {
    # what CLEAR n grants, untouched
    'c.pool100': (['CLEAR 100'], 'FRE("")'),
    'c.pool150': (['CLEAR 150'], 'FRE("")'),
    # what survives the same allocations
    'c.after100': (['CLEAR 100', HOLE, BIG], 'FRE("")'),
    'c.after150': (['CLEAR 150', HOLE, BIG], 'FRE("")'),
    # and the cost of ONE more X$ concatenation on top
    'c.step100': (['CLEAR 100', HOLE, BIG, 'Y$=X$+X$'], 'FRE("")'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides))
