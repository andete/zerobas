#!/usr/bin/env python3
r"""D-CONCATPEAK — the filed cause is WRONG, and the real one PREDICTS the threshold.

TODO.md (filed 2026-08-27, D-FNGCROOT / D-POOLCAP) says the remaining half of the
`CLEAR 100` divergence is:

    "str_concat snapshots BOTH operands (basic/str-engine.asm:1435), so `X$+X$`
     is 20+20 transient over the 40 B result."

🔴 THREE THINGS WRONG WITH THAT. There is no `str_concat` label; line 1435 is
`ev_f_instr` (INSTR), which does snapshot both operands -- a DIFFERENT routine.
Concatenation is `str_concat_tail` (basic/str-engine.asm:426) and it snapshots
**operand 1 only**; operand 2 is passed straight through as SH_SRC.

THE REAL MECHANISM. `sh_append` (sub/strheap.asm:1309) never appends in place: it
`heap_alloc`s a body of the COMBINED length and copies BOTH operands into it, then
repoints R and lets R's old body become garbage. So the peak is

    held  +  R's old body  +  the new body

and for `LEFT$(X$+X$,0)` with X$ of length L, held = L (X$) + 4 (A$):

    peak = L + 4 + L + 2L  =  4L + 4

🎯 THAT IS A PREDICTION, NOT A STORY: the failure threshold must MOVE WITH L.
L=20 predicts ~84, and the filed rows already bracket it (80 red, 100 green).
This probe tests L=10 (predicts ~44) and L=30 (predicts ~124) as well -- values
the filed rows never touched, so agreeing is not automatic.

⚠️ `str_concat_tail`'s own comment justifies the snapshot as *"R must be a fresh
temp we can modify in place"*. sh_append does NOT modify the body in place. What R
must be is a SLOT that can be repointed; the BODY copy buys nothing, and it is
exactly the L bytes that make the peak 4L instead of 3L.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

def mk(L):
    half = L // 2
    return 'X$="' + "A"*half + '"+"' + "B"*half + '":A$="AB"+"CD"'

NEW, PRED = {}, {}
for L, clears in ((10, (30, 40, 50, 60)), (20, (70, 80, 90, 100)),
                  (30, (110, 120, 130, 140))):
    for c in clears:
        lab = f"c{L}.{c}"
        NEW[lab] = ([f'CLEAR {c}', mk(L)], 'LEN(LEFT$(X$+X$,0))')
        PRED[lab] = (L, c, 4*L + 4)      # pre-fix model; 3L+4 is scored beside it
# 🔴 THE FIRST CUT OF THIS PROBE HAD NO CONTROL ROW, AND IT COST A WRONG VERDICT.
# When D-CONCATPEAK's own fix corrupted the heap, every row returned the TYPED
# LINE (the echo fence) instead of a value -- and because the pass/fail test below
# asks "is 'Out of string space' in the answer", an echo is not, so SIX ROWS
# SCORED `ok` ON A DEAD MACHINE. A control that must stay green, plus an explicit
# echo-fence detector, is what makes a row's `ok` mean anything.
# [[an-unnamed-outcome-reads-as-no-outcome]] [[trapsvc-echo-fence]]
CTL = {
    'ctl.num':  ([], '1+1'),                       # nothing string-related
    'ctl.str':  (['A$="HI"'], 'A$'),               # strings work at all
    'ctl.cat':  (['A$="AB":B$="CD"'], 'A$+B$'),    # CONCAT works at all
}
CTL_WANT = {'ctl.num': '2', 'ctl.str': 'HI', 'ctl.cat': 'ABCD'}
D.CASES.update(NEW)
D.CASES.update(CTL)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels + sorted(CTL)) for s in sides}

# --- controls FIRST: nothing below is readable if one of these moved ---------
dead = []
for c, want in sorted(CTL_WANT.items()):
    got = str(res.get("zb", {}).get(c))
    print(f"{'CTL':<6} {c:<10} want {want!r:<8} got {got!r}")
    if got != want:
        dead.append(c)
if dead:
    print(f"\n🔴 CONTROL ROW(S) FAILED: {' '.join(dead)} — the machine is broken "
          f"and NO row below is a reading. (An echo-fence answer is not a pass.)")
    raise SystemExit(2)
print()
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  {'L':>3s} {'CLEAR':>6s} {'pred':>5s}  "
      + "  ".join(f"{s:>22}" for s in sides) + "   model")
bad = []
for l in sorted(labels, key=lambda x: (PRED[x][0], PRED[x][1])):
    L, c, thr = PRED[l]
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    want_fail = c < thr
    # an echo-fence answer is neither a pass nor a fail -- it is NO READING
    if "LEFT$" in zb or "PRINT" in zb:
        print(f"{l:<{w}}  {L:>3d} {c:>6d} {thr:>5d}  🔴 ECHO FENCE — no reading")
        bad.append(l); continue
    got_fail = "Out of string space" in zb
    ok = (want_fail == got_fail)
    if not ok: bad.append(l)
    print(f"{l:<{w}}  {L:>3d} {c:>6d} {thr:>5d}  "
          + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides)
          + f"   {'ok' if ok else 'MISS'} ({'fail' if want_fail else 'pass'} predicted)")
print()
# 🎯 SCORE BOTH MODELS. The pre-fix code copied op1 into R and then allocated a
# fresh lenR+lenTk body while R's was still live -> peak 4L+4. sap_try_extend
# (D-CONCATPEAK) grows R in place instead, so the extra body is `ext`, not
# `lenR+ext` -> peak 3L+4. A fix that works must move the tree from one model to
# the OTHER, not merely stop failing: both are scored so the run says WHICH.
for name, coeff in (("4L+4 (pre-fix)", 4), ("3L+4 (in-place extend)", 3)):
    miss = []
    for l in labels:
        L, c, _ = PRED[l]
        thr = coeff * L + 4
        zb = str(res["zb"].get(l))
        if "LEFT$" in zb or "PRINT" in zb:
            miss.append(l); continue
        if (c < thr) != ("Out of string space" in zb):
            miss.append(l)
    print(f"model peak = {name:<24s} {len(labels)-len(miss):>2d}/{len(labels)} rows"
          + (f"   MISSES: {' '.join(miss)}" if miss else "   ✅ FITS"))
refs = [x for x in sides if x != "zb"]
if refs:
    d = [l for l in labels if any(res["zb"].get(l) != res[r].get(l) for r in refs)]
    print(f"\nDIFF vs references: {len(d)}/{len(labels)}" + ("  " + " ".join(d) if d else ""))
