#!/usr/bin/env python3
r"""D-POOLCAP round 4: the SETTLED cost is identical, so measure the PEAK.

Round 3 refuted the obvious mechanism. `LEFT$(X$,n)` charges the pool exactly n
bytes on ALL THREE sides (0/5/20), and RIGHT$/MID$ of length 0 charge 0. So
zerobas does not over-allocate the RESULT.

What separates the passing rows from the failing ones is the SOURCE: every row
that works slices a VARIABLE (`LEFT$(X$,0)`), and every row that diverges slices
a TEMP (`LEFT$(X$+X$,0)`, `LEFT$(STR$(FRE(""))+X$+X$,0)`). A transient peak does
not show up in a before/after FRE reading -- it shows up as the minimum pool the
expression needs at all. So walk CLEAR down and find each side's threshold; the
gap between them IS the extra transient, in bytes.

Live data is 24 B (X$ 20 + A$ 4), so free = CLEAR n - 24, and the temp is 40 B.
`v.*` slices a VARIABLE at the tightest pool as the control: if the divergence is
about temps, it must stay green where the temp rows go red.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

BIG = 'X$="ABCDEFGHIJ"+"KLMNOPQRST":A$="AB"+"CD"'
NEW = {}
for n in (70, 80, 90, 100, 120):
    NEW['t.%d' % n] = (['CLEAR %d' % n, BIG], 'LEN(LEFT$(X$+X$,0))')
NEW['v.70'] = (['CLEAR 70', BIG], 'LEN(LEFT$(X$,0))')
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides))
print("\nthreshold = the smallest CLEAR at which `LEN(LEFT$(X$+X$,0))` answers 0")
for s in sides:
    ok = [n for n in (70, 80, 90, 100, 120) if str(res[s].get('t.%d' % n)) == '0']
    print(f"  {s:<8} works at {ok if ok else 'NONE of the ladder'}")
