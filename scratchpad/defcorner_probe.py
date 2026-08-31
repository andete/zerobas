#!/usr/bin/env python3
r"""D-DEFCORNER — the DEFtype argument-shape corners the statement review
flagged as unmeasured (notes: /tmp/zerobas/deftype_review_notes.md).

  ctl.range  DEFINT A-C, A=5        -> 5 everywhere (the machinery works)
  ctl.str    DEFSTR S, S="X"        -> X everywhere
  d.two      DEFINT AB              -> zerobas hands the cursor back at 'B',
             so the item's TAIL runs as a statement. The references?
  d.rev      DEFSTR Z-A             -> reversed range: zb says ERR 2; ref code?
  d.bare     DEFINT                 -> zb ERR 2; refs?
  d.digit    DEFINT A-1             -> zb ERR 2; refs?
  d.num      DEFINT 1               -> zb ERR 2; refs?

⚠️ d.two CAN AGREE FOR THE WRONG REASON: zb's mid-item cursor makes `B` alone
a statement, which is ERR 2 too. If both sides read ERR 2, the ERL and the
next-statement behaviour (d.two2: DEFINT AB:C=7) separate "rejected the item"
from "executed the tail".
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D                                    # noqa: E402

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

add('ctl.range', ['DEFINT A-C', 'A=5'],  'A')
add('ctl.str',   ['DEFSTR S', 'S="X"'],  'S')
add('d.two',     ['DEFINT AB'],          'C')
add('d.two2',    ['DEFINT AB:C=7'],      'C')
add('d.rev',     ['DEFSTR Z-A'],         'C')
add('d.bare',    ['DEFINT'],             'C')
add('d.digit',   ['DEFINT A-1'],         'C')
add('d.num',     ['DEFINT 1'],           'C')
# the SEPARATING row for d.two's wrong-reason hazard: make the item's tail a
# HARMLESS statement. If zb hands the cursor back mid-item, `C=7` RUNS (C=7,
# no error); if the references reject the two-letter item, ERR 2 and C=0.
add('d.tail',    ['DEFINT AC=7'],        'C')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>14}" for s in sides) + "   verdict")
diff, blind = [], []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if refs and not same:
        diff.append(l)
    if any("<NO OUTPUT>" in str(res[s].get(l)) or "<NO CAPTURE>" in str(res[s].get(l))
           for s in sides):
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>14}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}"
      + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
raise SystemExit(1 if diff else 0)
