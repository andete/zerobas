#!/usr/bin/env python3
r"""D-POOLCAP round 5: did the threshold move, and does in-place truncation bite?

LEFT$/RIGHT$/MID$ now snapshot through str_snapshot_arg -> str_snapshot_keep,
which returns an ALREADY-OWNED temp as-is instead of copying it.

🔴 THE HAZARD IS NAMED IN LEFT$'s OWN HEADER: "Snapshot the source into an owned
temp, then TRUNCATE IN PLACE." If the source is handed back as-is, the truncation
now mutates the source temp rather than a private copy. That is safe only while no
one else can still read that temp. The h.* rows below try to make someone else
read it -- nested slices, a temp sliced two different ways in one expression, and
a slice printed beside a freshly rebuilt copy of the same concatenation.

t.* re-runs the threshold ladder: zerobas needed CLEAR 120 where both references
worked at 70.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

BIG = 'X$="ABCDEFGHIJ"+"KLMNOPQRST":A$="AB"+"CD"'
S2  = 'X$="ABCDEF":Y$="GHIJKL"'
NEW = {}
for n in (70, 80, 100, 120):
    NEW['t.%d' % n] = (['CLEAR %d' % n, BIG], 'LEN(LEFT$(X$+X$,0))')
NEW['v.70']  = (['CLEAR 70', BIG], 'LEN(LEFT$(X$,0))')
# in-place-truncation hazard rows
NEW['h1.twice']  = (['CLEAR 400', S2], 'LEFT$(X$+Y$,3)+"|"+X$+Y$')
NEW['h2.nested'] = (['CLEAR 400', S2], 'LEFT$(LEFT$(X$+Y$,8),3)')
NEW['h3.midof']  = (['CLEAR 400', S2], 'LEFT$(MID$(X$+Y$,2,8),3)')
NEW['h4.bothend']= (['CLEAR 400', S2], 'RIGHT$(X$+Y$,3)+LEFT$(X$+Y$,3)')
NEW['h5.var']    = (['CLEAR 400', S2, 'Z$=X$+Y$'], 'LEFT$(Z$,3)+"|"+Z$')
NEW['h6.deep']   = (['CLEAR 400', S2], 'MID$(LEFT$(X$+Y$,9),3,4)+"|"+LEFT$(X$+Y$,2)')
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides))
print()
bad = 0
for l in labels:
    v = {s: res[s].get(l) for s in sides}
    refs = {s: x for s, x in v.items() if s != "zb"}
    if len(set(refs.values())) > 1:
        print(f"  {l}: THE REFERENCES DISAGREE {refs} -- no oracle")
    elif "zb" in v and refs and v["zb"] not in set(refs.values()):
        print(f"  {l}: DIVERGENCE  zb={v['zb']!r}  ref={list(refs.values())[0]!r}")
        bad += 1
print(f"\n{bad} divergence(s)")
