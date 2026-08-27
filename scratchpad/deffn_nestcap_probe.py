#!/usr/bin/env python3
"""Does the nine-formal ceiling still hold for a NESTED call, on the reference?

D-FNALIAS's candidate fix starts a call's shadow slots ABOVE the caller's live
frame (so binding cannot clobber a caller formal an actual has yet to read).
That costs nested capacity: a nested call would see fewer than nine slots.
Before adopting it, ask whether the reference gives nine INSIDE another FN --
otherwise the fix trades a measured divergence for an unmeasured one.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

NINE = "A,B,C,D,E,F,G,H,I"
NEW = {
    # nine formals in a callee, called from inside a 1-formal caller
    'o.p9nest':     (['DEF FNA(%s)=I' % NINE, 'DEF FNB(X)=FNA(1,2,3,4,5,6,7,8,9)'],
                     'FNB(1)'),
    # the same nine at TOP level -- the already-measured o.p9 shape, as control
    'o.p9nest.ctl': (['DEF FNA(%s)=I' % NINE], 'FNA(1,2,3,4,5,6,7,8,9)'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>14}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>14}" for s in sides))
