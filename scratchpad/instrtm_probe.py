#!/usr/bin/env python3
r"""D-INSTRTM — INSTR answers Syntax error where both references say Type
mismatch; but the tail that answers is SHARED with the genuinely-malformed
shapes, so the reference surface has to be measured before it is split.

D-NGRAM11 found 2 rows. The fix looks like D-LEFTTM's -- raise TYPE MISMATCH
after evaluating the operand -- except that `efi_reject_p` / `efi_reject_pa` are
each reached BOTH by a `jr nz` (a missing ',') and by a `jr nc` (an operand that
is not a string). D-MIDOP measured exactly this distinction for the MID$
statement and the references answered 24 / 13 / 24 across three shapes, so a
blanket change here would be wrong in the same way.
[[a-shared-tail-is-not-a-decision]]

This probe asks the references which shapes want which code.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- NOT A STRING: the `jr nc` arm. D-NGRAM11 measured the first two at ERR 13.
add('t.a2num',   [], 'INSTR("ABCDE",5)')        # b$ numeric, 2-arg form
add('t.p_anum',  [], 'INSTR(2,5,"CD")')         # a$ numeric, 3-arg form
add('t.p_bnum',  [], 'INSTR(2,"ABCDE",5)')      # b$ numeric, 3-arg form
add('t.a1num',   [], 'INSTR(5,"CD")')           # 2-arg shape, a$ numeric
add('t.avar',    ['A=7'], 'INSTR(A,"CD")')      # a numeric VARIABLE, not a literal

# --- MALFORMED: the `jr nz` arm. These must NOT become Type mismatch.
add('m.oneonly', [], 'INSTR("AB")')             # no second argument
add('m.dangle',  [], 'INSTR("AB",)')            # dangling comma
add('m.noparen', [], 'INSTR("AB","CD"')         # missing ')'
add('m.empty',   [], 'INSTR()')                 # nothing at all
add('m.ponly',   [], 'INSTR(2,"AB")')           # 3-arg shape, b$ absent

# --- the ORDERING axis D-LEFTTM turned on: a fault already pending -----------
# If the fix arms TYPEMM before evaluating the operand it BLOCKS the real fault,
# which is exactly the mistake D-NGRAM8 made and D-LEFTTM's K-LT2 now pins.
add('o.pend',    [], 'INSTR("ABCDE",0*(1/0)+1)')
add('o.pendp',   [], 'INSTR(2,"ABCDE",0*(1/0)+1)')

# --- the working forms, which must not move ---------------------------------
add('g.two',     [], 'INSTR("ABCDE","CD")')
add('g.three',   [], 'INSTR(2,"ABCDE","CD")')
add('g.miss',    [], 'INSTR("ABCDE","ZZ")')
add('g.vars',    ['A$="ABCDE":B$="CD"'], 'INSTR(A$,B$)')

# --- controls that touch no INSTR -------------------------------------------
add('ctl.num',   [], '1+1')
add('ctl.lit',   [], '"AB"+"CD"')

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
