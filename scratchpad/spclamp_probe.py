#!/usr/bin/env python3
r"""D-SPCLAMP — does SPACE$/STRING$ RAISE or CLAMP past the string ceiling?

Filed by D-STRLONG and never run. `basic/PROVENANCE.md` justifies these two
verbs' clamp as "identical to the concat/substring STRMAX-clamp philosophy" --
and D-STRLONG made the CONCAT half RAISE, so the cell cites a sibling that went
the other way. That is not evidence the verbs are wrong; it is evidence nobody
had asked.

🔴 AND THE FILED PREDICTION IS ITSELF A GUESS: STRMAX is 255, the byte ceiling,
so a count over 255 cannot be REPRESENTED in the byte the argument coerces to --
so the failure is likely `Illegal function call` AT THE COERCION and not a clamp
at all. Both stories are written down; neither has been run. This runs them.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- over the byte ceiling: raise, clamp, or refuse at the coercion? --------
add('s.string.300', [], 'LEN(STRING$(300,"A"))')
add('s.space.300',  [], 'LEN(SPACE$(300))')
# --- the exact boundary pair ------------------------------------------------
add('s.string.255', [], 'LEN(STRING$(255,"A"))')
add('s.string.256', [], 'LEN(STRING$(256,"A"))')
add('s.space.255',  [], 'LEN(SPACE$(255))')
add('s.space.256',  [], 'LEN(SPACE$(256))')
# --- the negative and int16 edges the same coercion owns --------------------
add('s.string.neg', [], 'LEN(STRING$(-1,"A"))')
add('s.space.32768',[], 'LEN(SPACE$(32768))')
# --- 🔴 SEPARATE THE POOL FROM THE CEILING ---------------------------------
# `LEN(STRING$(255,"A"))` raises ERR 14 at the DEFAULT pool (200 bytes), which
# would let a wrong ceiling hide behind an out-of-space answer: the row agrees
# for a reason that has nothing to do with the question asked.
# [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
add('s.string.255c', ['CLEAR 600'], 'LEN(STRING$(255,"A"))')
add('s.space.255c',  ['CLEAR 600'], 'LEN(SPACE$(255))')
add('s.string.256c', ['CLEAR 600'], 'LEN(STRING$(256,"A"))')

# --- 🟢 controls: the verbs work, and the harness is sound ------------------
add('g.string',     [], 'STRING$(3,"A")')
add('g.space',      [], 'LEN(SPACE$(3))')
add('ctl.num',      [], '1+1')

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
    if "<NO OUTPUT>" in zb or "<NO CAPTURE>" in zb or "STRING$" in zb or "SPACE$" in zb:
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>20}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}" + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
