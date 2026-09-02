#!/usr/bin/env python3
r"""D-DEFERCHECK — two deferrals from the sweep, checked against the machine.

D-DEFERSWEEP narrowed the tree's deferral comments to 29. Two name a condition
that has plainly since been met:

  sysvars.inc:232  "The float siblings (MKS$/MKD$/CVS/CVD) need Phase-3 floats
                    and are deferred"     -- floats landed
  sysvars.inc:314/328/336  "RND not yet implemented" (x3)
                                          -- fp_rnd ships as a sub-ROM tenant

This is the PRINT USING shape exactly (D-PUSING): a deferral whose trigger has
fired and which nobody revisited. Whether the FEATURE is missing or only the
COMMENT is stale is a measurement, and these are the rows.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- RND: "not yet implemented" x3 -----------------------------------------
# 🎯 RND IS RANDOM, so a VALUE row cannot be differential. These ask only
# whether it EXISTS and is in range -- the question the comment raises.
add('r.exists', ['X=RND(1)'],            '"ok"')
add('r.range',  ['X=RND(1)', 'Y=0', 'IF X>=0 AND X<1 THEN Y=1'], 'Y')
add('r.neg',    ['X=RND(-1)'],           '"ok"')
add('r.zero',   ['X=RND(0)'],            '"ok"')

# --- the MKx$/CVx float siblings -------------------------------------------
# MKI$/CVI are the INTEGER pair and ship (D-CVITM). The float siblings are the
# deferred ones. A round-trip is the row: CVS(MKS$(x)) must return x.
add('m.mki',    ['A$=MKI$(258)'],        'CVI(A$)')
add('m.mks',    ['A$=MKS$(1.5)'],        'CVS(A$)')
add('m.mkd',    ['A$=MKD$(1.5)'],        'CVD(A$)')
add('m.mkslen', ['A$=MKS$(1.5)'],        'LEN(A$)')
add('m.mkdlen', ['A$=MKD$(1.5)'],        'LEN(A$)')
# 🟢 CONTROL: the integer pair's length, which is known to work (2 bytes)
add('m.mkilen', ['A$=MKI$(258)'],        'LEN(A$)')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>18}" for s in sides) + "   verdict")
diff = []
for l in ORDER:
    vals = [str(res[s].get(l)) for s in sides]
    same = len(set(vals)) == 1
    if not same: diff.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{v:>18}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF: {len(diff)}/{len(ORDER)}  " + " ".join(diff))
