#!/usr/bin/env python3
r"""D-NGRAM8 — one `str_arg_snap` for LEFT$ / RIGHT$ / MID$.

All three open by evaluating the source expression, bailing if it is not a
string, and snapshotting it into an OWNED temp before the count argument is
evaluated (that evaluation can push temps of its own). Three identical runs ->
one body plus three 3 B calls: -12 B of the LOW region (106 -> 118 B free).

🔴 BOTH HALVES, one row per site: the SNAPSHOT half (a normal call) and the
BAIL half (`jp nc,str_eval_no`, a non-string argument). A row set covering only
the success half would leave the bail unwitnessed.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- the SNAPSHOT half, one row per site ------------------------------------
add('s.left',      [], 'LEFT$("ABCDE",2)')
add('s.right',     [], 'RIGHT$("ABCDE",2)')
add('s.mid',       [], 'MID$("ABCDE",2,3)')
# 🎯 the reason the snapshot exists: a count argument that itself builds a
# string, so a shared descriptor would be clobbered between the two.
# 🔴 `LEN("XY")` ALLOCATES NOTHING, so those first rows did not exercise the
# clobber at all -- K-N8B removed the snapshot outright and moved ZERO rows
# (with the ROM provably changed). The count expression has to BUILD a string
# for the source descriptor to be at risk.
add('s.left.nest', ['A$="ABCDE"', 'B$="XY"'], 'LEFT$(A$,LEN(B$+B$))')
add('s.mid.nest',  ['A$="ABCDE"', 'B$="XY"'], 'MID$(A$,LEN(B$),LEN(B$+B$))')
add('s.left.deep', ['A$="ABCDE"', 'B$="XY"'], 'LEFT$(A$+B$,LEN(B$+B$))')
add('s.right.nest',['A$="ABCDE"', 'B$="XY"'], 'RIGHT$(A$,LEN(B$+B$))')

# --- the BAIL half: a non-string argument -----------------------------------
add('s.left.bad',  [], 'LEFT$(5,2)')
add('s.right.bad', [], 'RIGHT$(5,2)')
add('s.mid.bad',   [], 'MID$(5,1,2)')

# --- 🔴 THE DECLINE WITH A FAULT ALREADY PENDING -------------------------
# THE ROW THIS PROBE WAS MISSING, AND WHY THE SUITE CAUGHT WHAT IT DID NOT.
# `.bad` above already reads DIFF (the known ERR 2 / ERR 13 divergence), so when
# the DECLINE ITSELF broke -- str_eval_no running one frame deeper behind the new
# `call`, returning INTO the verb instead of out of it -- those rows still read
# ERR 2 and the probe saw no change. AN EXISTING DIFF ROW MASKS A NEW BREAKAGE ON
# THE SAME PATH.
# What separates them is the ORDERING axis: a fault raised BEFORE the decline
# must still be the one reported. Ported from penderr-acceptance's `o.pt.left`.
# ⚠️ AND THE CONTEXT MATTERS AS MUCH AS THE EXPRESSION. Printing the expression
# reaches neither: HEAD, the shipped tree and a DELIBERATELY BROKEN decline all
# read identically on `PRINT LEFT$(0*(1/0)+1)`. The discriminating shape is the
# ASSIGNMENT -- `Q2$=LEFT$(...)` -- which is what penderr-acceptance uses.
add('s.left.pend',  ['Q2$=LEFT$(0*(1/0)+1)'],  '"done"')
add('s.right.pend', ['Q2$=RIGHT$(0*(1/0)+1)'], '"done"')
add('s.mid.pend',   ['Q2$=MID$(0*(1/0)+1)'],   '"done"')
add('s.left.pexp',  [], 'LEFT$(0*(1/0)+1)')    # the printed form, kept: it reads
add('s.mid.pexp',   [], 'MID$(0*(1/0)+1)')     # the same on all three trees

# --- 🟢 controls ------------------------------------------------------------
add('g.cat',   ['A$="AB":B$="CD"'], 'A$+B$')
add('ctl.num', [], '1+1')

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
    if "<NO OUTPUT>" in zb or "<NO CAPTURE>" in zb or "LEFT$" in zb or "MID$" in zb:
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>20}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}" + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
