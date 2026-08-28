#!/usr/bin/env python3
r"""Does sg_walk_fnframe's OUTER-frame limitation actually bite? Measure it.

sg_walk_fnframe walks [FN_PAREA, FN_FEND) -- the LIVE frame. fn_enter saves the
caller's live prefix to the Z80 STACK, which no walk can address, so during a
NESTED call an outer string formal's body should have exactly the hazard the
inner one just stopped having. Claimed in the code comment; measured here.

    DEF FNI$(T$)=LEFT$(STR$(FRE(""))+X$+X$,0)+T$    inner: collect, then allocate
    DEF FNO$(S$)=FNI$("q")+S$                       outer: call inner, THEN read S$

`+` is left to right, so the inner call (and its collection) completes before the
OUTER formal S$ is fetched from a slot that was saved to the stack and restored.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

HOLE = 'B$="12345"+"67890":A$="AB"+"CD":B$=""'
BIG  = 'X$="ABCDEFGHIJ"+"KLMNOPQRST"'
NEW = {
    'n.outer': (['CLEAR 400', HOLE + ':' + BIG,
                 'DEF FNI$(T$)=LEFT$(STR$(FRE(""))+X$+X$,0)+T$',
                 'DEF FNO$(S$)=FNI$("q")+S$'], 'FNO$(A$)'),
    # control: the same nesting with NO collection in the inner body
    'n.outer.ctl': (['CLEAR 400', HOLE + ':' + BIG,
                     'DEF FNJ$(T$)=LEFT$(X$,0)+T$',
                     'DEF FNP$(S$)=FNJ$("q")+S$'], 'FNP$(A$)'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>18}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>18}" for s in sides))
