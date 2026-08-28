#!/usr/bin/env python3
r"""D-NGRAM3 — one `le_call` for five lineedit sub-ROM call sites, per SITE.

The identical 14 B run drove SUBROM_IDX_LINEEDIT at five sites: LIST, the line
STORE, DELETE, RENUM and AUTO. One 15 B body plus five 3 B calls, and a 3 B
second entry (`le_call_op`) for the four that set LE_OP immediately before:
-49 B of page 1 (226 -> 275 B free).

🔴 SAME HAZARD AS D-NGRAM2: the risk is not a wrong helper, it is a SITE THAT WAS
NEVER REWIRED -- it behaves identically and the saving quietly comes up short. So
there is a row per site and the knife must move all of them.

🟢 The line STORE needs no row of its own: this harness TYPES its program, so
every row here goes through that site already. A store failure would blank the
whole run, which is why the numeric control is the last line of defence.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- one row per SITE, on its LE_STATUS-carrying path -----------------------
add('s.list.junk',   ['LIST 10-20 X'],        '"done"')   # LIST  -> status 2
add('s.del.high',    ['DELETE 999'],          '"done"')   # DELETE-> status 5
add('s.del.rev',     ['DELETE 20-10'],        '"done"')   # DELETE-> status 5
add('s.renum.junk',  ['RENUM 10,10,10 X'],    '"done"')   # RENUM -> status 2
add('s.auto.zero',   ['AUTO ,'],              '"done"')   # AUTO  -> status 5
add('s.auto.junk',   ['AUTO 10,10 X'],        '"done"')   # AUTO  -> status 2

# --- 🔴 THE OK PATHS OF LIST/DELETE/RENUM CANNOT BE WITNESSED IN THIS FIXTURE,
# and the first cut of this probe pretended otherwise. `DELETE 10`,
# `RENUM 100,10,10` and `LIST 10-10` all operate on the harness's OWN typed
# program, so a successful one destroys the very lines that would report the
# result: all three read `";"ok";"` -- the ECHO of the typed source -- on ALL
# THREE sides, and scored SAME. Three echoes agreeing is not agreement.
# They are removed rather than left as decoration; what stands in for them is
# (a) ctl.store below, which proves the line-STORE site works because this
# harness TYPES its program through it, and (b) knife K-NG3, which requires
# every subject row to move. [[an-unnamed-outcome-reads-as-no-outcome]]
add('ctl.num',       [],                      '1+1')
add('ctl.store',     ['A=7'],                 'A')
add('ctl.str',       ['B$="HI"'],             'B$')

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
    # a row that answers with the TYPED SOURCE is an echo -- no reading either.
    # `<NO OUTPUT>` is not the only way to measure nothing.
    if "<NO OUTPUT>" in zb or "<NO CAPTURE>" in zb or '"' in zb: blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}" + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND (no capture on any side -- NOT a reading): "
          + " ".join(blind))
    raise SystemExit(2)
