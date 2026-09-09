#!/usr/bin/env python3
"""D-FNNESTDEPTH — how much shadow-slot capacity does the REFERENCE actually have?

WHY THIS EXISTS. Joost authorised "match the reference" for the DEF FN aliasing
rows, and the filed design is: stop resetting the slot pointer to 0, allocate a
call's formals ABOVE the caller's live frame, and grow the shadow area to
~18 slots (198 B of page-3 RAM) so `o.p9nest` — nine formals in a call made from
inside another FN — still fits.

🔴 18 IS A GUESS UNTIL THE REFERENCE'S OWN CEILING IS MEASURED. It was derived
from ONE row at depth 2. If the reference gives nine formals at depth 3, 4 or 5,
then a fixed 18-slot array is "a bigger number is a different wrong answer, not a
fix" — the exact reasoning the control-frame arc had to invert once already, when
D-CTLPOOL found the references use one HIMEM-bounded pool where zerobas had fixed
arrays (docs/spec-basic-trapsvc.md §17). Sizing a NEW fixed array without asking
that question is how that mistake gets made a second time in the same tree.

WHAT THE ROWS ASK. Nine formals at nesting depth 1..4, plus a nine-formal call at
each depth's innermost level. `d.n1` is the already-measured control (= o.p9).
Every row returns the innermost formal's value, so a row that answers at all
answers with evidence the call really bound nine.

⚠️ A ROW THAT ERRORS IS A READING. ERR 5 is the shadow area refusing; the value
is the area holding. What is NOT distinguishable here is WHICH limit bit — slot
count, evaluator depth, or the Z80 stack (docs/spec-basic-trapsvc.md §19 measured
zerobas's DEF FN nesting cap at THREE, which is a stack address, not a constant)
— so a zerobas failure at depth 3 may be that cap and not this area.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

NINE = "A,B,C,D,E,F,G,H,I"
ARGS = "1,2,3,4,5,6,7,8,9"


def chain(depth):
    """FNZ0 has the nine formals; FNZ1..FNZ<depth-1> each take one formal and
    call the level below, so `depth` counts FN frames live at the innermost
    call. Every level's own formal is READ after the inner call returns, so a
    level whose slot was clobbered shows up as a wrong number, not just an error.
    """
    defs = ['DEF FNZ0(%s)=I' % NINE]
    for k in range(1, depth):
        inner = 'FNZ%d(%s)' % (k - 1, ARGS if k == 1 else 'X')
        defs.append('DEF FNZ%d(X)=%s' % (k, inner))
    return defs, 'FNZ%d(%s)' % (depth - 1, ARGS if depth == 1 else '1')


NEW = {}
for d in (1, 2, 3, 4):
    defs, call = chain(d)
    NEW['d.n%d' % d] = (defs, call)

D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>14}" for s in sides) + "   what it asks")
WHY = {
    'd.n1': "nine formals at top level (the o.p9 control)",
    'd.n2': "...called from inside ONE outer FN (the o.p9nest shape)",
    'd.n3': "...from inside TWO",
    'd.n4': "...from inside THREE",
}
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>14}" for s in sides)
          + f"   {WHY[l]}")
print("\n  every row that answers should answer 9 (the innermost formal I).")
print("  the DEEPEST row both references still answer is what sizes the area;")
print("  a reference that keeps answering says the area is not the shape.")
