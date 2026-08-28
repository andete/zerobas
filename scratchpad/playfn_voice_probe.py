#!/usr/bin/env python3
r"""D-PLAYFN round 2: is PLAY(0) "ANY voice", or is the numbering 0-based?

Round 1 measured, on both references:

    idle                      PLAY(0..3) = 0 0 0 0
    during PLAY"L1CDEFGAB"    PLAY(0)=-1 PLAY(1)=-1 PLAY(2)=0 PLAY(3)=0
    PLAY(4) / PLAY(-1)        ERR 5

🔴 TWO RULES FIT ALL OF THAT AND THEY DISAGREE ELSEWHERE:
  A  n=0 means "is ANY voice playing", n=1..3 are voices 1..3.
  B  the numbering is 0-BASED: n=0 is voice 1, n=1 is voice 2, ...

Under A, a single string plays voice 1, so 0 and 1 both report -1. Under B, a
single string would have to be reported by n=0 -- and n=1 reading -1 would then
mean the string played voice 2, which it did not. The row that SEPARATES them
plays ONLY the second voice: `PLAY "","L1CDEFGAB"`.

    A predicts   PLAY(0)=-1  PLAY(1)=0   PLAY(2)=-1  PLAY(3)=0
    B predicts   PLAY(0)=0   PLAY(1)=-1  PLAY(2)=0   PLAY(3)=0

Third voice too, because a rule that survives two rows can still be wrong on the
third, and the cost of the extra row is one boot.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

V2 = 'PLAY "","L1CDEFGAB"'
V3 = 'PLAY "","","L1CDEFGAB"'
NEW = {
    'v2.all': ([V2], 'PLAY(0);PLAY(1);PLAY(2);PLAY(3)'),
    'v3.all': ([V3], 'PLAY(0);PLAY(1);PLAY(2);PLAY(3)'),
    'v1.all': (['PLAY"L1CDEFGAB"'], 'PLAY(0);PLAY(1);PLAY(2);PLAY(3)'),
    # does a NON-INTEGER argument truncate or round?  (the fix must match)
    'v.frac': (['PLAY"L1CDEFGAB"'], 'PLAY(1.7)'),
    'v.frac0':(['PLAY"L1CDEFGAB"'], 'PLAY(0.9)'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides))
print("\n(columns are PLAY(0) PLAY(1) PLAY(2) PLAY(3))")
