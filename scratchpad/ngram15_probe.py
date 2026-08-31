#!/usr/bin/env python3
r"""D-NGRAM15 — one `str_eval_ix` for the seven "evaluate the string at the IX
cursor" sites.

ONE ROW PER SITE, NAMED FROM ITS ENCLOSING LABEL rather than from nearby prose
(D-NGRAM4 lost a site by reading the prose and left CHR$ unwitnessed):

  ev_rel       basic/expr.asm        a relational operator's LHS
  evr_rhs      basic/expr.asm        ...and its RHS
  ev_ff_cvi    basic/expr.asm        CVI
  ev_ff_fre    basic/expr.asm        FRE
  ev_str_arg   basic/str-engine.asm  the shared string-function argument parse
  ev_f_instr   basic/str-engine.asm  INSTR
  ers_rhs      basic/str-engine.asm  the string relational's RHS

🔴 BOTH HALVES. `str_eval` DECLINES (CF clear) as well as succeeding, and every
one of the seven callers keeps its OWN `jr c` / `jr nc` AT THE SITE -- which is
exactly the structure a success-only row set cannot see. D-NGRAM8 put `str_eval`
behind a `call` whose `ret` landed one frame too shallow, the decline stopped
declining, and its probe was blind to it.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D                                    # noqa: E402

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- the SUCCESS half, one row per site -------------------------------------
add('g.rel',     [], '"AB"="AB"')                  # ev_rel + evr_rhs
add('g.relvar',  ['A$="AB"'], 'A$<"B"')            # ...through a variable
add('g.cvi',     [], 'CVI("AB")')                  # ev_ff_cvi
add('g.fre',     [], 'FRE("")>=0')                 # ev_ff_fre (string arg)
add('g.len',     [], 'LEN("ABC")')                 # ev_str_arg
add('g.instr',   [], 'INSTR("ABCDE","CD")')        # ev_f_instr
add('g.ersrhs',  ['A$="AB"', 'B$="AC"'], 'A$<B$')  # ers_rhs

# --- the DECLINE half: str_eval returns CF clear and the SITE branches -------
# Each of these reaches a DIFFERENT `jr c` / `jr nc` at a different site, which
# is the half a frame mistake breaks.
add('b.cvi',     [], 'CVI(5)')
add('b.len',     [], 'LEN(5)')
add('b.instr',   [], 'INSTR("ABCDE",5)')
add('g.frenum',  [], 'FRE(0)>=0')                  # the NC arm of ev_ff_fre --
                                                   # a DECLINE that is not an error
add('g.relnum',  [], '1<2')                        # the NC arm of ev_rel

# --- 🟢 CONTROLS: no string expression at an IX cursor anywhere --------------
add('ctl.num',   [], '1+1')
add('ctl.arr',   ['DIM A(3)', 'A(1)=7'], 'A(1)')

# 🔴 ONE ROW HAS NO ORACLE, AND THE REASON IS STRUCTURAL, NOT NUMERIC. `CVI` is
# a DISK BASIC verb: the cassette-only VG-8020 does not have it and answers
# `Illegal function call` to every CVI, well-formed or not. So the two references
# DISAGREE WITH EACH OTHER on `g.cvi`, and a row with two different right answers
# is not evidence about this tree either way. zerobas targets the disk machine
# and matches it (16961).
# ⚠️ `b.cvi` is NOT in here: there the two references disagree too, but zerobas
# ALSO disagrees with the CF-3300 -- `CVI(5)` reads Type mismatch on the disk
# reference and Syntax error here. That is a real divergence (the D-LEFTTM class:
# the argument parse rejects before the type check), pre-existing, filed in
# TODO.md, and NOT this slice's to fix.
NO_ORACLE = {'g.cvi'}

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides) + "   verdict")
diff, blind = [], []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if refs and not same and l not in NO_ORACLE:
        diff.append(l)
    if any("<NO OUTPUT>" in str(res[s].get(l)) or "<NO CAPTURE>" in str(res[s].get(l))
           for s in sides):
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides)
          + f"   {'NO-ORACLE' if l in NO_ORACLE else ('SAME' if same else 'DIFF')}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER) - len(NO_ORACLE)} scorable"
      + ("  " + " ".join(diff) if diff else ""))
if NO_ORACLE:
    print(f"⚠️  {len(NO_ORACLE)} NO-ORACLE row(s) (the two references disagree): "
          + " ".join(sorted(NO_ORACLE)))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
raise SystemExit(1 if diff else 0)
