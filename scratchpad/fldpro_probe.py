#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DISKREST slice 4 (2026-10-20): FIELD's prologue -- `#`, the channel, its mode
class, the record's span, the comma -- moved from main's field_prologue into
disk.rom's hk_field, which reads the record's address from its own RANDOM row and
calls back for the channel expression, fch_check and fch_mode_class. Every answer
the prologue owns, against the CF-3300, each row under ON ERROR GOTO
(basic_probe_deffn's frame: ERR and ERL), with a /tmp copy of disk/test720.dsk per
case (dskparse_probe.py's lesson: the harness boots with the drive EMPTY).

  c.*  controls: FIELD binds, with and without `#`
  e.*  the prologue's refusals: 59 closed / 61 not RANDOM / 5 device / 2 comma /
       52 past MAXFILES / 13 a string channel / 50 a field past the record
  n.*  the record's span: a second channel, an expression channel, the bound
  s.*  blanks
    python3 -u scratchpad/fldpro_probe.py [cf3300,zb]
"""
import os, sys, shutil, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

R = 'OPEN "FP.DAT" AS #1 LEN=32'
# --- 🟢 CONTROLS -------------------------------------------------------------
add('c.bind',    [R, 'FIELD #1,8 AS A$,4 AS B$'], 'LEN(A$);LEN(B$)')
add('c.nohash',  [R, 'FIELD 1,8 AS A$'], 'LEN(A$)')
add('c.store',   [R, 'FIELD #1,4 AS A$', 'LSET A$="XY"'], '"<"+A$+">"')
# --- e.* the prologue's refusals -------------------------------------------------
add('e.closed',  ['FIELD #1,8 AS A$'], '1')
add('e.input',   ['OPEN "FP.DAT" FOR OUTPUT AS #1:PRINT #1,"X":CLOSE #1',
                  'OPEN "FP.DAT" FOR INPUT AS #1', 'FIELD #1,8 AS A$'], '1')
add('e.output',  ['OPEN "FP.DAT" FOR OUTPUT AS #1', 'FIELD #1,8 AS A$'], '1')
add('e.lpt',     ['OPEN "LPT:" FOR OUTPUT AS #1', 'FIELD #1,8 AS A$'], '1')
add('e.crt',     ['OPEN "CRT:" FOR OUTPUT AS #1', 'FIELD #1,8 AS A$'], '1')
add('e.nocomma', [R, 'FIELD #1 8 AS A$'], '1')
add('e.semi',    [R, 'FIELD #1;8 AS A$'], '1')
add('e.zero',    [R, 'FIELD #0,8 AS A$'], '1')
add('e.maxf',    [R, 'FIELD #3,8 AS A$'], '1')
add('e.str',     [R, 'FIELD #"A",8 AS A$'], '1')
add('e.ovf',     ['OPEN "FP.DAT" AS #1 LEN=4', 'FIELD #1,8 AS A$'], '1')
add('e.noarg',   [R, 'FIELD'], '1')
# --- n.* the record's span ------------------------------------------------------
add('n.two',     ['MAXFILES=2', R, 'OPEN "FQ.DAT" AS #2 LEN=16',
                  'FIELD #2,16 AS B$:FIELD #1,32 AS A$'], 'LEN(A$);LEN(B$)')
add('n.twoovf',  ['MAXFILES=2', R, 'OPEN "FQ.DAT" AS #2 LEN=16',
                  'FIELD #2,17 AS B$'], '1')
add('n.expr',    [R, 'C=1', 'FIELD #C*1,8 AS A$'], 'LEN(A$)')
add('n.exact',   [R, 'FIELD #1,16 AS A$,16 AS B$'], 'LEN(A$)+LEN(B$)')
# --- s.* the parse's shape ------------------------------------------------------
add('s.blanks',  [R, 'FIELD  #  1 ,  8 AS A$'], 'LEN(A$)')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
_orig = D.omsx_repl.run_cases
_src = os.path.join(os.path.dirname(HERE), "disk", "test720.dsk")
def _with_disk(*a, **k):
    td = tempfile.mkdtemp(prefix="fldpro_")
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
