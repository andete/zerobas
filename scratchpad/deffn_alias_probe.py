#!/usr/bin/env python3
"""D-FNALIAS scout: does binding formal 0 shadow the caller for actual 1?

TODO.md (D-DEFFN, docs/deffn-impl-2026-08-22.md §8) filed this against the DRAFT:
"the draft binds in place ... writes slot 0 before the second actual reads it",
with the reference's behaviour UNMEASURED. DEF FN has SHIPPED since (D-DEFFNLAND,
2026-08-23), so the premise is re-run here rather than inherited.

THE SEPARATOR. `DEF FNA(P,Q)=P*100+Q` with a caller variable also called P:

    P=3 : PRINT FNA(5,P)
        503  -> every actual is evaluated in the CALLER's scope
        505  -> binding P:=5 already shadows the caller when Q's actual is read

and the nested form the item actually describes -- a callee formal sharing a name
with the CALLER's formal:

    DEF FNA(X,Q)=X*100+Q : DEF FNB(X)=FNA(9,X) : PRINT FNB(3)
        903  -> caller's frame still visible
        909  -> callee's slot 0 shadows it

Each has a POSITIVE CONTROL with no shared name, so a broken two-formal fixture
reddens the control before it reddens the subject.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

NEW = {
    'o.alias':          (['DEF FNA(P,Q)=P*100+Q', 'P=3'],            'FNA(5,P)'),
    'o.alias.ctl':      (['DEF FNA(P,Q)=P*100+Q'],                   'FNA(5,7)'),
    'o.aliasnest':      (['DEF FNA(X,Q)=X*100+Q', 'DEF FNB(X)=FNA(9,X)'], 'FNB(3)'),
    'o.aliasnest.ctl':  (['DEF FNA(X,Q)=X*100+Q', 'DEF FNB(X)=FNA(9,7)'], 'FNB(3)'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")

res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>12}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>12}" for s in sides))
print()
for l in labels:
    vals = {s: res[s].get(l) for s in sides}
    refs = {s: v for s, v in vals.items() if s != "zb"}
    if len(set(refs.values())) > 1:
        print(f"  {l}: THE REFERENCES DISAGREE {refs} -- no oracle")
    elif "zb" in vals and refs and vals["zb"] not in set(refs.values()):
        print(f"  {l}: DIVERGENCE  zb={vals['zb']!r}  ref={list(refs.values())[0]!r}")
    elif refs:
        print(f"  {l}: agree ({list(refs.values())[0]!r})")
