#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-P0CB slice C1 (2026-10-21): OPEN / CLOSE / MERGE / MAXFILES moved from main
into zerobas-sub2 page 0 (sub2/filestmt.asm). Each statement's answers against the
CF-3300, each row under ON ERROR GOTO (basic_probe_deffn's frame: ERR and ERL), with
a /tmp copy of disk/test720.dsk per case (the harness boots with the drive empty).
The suites cover much of this; this probe is the slice's own witness and its knives'.
  m.*  MAXFILES   o.*  OPEN   c.*  CLOSE   g.*  MERGE
    python3 -u scratchpad/filestmt_probe.py [cf3300,zb]
"""
import os, sys, shutil, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- MAXFILES -------------------------------------------------------------------
add('m.ok',      ['MAXFILES=3'], '1')
add('m.16',      ['MAXFILES=16'], '1')                  # ERR 5
add('m.big',     ['MAXFILES=40000'], '1')               # ERR 6
add('m.str',     ['MAXFILES="A"'], '1')                 # ERR 13
add('m.bare',    ['MAXFILES'], '1')                     # ERR 2
add('m.tail',    ['A=7', 'MAXFILES=1 ZZ'], 'A')         # ERR 2, variables intact?
# --- OPEN -----------------------------------------------------------------------
add('o.out',     ['OPEN "FS.DAT" FOR OUTPUT AS #1', 'PRINT #1,"HI"', 'CLOSE #1'], '1')
add('o.in',      ['OPEN "FS.DAT" FOR OUTPUT AS #1:PRINT #1,"HI":CLOSE #1',
                  'OPEN "FS.DAT" FOR INPUT AS #1', 'INPUT #1,A$'], 'A$')
add('o.app',     ['OPEN "FS.DAT" FOR OUTPUT AS #1:PRINT #1,"A":CLOSE #1',
                  'OPEN "FS.DAT" FOR APPEND AS #1:PRINT #1,"B":CLOSE #1',
                  'OPEN "FS.DAT" FOR INPUT AS #1:INPUT #1,A$,B$'], 'A$+B$')
add('o.chan0',   ['OPEN "FS.DAT" FOR OUTPUT AS #0'], '1')       # 52
add('o.chan2',   ['OPEN "FS.DAT" FOR OUTPUT AS #2'], '1')       # 52 (MAXFILES=1)
add('o.busy',    ['OPEN "FS.DAT" FOR OUTPUT AS #1', 'OPEN "FT.DAT" FOR OUTPUT AS #1'], '1')  # 54
add('o.same',    ['MAXFILES=2', 'OPEN "FS.DAT" FOR OUTPUT AS #1',
                  'OPEN "FS.DAT" FOR OUTPUT AS #2'], '1')       # 54
add('o.wild',    ['OPEN "F*.DAT" FOR OUTPUT AS #1'], '1')       # 56
add('o.nofile',  ['OPEN "NONE.DAT" FOR INPUT AS #1'], '1')      # 53
add('o.num',     ['OPEN 5 FOR OUTPUT AS #1'], '1')              # 13
add('o.junk',    ['OPEN "FS.DAT" FOR OUTPUT AS #1 ZZ'], '1')    # 2
add('o.len0',    ['OPEN "FS.DAT" AS #1 LEN=0'], '1')            # 5
add('o.lpt',     ['OPEN "LPT:" FOR OUTPUT AS #1', 'CLOSE #1'], '1')
add('o.casrnd',  ['OPEN "CAS:X" AS #1'], '1')                   # 56
add('o.grpin',   ['OPEN "GRP:" FOR INPUT AS #1'], '1')
# --- CLOSE ----------------------------------------------------------------------
add('c.zero',    ['CLOSE #0'], '1')
add('c.two',     ['CLOSE #2'], '1')
add('c.neg',     ['CLOSE #-1'], '1')
add('c.list',    ['MAXFILES=2', 'OPEN "FS.DAT" FOR OUTPUT AS #1',
                  'OPEN "FT.DAT" FOR OUTPUT AS #2:CLOSE #1,#2'], '1')
add('c.bare',    ['OPEN "FS.DAT" FOR OUTPUT AS #1', 'CLOSE', 'PRINT #1,"X"'], '1')  # 59
# --- MERGE ----------------------------------------------------------------------
add('g.bare',    ['MERGE'], '1')                                # 24
add('g.num',     ['MERGE 5'], '1')                              # 13
add('g.none',    ['MERGE "NONE.BAS"'], '1')                     # 53

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
_orig = D.omsx_repl.run_cases
_src = os.path.join(os.path.dirname(HERE), "disk", "test720.dsk")
def _with_disk(*a, **k):
    td = tempfile.mkdtemp(prefix="filestmt_")
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
