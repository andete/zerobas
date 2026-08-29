#!/usr/bin/env python3
r"""D-NUMSTR — what a NUMERIC context does when it meets a STRING.

The mirror of D-STRTM. That slice asked what a string-taking verb does with a
number; this asks what the numeric evaluator does with a string, because
D-STRTM's one unfixed row is exactly that shape:

    5+"AB"     zerobas ERR 24 (Missing operand)   both references ERR 13

⚠️ AND ERR 24 IS NOT SIMPLY WRONG HERE. D-MISSOP established `Missing operand`
for a genuinely absent operand. So the question is not "24 or 13" but WHERE THE
BOUNDARY IS -- and the `k.` rows below are D-MISSOP's own slots, which must keep
their answer whatever happens to the expression-internal ones.
[[two-rules-that-coincide-on-every-row-you-have]]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- a STRING where a numeric factor is required ----------------------------
add('s.addlit',  [], '5+"AB"')
add('s.sublit',  [], '5-"AB"')
add('s.mullit',  [], '5*"AB"')
add('s.divlit',  [], '5/"AB"')
add('s.addvar',  ['A$="AB"'], '5+A$')
add('s.lhslit',  [], '"AB"+5')          # the OTHER side -- correct today (13)
add('s.unary',   [], '-"AB"')
add('s.paren',   [], '5+("AB")')
add('s.fn',      [], '5+LEFT$("AB",1)')  # a string-VALUED function

# --- 🔴 NOTHING there. D-MISSOP's header says BOTH references answer 24 "at
# every such slot, measured at 16 of them" -- but all sixteen were STATEMENT
# ARGUMENT slots, and `ev_f_missop` serves EVERY factor position including
# inside an expression. These rows ask whether the rule generalises.
# ⚠️ I wrote "5+ really is 24 on all three sides" in this file's own header
# before running it. It is not. That claim is deleted rather than softened.
add('m.add',     [], '5+')
add('m.mul',     [], '5*')
add('m.paren',   [], '5+()')
# the STATEMENT-ARGUMENT slots D-MISSOP actually measured -- these must stay 24
add('k.poke',    ['POKE &HE000,'],   '"bail-missed"')
add('k.locate',  ['LOCATE ,'],       '"bail-missed"')
add('k.pokev',   ['POKE ,1'],        '"bail-missed"')
add('k.tab',     ['PRINT TAB();1'],  '"bail-missed"')

# --- a string in other numeric slots ----------------------------------------
add('s.abs',     [], 'ABS("AB")')
add('s.sgn',     [], 'SGN("AB")')
add('s.cmp',     [], '5<"AB"')
add('s.poke',    ['POKE "AB",1'], '"bail-missed"')
add('s.tab',     [], '1')                # placeholder, replaced below
CASES['s.tab'] = (['PRINT TAB("AB");1'], '"bail-missed"')

# --- 🔴 the ORDERING twin, the axis that separated every fix today ----------
add('o.add',     [], '(0*(1/0)+1)+"AB"')
add('o.abs',     [], 'ABS(0*(1/0)+1)')   # numeric operand, clean control

# --- 🟢 the working forms ----------------------------------------------------
add('g.add',     [], '5+2')
add('g.abs',     [], 'ABS(-3)')
add('ctl.num',   [], '1+1')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides) + "   verdict")
diff, blind, no_oracle = [], [], []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if len(set(refs)) > 1:
        no_oracle.append(l)
    elif not same:
        diff.append(l)
    if any(any(m in str(res[s].get(l)) for m in ("<NO OUTPUT>", "<NO CAPTURE>", ';"'))
           for s in sides):
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides)
          + f"   {'NO-ORACLE' if l in no_oracle else ('SAME' if same else 'DIFF')}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER) - len(no_oracle)} scorable"
      + ("  " + " ".join(diff) if diff else ""))
if no_oracle:
    print(f"⚠️  {len(no_oracle)} NO-ORACLE row(s): " + " ".join(no_oracle))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
