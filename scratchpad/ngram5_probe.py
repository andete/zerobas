#!/usr/bin/env python3
r"""D-NGRAM5 — one `goto_take_bc` for GOSUB / ON..GOTO / ON..GOSUB.

The identical 15 B run (`call find_line_bc / jp nc,ex_goto_undef /
ld (GOTOTGT),hl / ld a,1 / ld (GOTOFLAG),a / ret`) stood at three sites. The
last one keeps the code and is simply LABELLED, so the third jump costs nothing:
-24 B of page 1 (275 -> 299 B free).

🔴 ONE ROW PER SITE, and both halves of the body: the FAILING half
(`jp nc,ex_goto_undef`, an undefined line) and the ARMING half (a transfer that
actually happens). A row set covering only the error half would leave the four
instructions that arm GOTOTGT/GOTOFLAG unwitnessed.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- the FAILING half: an undefined line, one row per site ------------------
add('s.gosub.undef',   ['GOSUB 12345'],        '"done"')
add('s.ongoto.undef',  ['ON 1 GOTO 12345'],    '"done"')
add('s.ongosub.undef', ['ON 1 GOSUB 12345'],   '"done"')

# --- the ARMING half: a transfer that must be DISTINGUISHABLE from falling
# through ------------------------------------------------------------------
# 🔴 THE FIRST CUT OF THESE ROWS WAS VACUOUS AND A KNIFE SAID SO. They read
# `ON 1 GOTO 60` and expected the value line to print -- but the setup lines sit
# at 20/30/... and the value line IS 60, so FALLING THROUGH lands in exactly the
# same place as taking the jump. K-N5A broke the arming half outright and moved
# ZERO rows (with the ROM provably changed), because both outcomes agree.
# 🎯 The fix is a line BETWEEN the jump and its target that only executes when
# the jump is NOT taken: A stays 1 if it was taken, becomes 2 if it was not.
# [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
add('s.ongoto.ok',     ['A=1:ON 1 GOTO 60', 'A=2'],       'A')
add('s.ongosub.ok',    ['A=1:ON 1 GOSUB 60', 'A=2'],      'A')
add('s.gosub.ok',      ['A=1:GOSUB 60', 'A=2'],           'A')
add('s.ongoto.2nd',    ['A=1:ON 2 GOTO 12345,60', 'A=2'], 'A')

# --- 🟢 controls ------------------------------------------------------------
add('g.forloop',  ['FOR I=1 TO 3:NEXT I'], 'I')
add('ctl.num',    [],                      '1+1')

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
    if "<NO OUTPUT>" in zb or "<NO CAPTURE>" in zb or "GOSUB" in zb or "GOTO" in zb:
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>20}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}" + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
