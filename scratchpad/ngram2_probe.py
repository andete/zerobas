#!/usr/bin/env python3
r"""D-NGRAM2 — one shared `req_operand` for six open-coded copies, witnessed per SITE.

`call skip_spaces / or a / jp z,loc_missing / cp COLON / jp z,loc_missing` stood
open-coded at six main-region sites (12 B each). One 13 B helper plus six 3 B
calls is 31 B: -41 B of page 1, measured 185 -> 226 B free.

🔴 A COLLECTIVE WITNESS IS NOT A PER-SITE WITNESS. One knife on the helper moves
every row at once, which proves the helper is load-bearing and says NOTHING about
whether all six call sites were actually rewired -- a site left open-coded behaves
identically and would never be noticed. So there is at least one row per SITE, and
the knife's job is to show that each of them moves.

🟢 And a green control per site: the same statement with its operand PRESENT must
keep working. Without those, a helper that raised ERR 24 unconditionally would
score perfect on every subject row here.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- one SUBJECT row per site (empty slot -> ERR 24) ------------------------
add('s.locate.colon',  ['LOCATE :'],        '"done"')
add('s.locate.arg3',   ['LOCATE 5,3,:'],    '"done"')
add('s.play.bare',     ['PLAY'],            '"done"')
add('s.play.colon',    ['PLAY:'],           '"done"')
add('s.using.bare',    ['PRINT USING'],     '"done"')
add('s.using.colon',   ['PRINT USING:'],    '"done"')
add('s.using.list',    ['PRINT USING"##";'], '"done"')
add('s.screen.bare',   ['SCREEN'],          '"done"')
add('s.screen.colon',  ['SCREEN :'],        '"done"')
# 🔴 MODE 0, NOT MODE 1. `SCREEN 1,` leaves text mode, so the harness captures
# NOTHING and the row reads `<NO OUTPUT>` on all three sides -- three blanks
# agreeing, which is not a reading and would have left screen.asm:140 (one of the
# six sites) with no witness at all. Mode 0 keeps the screen readable and reaches
# the identical trailing-argument slot. [[an-unnamed-outcome-reads-as-no-outcome]]
add('s.screen.trail',  ['SCREEN 0,'],       '"done"')
add('s.screen.trailc', ['SCREEN 0,:'],      '"done"')

# --- 🟢 the operand PRESENT: every site must still work ---------------------
add('g.locate',  ['LOCATE 5,3'],            '"ok"')
add('g.play',    ['PLAY"A"'],               '"ok"')
add('g.using',   ['PRINT USING"##";1'],     '"ok"')
add('g.usingv',  ['PRINT USING"##";5'],     '"ok"')
add('g.screen',  ['SCREEN 0'],              '"ok"')
add('g.screen2', ['SCREEN 0,1'],            '"ok"')
add('ctl.num',   [],                        '1+1')

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
    if not same: diff.append(l)
    # 🔴 THREE BLANKS AGREEING IS NOT AGREEMENT.
    if "<NO OUTPUT>" in zb or "<NO CAPTURE>" in zb:
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}" + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND (no capture on any side -- NOT a reading): "
          + " ".join(blind))
    raise SystemExit(2)
