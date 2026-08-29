#!/usr/bin/env python3
r"""D-STRTM — the string-argument TYPE-MISMATCH surface, swept across every verb.

Three separate slices found the same defect in three places today: a verb handed
a NUMERIC where it wants a string answered `Syntax error` where both references
answer `Type mismatch`.

  D-NGRAM9   MID$-statement / LINE INPUT target   ERR 2 -> ERR 13   (fixed)
  D-LEFTTM   LEFT$ / RIGHT$ / MID$ function       ERR 2 -> ERR 13   (fixed)
  D-INSTRTM  INSTR's two string arguments         ERR 2 -> ERR 13   (fixed)

🎯 THREE INSTANCES IS A CLASS, NOT A COINCIDENCE. Each was found incidentally,
by a carve that happened to touch the site. This sweeps the WHOLE surface on
purpose instead: every verb that takes a string argument, handed a number.

⚠️ AND THE ORDERING AXIS COMES WITH IT. D-LEFTTM and D-INSTRTM both showed that
the raise must come AFTER the operand is evaluated, so a fault the operand itself
raises wins. A verb can answer 13 correctly and still get the pending case wrong,
so every subject row has an `o.` twin.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- string-VALUED functions given a number ---------------------------------
add('t.left',    [], 'LEFT$(5,2)')          # fixed by D-LEFTTM -- regression row
add('t.right',   [], 'RIGHT$(5,2)')
add('t.midf',    [], 'MID$(5,1,2)')
add('t.instr',   [], 'INSTR("ABCDE",5)')    # fixed by D-INSTRTM -- regression row

# --- numeric-VALUED functions OVER a string argument ------------------------
add('t.len',     [], 'LEN(5)')
add('t.asc',     [], 'ASC(5)')
add('t.val',     [], 'VAL(5)')

# --- string operators -------------------------------------------------------
add('t.cat',     [], '"AB"+5')
add('t.catl',    [], '5+"AB"')
add('t.cmp',     [], '"AB"=5')

# --- statements that take a string ------------------------------------------
add('t.printus', [], '"x"')                 # placeholder, replaced below
CASES['t.printus'] = (['PRINT USING 5;1'], '"bail-missed"')
add('t.name',    ['NAME 5 AS "B"'],          '"bail-missed"')
add('t.kill',    ['KILL 5'],                 '"bail-missed"')
add('t.midst',   ['A$="ABCDE"', 'MID$(A$,2,2)=5'], '"bail-missed"')

# --- 🔴 the ORDERING twin: a fault the operand itself raises must WIN --------
add('o.left',    [], 'LEFT$(0*(1/0)+1,2)')
add('o.instr',   [], 'INSTR("ABCDE",0*(1/0)+1)')
add('o.len',     [], 'LEN(0*(1/0)+1)')
add('o.cat',     [], '"AB"+(0*(1/0)+1)')

# --- 🟢 the working forms -----------------------------------------------------
add('g.left',    [], 'LEFT$("ABCDE",2)')
add('g.len',     ['A$="ABC"'], 'LEN(A$)')
add('g.cat',     [], '"AB"+"CD"')
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
    # detect the ECHO, on EVERY side (D-NGRAM10 §3)
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
