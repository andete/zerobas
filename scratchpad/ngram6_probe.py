#!/usr/bin/env python3
r"""D-NGRAM6 — seven sites open-coded a helper that already existed.

`ld a,(FPERR) / or a / jp nz,fp_runtime_error` (7 B) stood at SEVEN sites while
`check_fperr_only` (basic/interp.asm) already WAS that routine. Each site becomes
`call check_fperr_only` (3 B): -28 B, and no new body -- low 94 -> 106 B free,
page 1 299 -> 315 B free.

⚠️ THE ABORT PATHS ARE NOT LITERALLY IDENTICAL, WHICH IS THE THING TO WITNESS.
Open-coded, an error jumps STRAIGHT to fp_runtime_error with the caller's frame
intact. Through the helper it reaches `cee_abort_fp`, which pops the helper's own
dead return address FIRST -- a routine written for exactly this (its comment says
"discard our own dead resume addr"). Net stack identical, and fp_runtime_error
resets SP from SAVSTK regardless. One row per site says so in rows rather than in
reasoning.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- one row per SITE, each on its deferred-fault path ----------------------
add('s.poke',     ['POKE 1E10,1'],              '"done"')   # do_poke
add('s.time',     ['TIME=1E10'],                '"done"')   # ex_time_assign
add('s.interval', ['ON INTERVAL=1E10 GOSUB 60'],'"done"')   # ex_on_interval
add('s.print',    ['PRINT HEX$(65536.)'],       '"done"')   # ems_print
# 🔴 `A(1)=1E10` AND `A=1E10` DO NOT FAULT -- 1E10 is fine in the FLOAT domain,
# and these two sites check the INTEGER coercion. Both rows read "done" on all
# three sides, i.e. agreed because nothing happened, while looking like witnesses
# for two of the seven sites. The `%` forms actually reach them.
# [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
add('s.arr',      ['DIM A%(3)', 'A%(1)=99999'], '"done"')   # ex_let_arr
# 🔴 `A%=99999` WAS DROPPED, NOT KEPT AS A SPARE. It raises ERR 6 like the rows
# below, so it LOOKED like the exec_stmt witness -- but under K-N6A it did not
# move: its error comes from the LET store's OWN coercion check, never from the
# statement-boundary one. A row that agrees through a different layer is not a
# witness for this site. The three below DO move.
# [[a-case-that-agrees-can-agree-for-the-wrong-reason]] [[evferr-slice]]
add('s.exec.print',['PRINT 1E38*1E38'],          '"done"')   # exec_stmt boundary
add('s.exec.if',   ['IF 1E38*1E38 THEN A=1'],    '"done"')
add('s.exec.for',  ['FOR I=1 TO 1E38*1E38'],     '"done"')

# --- 🟢 the same verbs on their CLEAN path: the helper must fall through -----
add('g.poke',     ['POKE &HE000,7'],            'PEEK(&HE000)')
add('g.time',     ['TIME=0'],                   '"ok"')
add('g.print',    [],                           'HEX$(255)')
add('g.arr',      ['DIM A%(3)', 'A%(1)=7'],     'A%(1)')
add('ctl.num',    [],                           '1+1')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>20}" for s in sides) + "   verdict")
diff, blind = [], []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if not same: diff.append(l)
    if "<NO OUTPUT>" in zb or "<NO CAPTURE>" in zb or "POKE" in zb or "TIME" in zb:
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>20}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}" + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
