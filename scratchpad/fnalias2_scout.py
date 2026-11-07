#!/usr/bin/env python3
"""D-FNALIAS build, pre-build scout (2026-11-07): the questions the two-pass
design answers by CHOICE unless the reference is asked first.

  q.dup*   a formal NAMED TWICE. Binding by key (today: the second actual's
           store finds the FIRST slot) answers the LAST actual; binding
           positionally (copy pass) answers the FIRST.
  q.fre*   the string space a string actual costs DURING the body: one copy
           (the parked value IS the formal) or two (the slot copies it).
  q.tend   are the parked actuals released when the call ends, or held to
           the statement's end? Three calls of five string temporaries each.

    python3 -u scratchpad/fnalias2_scout.py [vg8020,cf3300,zb]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

A5 = ",".join(f'"{i}"+""' for i in range(1, 6))
NEW = {
    'q.dup':      (['DEF FNA(X,X)=X'], 'FNA(1,2)'),
    'q.dup3':     (['DEF FNA(X,Y,X)=X*10+Y'], 'FNA(1,2,3)'),
    'q.dupstr':   (['DEF FNA$(X$,X$)=X$'], 'FNA$("a","b")'),
    'q.fre.ctl':  (['DEF FNA(S$)=FRE("")', 'F=FRE("")'], 'F-FRE("")'),
    'q.fretmp':   (['DEF FNA(S$)=FRE("")', 'F=FRE("")'], 'F-FNA("AB"+"CD")'),
    'q.frelit':   (['DEF FNA(S$)=FRE("")', 'F=FRE("")'], 'F-FNA("ABCD")'),
    'q.frevar':   (['DEF FNA(S$)=FRE("")', 'A$="AB"+"CD":F=FRE("")'], 'F-FNA(A$)'),
    'q.tend':     (['DEF FNA$(A$,B$,C$,D$,E$)=A$'],
                   f'FNA$({A5})+FNA$({A5})+FNA$({A5})'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")

res = {}
for s in sides:
    res[s] = D.run_side(s, labels)
    print(f"[{s} done]", flush=True)
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>14}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>14}" for s in sides))
print(__import__("probe_refcache").summary())
