#!/usr/bin/env python3
r"""D-NGRAM11 — one `str_eval_next` for the six "past the delimiter, evaluate a
string" sites: LET A$(i)= / LSET / LET A$= / MID$-statement / INSTR's two args.

🔴 BOTH HALVES, ONE ROW PER SITE. `str_eval` DECLINES (CF clear) as well as
succeeding, and each of the six callers keeps its OWN `jp/jr nc,<target>` --
which is exactly what a row set covering only the success half would leave
unwitnessed. D-NGRAM8 broke a decline behind a `call` and its probe could not
see it.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- the SUCCESS half, one row per site -------------------------------------
add('g.letary',  ['DIM A$(3)', 'A$(1)="XY"'],             'A$(1)')   # arrays.asm
# ⚠️ NO ORACLE: THE TWO REFERENCES DISAGREE WITH EACH OTHER HERE. LSET/RSET on a
# variable that was never FIELDed reads `Illegal function call` on the
# cassette-only VG-8020 and pads-in-place on the disk-equipped CF-3300. zerobas
# targets the disk machine and agrees with it. Scored separately below rather
# than counted as a divergence -- a row with two different "right" answers is not
# evidence about this tree either way.
NO_ORACLE = {'g.lset', 'g.rset'}
add('g.lset',    ['A$="12345"', 'LSET A$="AB"'],          'A$+"|"')  # field.asm
add('g.rset',    ['A$="12345"', 'RSET A$="AB"'],          'A$+"|"')  # field.asm
add('g.let',     ['A$="XY"'],                             'A$')      # interp.asm
add('g.mid',     ['A$="ABCDE"', 'MID$(A$,2,2)="XY"'],     'A$')      # str-engine
add('g.instr',   [],                                      'INSTR("ABCDE","CD")')
add('g.instrp',  [],                                      'INSTR(2,"ABCDE","CD")')

# --- the DECLINE half: a NUMERIC operand where a string is required ----------
add('b.letary',  ['DIM A$(3)', 'A$(1)=5'],                '"bail-missed"')
add('b.lset',    ['A$="12345"', 'LSET A$=5'],             '"bail-missed"')
add('b.let',     ['A$=5'],                                '"bail-missed"')
add('b.mid',     ['A$="ABCDE"', 'MID$(A$,2,2)=5'],        '"bail-missed"')
add('b.instr',   [],                                      'INSTR("ABCDE",5)')
add('b.instrp',  [],                                      'INSTR(2,5,"CD")')

# --- 🔴 ONE OF THE TWO "CONTROLS" WAS A SUBJECT ROW ------------------------
# `ctl.cat` was `['A$="AB":B$="CD"'], 'A$+B$'` -- and its SETUP is two `LET A$=`
# statements, one of the six sites. K-N11A moved it, which is how it was caught.
# A control that runs the subject's own machinery is not a control; it is an
# unlabelled subject row that will be read as reassurance when it stays green.
# Renamed to what it is, and replaced by one that touches no string LET at all.
add('g.letcat',  ['A$="AB":B$="CD"'], 'A$+B$')   # LET A$= x2, then concat
add('ctl.num',   [], '1+1')
add('ctl.lit',   [], '"AB"+"CD"')                # literals only -- no LET, no site

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
    refs_agree = len(set(refs)) <= 1
    if l in NO_ORACLE or not refs_agree:
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
    # 🔴 NAMED, NOT DROPPED. An unscored row that vanishes from the report reads
    # as coverage. [[an-unnamed-outcome-reads-as-no-outcome]]
    print(f"⚠️  {len(no_oracle)} NO-ORACLE row(s) (the two references disagree): "
          + " ".join(no_oracle))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
