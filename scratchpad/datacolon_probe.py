#!/usr/bin/env python3
r"""D-DATACOLON — two DATA/RESTORE mechanism candidates from the statement
review, run before anything is built on them:

1. QUOTED ':' IN A DATA BODY. `tk_data_rest` (tokenise.inc) and `exd_lp`
   (interp.asm ex_data) both end the DATA body at the first ':' with NO quote
   state -- and the comment asserts "no strings" while the READ engine's own
   spec rows prove a comma inside quotes is content. If the references treat a
   quoted ':' as content (expected), zerobas splits the statement at crunch
   time and executes the tail of the string as code.

2. BARE RESTORE'S `ret`. The dispatcher enters handlers by push/ret (a tail
   jump), so a handler's `ret` ends the WHOLE LINE. ex_restore's bare arm ends
   in an unconditional `ret` under the comment "nothing else on a bare RESTORE
   word" -- so `RESTORE:C=9` would silently skip `C=9` here.

  d.qcolon   DATA "A:B" / READ A$        -> refs read the item as A:B
  d.qrun     DATA "A:B":C=7 / RUN        -> refs run C=7 (2nd colon separates)
  ctl.plain  DATA 5:C=7 / RUN            -> 7 everywhere (unquoted ':' ends DATA)
  r.chain    direct:  C=0:RESTORE:C=9    -> refs 9
  r.chain2   program: 10 C=0:RESTORE:C=9 -> refs 9
  ctl.rest   READ A:RESTORE:READ B       -> A+B = 2 everywhere (RESTORE works,
             and this row ALSO chains after RESTORE, so it separates "RESTORE
             is broken" from "the chain after it is")
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D                                    # noqa: E402

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# 🔴 THE FIRST CUT PRE-NUMBERED ITS LINES AND TYPED ITS OWN `RUN`, and all six
# rows FENCED on the references while zb answered values -- an asymmetric
# echo-fence that read exactly like six divergences. The deffn harness ALREADY
# builds a stored program (10 ON ERROR / 20.. setups / 60 PRINT expr / RUN), so
# `10 DATA ...` became the statement `10 DATA ...` on line 20 and `RUN` became
# line 40 of its own program. Setups here are BARE statements, harness-native.
add('d.qcolon',  ['DATA "A:B"', 'READ A$'],            'A$')
add('d.qrun',    ['DATA "A:B":C=7'],                   'C')
add('ctl.plain', ['DATA 5:C=7'],                       'C')
add('r.chain',   ['C=0:RESTORE:C=9'],                  'C')
add('ctl.rest',  ['DATA 1', 'READ A:RESTORE:READ B'],  'A+B')
# the row that decides what an UNTERMINATED quote does to the ':' scan: if the
# open quote swallows the rest of the line, C stays 0 on the references; if
# the scan drops out of quote mode at EOL-less ':' anyway, C reads 7.
add('d.unterm',  ['C=0', 'DATA "A:B:C=7'],             'C')
add('r.junk',    ['RESTORE X'],                        'C')

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
