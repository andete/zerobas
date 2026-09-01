#!/usr/bin/env python3
r"""D-CATFIX pre-measure — the trailing-'+' shapes sct_err2 also owns, plus the
does-the-item-print question, measured BEFORE the fix is written.

  t.vartrail  PRINT A$+      (operand missing at EOL)
  t.littrail  PRINT "AB"+
  t.colon     PRINT "AB"+:PRINT 9   (missing before ':')
  p.leak      does `PRINT "AB"+5` print AB before its error? The row captures
              the full tail, so `AB` + the message and the message alone read
              differently. (logicops §6 measured the refs raise BEFORE the item
              for the operator case; this is the concat-decline case.)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D                                    # noqa: E402

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# DIRECT-mode rows would echo-fence; the stored-program harness prints through
# line 60's own PRINT, so these use setup statements + a WITNESS variable and
# read the ERR through the harness's trap line instead.
add('t.vartrail', ['A$="AB"', 'PRINT A$+'],   'C')
add('t.littrail', ['PRINT "AB"+'],            'C')
add('t.colon',    ['PRINT "AB"+:C=9'],        'C')
add('p.leak',     ['PRINT "AB"+5', 'C=1'],    'C')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>14}" for s in sides) + "   verdict")
diff = []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if refs and not same:
        diff.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>14}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}"
      + ("  " + " ".join(diff) if diff else ""))
raise SystemExit(1 if diff else 0)
