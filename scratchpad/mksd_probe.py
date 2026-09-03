#!/usr/bin/env python3
r"""D-MKSD — the reference's MKS$ / MKD$ / CVS / CVD surface, before writing ours.

These four are MISSING here: `MKS$`/`MKD$`/`CVS`/`CVD` are absent from
`basic/kwtable.inc` entirely (148 entries; only `MKI$` and `CVI` from the family),
so `MKS$(1.5)` is not even tokenised as a keyword — it parses as the string ARRAY
`MKS$(1)`, which is why `LEN(MKS$(1.5))` reads 0 and the verb "returns an empty
string". A silent wrong answer, which this project ranks worse than a refusal.

🎯 THE ORACLE IS THE CF-3300, AND THE VG-8020 IS RECORDED RATHER THAN DROPPED.
These are Disk-BASIC verbs: the cassette VG-8020 raises ERR 5 on all of them. Same
disk-vs-cassette split D-LSETREF settled for `LSET`/`CVI`. Both sides are printed
so the split is visible in the table instead of asserted in prose.

🔬 THE INSTRUMENT IS THE BYTES, NOT `LEN`. `LEN` would have called a 4-byte
string in the WRONG FORMAT a pass, and a pad-width divergence hid behind exactly
that reasoning until D-LSETREF used the bytes instead. `b.*` reads each character
back with ASC, so the format is compared and not merely the length.

🟢 CONTROLS. `c.mki*` is the integer sibling, which SHIPS here and round-trips —
it says the fixture, the `ASC(MID$(...))` readout and the family's calling shape
are all sound before any `s.*`/`d.*` row is believed. `c.stored` reads the same
value out of an ordinary variable via VARPTR, so a divergence between it and
`b.mks` is a MKS$ divergence and not a float-representation one (that question was
settled separately: docs/spec-basic-faczero.md §0, byte-identical on all three).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

def chars(s, n):
    """the n characters of string expression `s`, as byte values"""
    return ";".join(f"ASC(MID$({s},{i},1))" for i in range(1, n + 1))

# --- 🟢 CONTROLS: the integer sibling, which ships here ---------------------
add('c.mkilen', [], 'LEN(MKI$(258))')
add('c.mkibytes', [], chars('MKI$(258)', 2))
add('c.cvi',    [], 'CVI(MKI$(258))')
add('c.stored', ['A!=1.5'], ";".join(f"PEEK(VARPTR(A!)+{i})" for i in range(4)))

# --- LENGTH: the coarse question ------------------------------------------
add('s.len',    [], 'LEN(MKS$(1.5))')
add('d.len',    [], 'LEN(MKD$(1.5))')
add('s.lenint', [], 'LEN(MKS$(1))')
add('d.lenint', [], 'LEN(MKD$(1))')

# --- BYTES: the real question ----------------------------------------------
add('b.mks',    [], chars('MKS$(1.5)', 4))
add('b.mkd',    [], chars('MKD$(1.5)', 8))
add('b.mksneg', [], chars('MKS$(-1.5)', 4))
add('b.mkszero',[], chars('MKS$(0)', 4))
add('b.mksint', [], chars('MKS$(1)', 4))

# --- ROUND TRIP -------------------------------------------------------------
add('r.cvs',    [], 'CVS(MKS$(1.5))')
add('r.cvd',    [], 'CVD(MKD$(1.5))')
add('r.cvsneg', [], 'CVS(MKS$(-1.5))')
add('r.cvszero',[], 'CVS(MKS$(0))')
add('r.third',  [], 'CVD(MKD$(1/3))')

# --- ARGUMENT COERCION: what type does each verb accept? -------------------
add('a.mksdbl', [], 'CVS(MKS$(1.23456789#))')     # double -> single: rounds?
add('a.mkdint', [], 'CVD(MKD$(7))')
add('a.mkspct', [], 'CVS(MKS$(3%))')

# --- CROSS-WIDTH: a string that is the wrong length for the reader ---------
add('x.cvimks', [], 'CVI(MKS$(1.5))')             # 2 bytes out of a 4-byte string
add('x.cvdmks', [], 'CVD(MKS$(1.5))')             # 8 wanted, 4 present -> ?
add('x.cvsshort',[], 'CVS("AB")')                 # too short -> which error?
add('x.cvslong', [], 'CVS("ABCDEFGH")')           # extra bytes ignored?
add('x.cvsempty',[], 'CVS("")')

# --- WRONG TYPES and malformed calls ---------------------------------------
add('e.mksstr', [], 'MKS$("A")')
add('e.cvsnum', [], 'CVS(5)')
add('e.mksnoarg',[], 'LEN(MKS$)')
add('e.mksempty',[], 'LEN(MKS$())')

# --- DOMAIN -----------------------------------------------------------------
add('v.big',    [], 'CVS(MKS$(1E30))')
add('v.small',  [], 'CVS(MKS$(1E-30))')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>28}" for s in sides) + "   verdict")
diff = []
for l in ORDER:
    vals = [str(res[s].get(l)) for s in sides]
    # the ORACLE comparison is cf3300 vs zb; vg8020 is printed for the record
    same = vals[1] == vals[2] if len(vals) == 3 else len(set(vals)) == 1
    if not same: diff.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{v:>28}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF (cf3300 vs zb): {len(diff)}/{len(ORDER)}  " + " ".join(diff))
print("done")
