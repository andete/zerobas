#!/usr/bin/env python3
r"""D-NGRAM7 — one `gfx_call` for the three page-0 graphics-tenant entries.

PSET/PRESET (GFX_OP=1), LINE/box (3) and PAINT (5) opened with the identical
15 B run. 45 B -> a 16 B body plus three 3 B calls: -20 B of page 1
(315 -> 335 B free).

🔴 THE READBACK HAS TO SURVIVE THE MODE SWITCH. The harness captures a SCREEN 0
text screen, so a row that ends in SCREEN 2 reads `<NO OUTPUT>` on all three
sides -- three blanks agreeing (D-NGRAM2 hit exactly that). Each row therefore
DRAWS in SCREEN 2, captures the pixel with POINT into a variable, returns to
SCREEN 0, and prints the variable.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- one row per SITE ------------------------------------------------------
# ⚠️ At most FOUR setup lines: the harness puts the value on line 60 and a fifth
# collides with it (it says so and refuses, which is the right behaviour).
# Statements are joined with `:` rather than spread over lines.
add('s.pset',   ['SCREEN 2:PSET(10,10),15:A=POINT(10,10)', 'SCREEN 0'], 'A')
add('s.preset', ['SCREEN 2:PSET(10,10),15:PRESET(10,10)',
                 'A=POINT(10,10):SCREEN 0'], 'A')
add('s.line',   ['SCREEN 2:LINE(0,0)-(20,0),15:A=POINT(10,0)', 'SCREEN 0'], 'A')
add('s.linebox',['SCREEN 2:LINE(0,0)-(20,20),15,B:A=POINT(20,10)', 'SCREEN 0'], 'A')
add('s.paint',  ['SCREEN 2:LINE(0,0)-(30,30),15,B:PAINT(15,15),15',
                 'A=POINT(15,15):SCREEN 0'], 'A')

# --- 🟢 controls: the pixel BEFORE any draw, and a non-graphics path --------
add('g.blank',  ['SCREEN 2:A=POINT(50,50)', 'SCREEN 0'], 'A')
add('ctl.num',  [], '1+1')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>18}" for s in sides) + "   verdict")
diff, blind = [], []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if not same: diff.append(l)
    if "<NO OUTPUT>" in zb or "<NO CAPTURE>" in zb or "SCREEN" in zb: blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>18}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}" + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
