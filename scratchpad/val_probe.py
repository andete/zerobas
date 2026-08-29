#!/usr/bin/env python3
r"""D-VAL — VAL is a whole number parser, and it had ONE row.

`probes/basic/basic_probe_string.py` carries exactly one VAL case:
`VAL("34")+1` -> 35. That is a thin surface for a function whose job is to
re-implement the tokeniser's numeric scanner over arbitrary user text: bases,
exponents, signs, embedded spaces, partial parses and junk.

⚠️ VAL NEVER RAISES ON JUNK -- it returns 0 -- so a wrong answer here is SILENT,
which this project ranks worse than a refusal. That is the reason to sweep it:
there is no error code to notice, only a number that is quietly not the
reference's number.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- the plain cases --------------------------------------------------------
add('p.int',     [], 'VAL("34")')
add('p.neg',     [], 'VAL("-34")')
add('p.plus',    [], 'VAL("+34")')
add('p.frac',    [], 'VAL("1.5")')
add('p.lead',    [], 'VAL(".5")')
add('p.trail',   [], 'VAL("5.")')

# --- junk and partial parses: VAL returns what it could read, never raises ---
add('j.empty',   [], 'VAL("")')
add('j.alpha',   [], 'VAL("ABC")')
add('j.tail',    [], 'VAL("12ABC")')
add('j.sign',    [], 'VAL("-")')
add('j.dot',     [], 'VAL(".")')
add('j.mid',     [], 'VAL("1.2.3")')
add('j.spacelead', [], 'VAL("  12")')
add('j.spacemid',  [], 'VAL("1 2")')
add('j.tabish',  [], 'VAL(" - 12")')

# --- bases: MSX VAL accepts the &H / &O / &B literal forms ------------------
add('b.hex',     [], 'VAL("&HFF")')
add('b.hexlow',  [], 'VAL("&hff")')
add('b.hexbare', [], 'VAL("&H")')
add('b.oct',     [], 'VAL("&O17")')
add('b.bin',     [], 'VAL("&B101")')
add('b.hextail', [], 'VAL("&HFFZZ")')
add('b.amp',     [], 'VAL("&")')
# --- base edge cases the first pass did not ask, needed BEFORE writing code ---
add('b.nopfx',   [], 'VAL("&17")')       # '&' + digits, no base letter
add('b.hsign',   [], 'VAL("-&H10")')     # a sign in front of a base literal
add('b.hspace',  [], 'VAL("&H 10")')     # a space between prefix and digits
add('b.hbad',    [], 'VAL("&HZZ")')      # prefix, then nothing valid
add('b.obad',    [], 'VAL("&O9")')       # 9 is not an octal digit
add('b.bbad',    [], 'VAL("&B2")')       # 2 is not a binary digit
add('b.hbig',    [], 'VAL("&HFFFF")')    # the 16-bit ceiling
add('b.hover',   [], 'VAL("&H1FFFF")')   # past it
add('b.lead',    [], 'VAL("  &HFF")')    # leading spaces then a base literal

# --- exponents --------------------------------------------------------------
add('e.e3',      [], 'VAL("1E3")')
add('e.eneg',    [], 'VAL("1E-3")')
add('e.d3',      [], 'VAL("1D3")')
add('e.ebare',   [], 'VAL("1E")')
add('e.big',     [], 'VAL("1E38")')

# --- STR$, which the Phase-3 deferral note pairs with VAL ("floats in
# VAL/STR$"). If the note is stale for one it may be stale for both.
add('s.int',     [], 'STR$(34)')
add('s.neg',     [], 'STR$(-34)')
add('s.frac',    [], 'STR$(1.5)')
add('s.small',   [], 'STR$(.5)')
add('s.big',     [], 'STR$(1E9)')
add('s.roundtrip', [], 'VAL(STR$(1.5))')

# --- 🟢 the arithmetic context, which is what the one existing row tested ----
add('g.plus1',   [], 'VAL("34")+1')
add('g.var',     ['A$="7.5"'], 'VAL(A$)*2')
# --- 🔴 CONTROLS THAT SEPARATE THE LAYERS. If these are wrong too, the gap is
# FLOAT LITERALS and the arithmetic path, not VAL/STR$ -- a completely different
# (and much larger) finding. Naming the second possible cause before attributing
# the defect. [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
add('c.lit',     [], '1.5')
add('c.litbig',  [], '1E9')
add('c.arith',   [], '3/2')
add('c.hexlit',  [], '&HFF')
add('ctl.num',   [], '1+1')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides) + "   verdict")
diff, blind, no_oracle = [], [], []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if len(set(refs)) > 1:
        no_oracle.append(l)
    elif not same:
        diff.append(l)
    if any(any(m in str(res[s].get(l)) for m in ("<NO OUTPUT>", "<NO CAPTURE>", ';"'))
           for s in sides):
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides)
          + f"   {'NO-ORACLE' if l in no_oracle else ('SAME' if same else 'DIFF')}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER) - len(no_oracle)} scorable"
      + ("  " + " ".join(diff) if diff else ""))
if no_oracle:
    print(f"⚠️  {len(no_oracle)} NO-ORACLE row(s): " + " ".join(no_oracle))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
