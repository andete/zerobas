#!/usr/bin/env python3
r"""D-POOLCAP round 2: the pool is identical, so bisect the EXPRESSION.

Round 1 (clearpool_cap_probe.py) killed the obvious explanation: all three sides
report the SAME grant for `CLEAR n` (100 -> 100, 150 -> 150), the SAME free space
after identical allocations (76 / 126), and the SAME cost for one more
concatenation (36). zerobas is not given less and does not spend more on ordinary
stores. So the extra cost lives inside the one expression that diverges, where a
chain of temps is built and nothing is released until the statement ends:

    LEFT$(STR$(FRE(""))+X$+X$,0)+A$          at CLEAR 100, with 76 B free

Each row below is a PREFIX or a variant of it, so the first row that diverges
names the term that costs zerobas more. The `.nofre` pair separates "FRE("") is
expensive here" from "the temp chain is".
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

HOLE = 'B$="12345"+"67890":A$="AB"+"CD":B$=""'
BIG  = 'X$="ABCDEFGHIJ"+"KLMNOPQRST"'
SETUP = ['CLEAR 100', HOLE, BIG]
NEW = {
    'e1.fre':      (SETUP, 'LEN(STR$(FRE("")))'),
    'e2.frex':     (SETUP, 'LEN(STR$(FRE(""))+X$)'),
    'e3.frexx':    (SETUP, 'LEN(STR$(FRE(""))+X$+X$)'),
    'e4.left':     (SETUP, 'LEN(LEFT$(STR$(FRE(""))+X$+X$,0))'),
    'e5.full':     (SETUP, 'LEFT$(STR$(FRE(""))+X$+X$,0)+A$'),
    # the same shapes with NO FRE in them -- separates the collector from the chain
    'n3.xx':       (SETUP, 'LEN(X$+X$)'),
    'n5.full':     (SETUP, 'LEFT$(X$+X$,0)+A$'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides))
print()
for l in labels:
    v = {s: res[s].get(l) for s in sides}
    refs = {s: x for s, x in v.items() if s != "zb"}
    if len(set(refs.values())) > 1:
        print(f"  {l}: THE REFERENCES DISAGREE {refs} -- no oracle")
    elif "zb" in v and refs and v["zb"] not in set(refs.values()):
        print(f"  {l}: DIVERGENCE  zb={v['zb']!r}  ref={list(refs.values())[0]!r}")
