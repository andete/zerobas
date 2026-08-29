#!/usr/bin/env python3
r"""D-NGRAM9 — one `str_target_parse` for INPUT# / LINE INPUT / MID$-statement.

All three ran the identical 13 B sequence: require the `$` suffix, raise ERR 2
without it, parse the reference (array element included), and raise a deferred
numeric fault from the subscript. Low 114 -> 134 B free, page 1 335 -> 331.

🔴 BOTH BAILS GET ROWS, and that is the D-NGRAM8 lesson applied: a row set that
covers only the type check leaves `jp nz,fp_runtime_error` -- the DEFERRED-fault
half -- unwitnessed, and a break there would be invisible.

⚠️ NO SUCCESS ROW FOR `LINE INPUT A$`: it waits on the keyboard and would hang
the harness. Its type-check bail raises before any input is read, so the error
row is safe; the success path is covered by the other two sites.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- the TYPE-CHECK bail (`jp z,stmt_error`), one row per site --------------
add('s.mid.num',   ['A=1', 'MID$(A,1,1)="X"'], '"done"')      # ex_mid_stmt
add('s.line.num',  ['LINE INPUT A'],           '"done"')      # inpc_line
add('s.inp.num',   ['INPUT#1,A'],              '"done"')      # inp_readvar

# --- the DEFERRED-FAULT bail (`jp nz,fp_runtime_error`) ---------------------
# a subscript whose evaluation leaves a pending numeric fault
add('s.mid.sub',   ['DIM A$(3)', 'MID$(A$(0*(1/0)),1,1)="X"'], '"done"')

# --- 🟢 the success path where it can be reached ----------------------------
add('g.mid',       ['A$="ABCDE"', 'MID$(A$,2,2)="XY"'], 'A$')
add('g.mid.ary',   ['DIM A$(3)', 'A$(1)="ABCDE"', 'MID$(A$(1),2,2)="XY"'], 'A$(1)')
add('ctl.num',     [], '1+1')
add('ctl.str',     ['B$="HI"'], 'B$')

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
    if "<NO OUTPUT>" in zb or "<NO CAPTURE>" in zb or "MID$" in zb or "INPUT" in zb:
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>20}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}" + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
