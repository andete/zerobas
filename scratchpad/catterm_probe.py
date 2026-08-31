#!/usr/bin/env python3
r"""D-CATTM — the concatenation pair: `5+"AB"` and `"AB"+(0*(1/0)+1)`.

Filed 2026-08-29 by D-STRTM §4 and left open with a HAZARD ANALYSIS rather than
a fix: both live at `sct_err2`, which calls `type_mismatch_set` and then RETURNS
NC so the caller re-drives the whole expression numerically. Evaluating the
operand inside `sct_err2` -- the D-STRTM/D-CVISTRTM route -- would evaluate it
TWICE, and a string operand can contain a `USR` call or a `DEF FN` invocation
with side effects. So the filed conclusion is that the fix belongs in whatever
the NUMERIC RE-DRIVE meets, not in `sct_err2`.

RUNNING THE CLAIM BEFORE BUILDING ON IT. The rows below re-measure the filed
pair, add the two MIRROR forms nobody measured (operand order swapped), and
carry the `LEN` control that D-STRTM's own fix made correct -- so a reading that
says "the whole class is broken" can be told from one that says "concatenation
specifically is".
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D                                    # noqa: E402

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- the filed pair ---------------------------------------------------------
add('c.numstr',   [], '5+"AB"')                  # filed: ours 24, refs 13
add('c.strfault', [], '"AB"+(0*(1/0)+1)')        # filed: ours 13, refs 11
# --- the MIRRORS, which the filing does not cover ---------------------------
add('c.strnum',   [], '"AB"+5')
add('c.faultstr', [], '(0*(1/0)+1)+"AB"')
# --- variables, in case the literal path differs ----------------------------
add('c.varnum',   ['A$="AB"'], 'A$+5')
add('c.numvar',   ['A$="AB"'], '5+A$')
# --- 🟢 CONTROLS ------------------------------------------------------------
add('ctl.cat',    [], '"AB"+"CD"')               # concatenation still works
add('ctl.num',    [], '1+2')                     # numeric add still works
add('ctl.lenf',   [], 'LEN(0*(1/0)+1)')          # D-STRTM's fix: the operand's
                                                 # own fault outranks the type
                                                 # error on the SHARED path
D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides) + "   verdict")
diff, noor = [], []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if len(set(refs)) > 1:
        noor.append(l)
    elif refs and not same:
        diff.append(l)
    tag = "NO-ORACLE" if l in noor else ("SAME" if same else "DIFF")
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides)
          + f"   {tag}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER) - len(noor)} scorable"
      + ("  " + " ".join(diff) if diff else ""))
if noor:
    print(f"⚠️  {len(noor)} NO-ORACLE row(s) (the references disagree): "
          + " ".join(noor))
raise SystemExit(1 if diff else 0)
