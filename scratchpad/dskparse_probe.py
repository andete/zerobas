#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DISKREST slice 3 (2026-10-20): DSKI$ / DSKO$'s `d,s` parse moved from main's
dsk_core into disk.rom's hk_dsk, which evaluates each argument by a CALL-BACK into
main. What can that move break, against the CF-3300?

  e.*  the error answers the parse owns -- and every row runs under ON ERROR GOTO
       (basic_probe_deffn's frame), so ERR *and ERL* say the raise from inside a
       call-back is trapped on the right line.
  n.*  nesting: an argument that re-enters the disk ROM (LOF), and DSKI$ inside an
       arithmetic expression, where the evaluator's own cursor (IX) must survive
       the hook.
  s.*  the parse's shape: blanks around the arguments.

dskio-acceptance covers the I/O itself (5 rows); nodisk-acceptance the diskless ERR 5.
    python3 -u scratchpad/dskparse_probe.py [cf3300,zb]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- 🟢 CONTROLS: the happy path, function and statement ---------------------
add('c.dski',    [], 'LEN(DSKI$(0,0))')                 # DSKI$ returns ""
add('c.dsko',    ['DSKO$ 0,700'], '1')                   # a write that succeeds
# --- e.* the parse's errors, under ON ERROR GOTO -------------------------------
add('e.drive',   [], 'LEN(DSKI$(3,0))')                 # Bad drive name
add('e.drive2',  ['DSKO$ 2,700'], '1')
add('e.nocomma', ['DSKO$ 0'], '1')                        # the CF-3300's 2
add('e.semi',    ['DSKO$ 0;700'], '1')                    # a separator that is NOT a
                                                          # comma: `DSKO$ 0` alone
                                                          # cannot see the comma check
                                                          # (the sector's own parse
                                                          # says 2 anyway; K-DP2 was
                                                          # inert on it)
add('e.strarg',  [], 'LEN(DSKI$(0,"A"))')               # a string sector
add('e.strdrv',  [], 'LEN(DSKI$("A",0))')               # a string drive
add('e.bigdrv',  [], 'LEN(DSKI$(256,0))')               # drive past a byte
add('e.negsec',  [], 'LEN(DSKI$(0,-1))')
add('e.nopar',   [], 'LEN(DSKI$(0,0)')                  # no `)`
# --- n.* nesting ----------------------------------------------------------------
add('n.lof',     ['OPEN "DP.DAT" FOR OUTPUT AS #1', 'PRINT #1,"X"', 'CLOSE #1',
                  'OPEN "DP.DAT" FOR INPUT AS #1'], 'LEN(DSKI$(0,LOF(1)))')
add('n.arith',   [], '1+LEN(DSKI$(0,0))*2')             # IX across the hook
add('n.twice',   [], 'LEN(DSKI$(0,0))+LEN(DSKI$(1,1))')
add('n.str',     [], '"<"+DSKI$(0,0)+">"')
# --- s.* the parse's shape ----------------------------------------------------
add('s.blanks',  [], 'LEN(DSKI$( 0 , 0 ))')
add('s.exprs',   ['D=0', 'S=1'], 'LEN(DSKI$(D,S*2))')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
# 🔴 WITH A DISK. basic_probe_deffn boots with the drive EMPTY, so the first run
# read ERR 70 (disk offline) on almost every row -- the parse errors still
# discriminated, but no row got PAST the I/O, so `1+LEN(DSKI$(0,0))*2` never
# tested the evaluator's cursor after the hook. Every case gets its OWN /tmp copy
# of disk/test720.dsk (DSKO$ writes), via run_cases' `diska`.
if os.environ.get("DP_NODISK") is None:
    import shutil, tempfile, functools
    _orig = D.omsx_repl.run_cases
    _src = os.path.join(os.path.dirname(HERE), "disk", "test720.dsk")
    def _with_disk(*a, **k):
        td = tempfile.mkdtemp(prefix="dskparse_")
        dsk = os.path.join(td, "t.dsk")
        shutil.copy(_src, dsk)
        try:
            return _orig(*a, diska=dsk, **k)
        finally:
            shutil.rmtree(td, ignore_errors=True)
    D.omsx_repl.run_cases = _with_disk
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>24}" for s in sides) + "   verdict")
diff = []
for l in ORDER:
    vals = [str(res[s].get(l)) for s in sides]
    same = len(set(vals)) == 1
    if not same: diff.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{v:>24}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF ({' vs '.join(sides)}): {len(diff)}/{len(ORDER)}  " + " ".join(diff))
print("done")
