#!/usr/bin/env python3
r"""D-NGRAM19 — one `evmc_arg_int` for ABS / SGN / INT / FIX.

All four opened with the same nine bytes: the D-F2-4 argument gate, a `ret nz`
that returns from the VERB, and `ld a,(FACTYP) / cp 2` -- *is the argument
already an int16?*

🔴 THREE PATHS LEAVE THAT RUN, so the rows cover three per verb:
  `i.*`  an INT argument      (FACTYP == 2, the Z arm)
  `f.*`  a FLOAT argument     (the NZ arm -- each verb branches differently)
  `b.*`  a MALFORMED argument (the `ret`-from-the-verb arm, now CARRY)
A row set with only the first two cannot see the malformed path at all, and it
is the one that changed shape in this carve.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D                                    # noqa: E402

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

add('i.abs', [], 'ABS(-5)')
add('f.abs', [], 'ABS(-5.5)')
add('b.abs', [], 'ABS()')
add('i.sgn', [], 'SGN(-5)')
add('f.sgn', [], 'SGN(-5.5)')
add('b.sgn', [], 'SGN()')
add('i.int', [], 'INT(5)')
add('f.int', [], 'INT(5.7)')
add('b.int', [], 'INT()')
add('i.fix', [], 'FIX(5)')
add('f.fix', [], 'FIX(-5.7)')
add('b.fix', [], 'FIX()')
# 🟢 the -32768 escape ABS has its own arm for, and a NEGATIVE float for SGN/FIX
add('x.abs8k', [], 'ABS(-32768)')
add('x.fixneg', [], 'FIX(-5.2)')
# 🟢 CONTROLS: a math verb NOT in the set, and plain arithmetic.
add('ctl.sqr', [], 'SQR(9)')
add('ctl.num', [], '1+1')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>20}" for s in sides) + "   verdict")
diff = []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if refs and not same:
        diff.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>20}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}"
      + ("  " + " ".join(diff) if diff else ""))
raise SystemExit(1 if diff else 0)
