#!/usr/bin/env python3
r"""D-STRFLT — STR$ of a NON-INTEGER, and the spaces nobody could see.

`scratchpad/val_probe.py` left four rows red after D-VALFLT, and all four are
STR$: `STR$(1.5)` -> 1, `STR$(.5)` -> 0, `STR$(1E9)` -> 0. str_fn_str formats
`DE` with pu_fmt_int and never looks at FACTYP, so a float argument is silently
the int16 flt_to_int16 left behind.

🔴 AND THE HARNESS CANNOT SEE A LEADING OR TRAILING SPACE. It prints
`"[";expr;"]"` and the capture strips, so ` 1.5` and `1.5` read the same. MSX
number format puts a space (or `-`) in FRONT of every number and PRINT adds one
BEHIND -- and STR$ is documented to carry the leading one and not the trailing
one. That difference is invisible to every row above, so this probe pins it two
ways: an explicit `"<"+...+">"` fence, and LEN.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr, extra=None):
    CASES[lab] = (setup, expr, list(extra or [])); ORDER.append(lab)

# --- the values ------------------------------------------------------------
add('v.int',     [], 'STR$(34)')
add('v.neg',     [], 'STR$(-34)')
add('v.zero',    [], 'STR$(0)')
add('v.frac',    [], 'STR$(1.5)')
add('v.negfrac', [], 'STR$(-1.5)')
add('v.small',   [], 'STR$(.5)')
add('v.big',     [], 'STR$(1E9)')
add('v.efrm',    [], 'STR$(1E-5)')
add('v.dbl',     [], 'STR$(1.234567890123#)')
add('v.expr',    [], 'STR$(3/2)')

# --- 🔴 THE SPACES, FENCED. `<` and `>` are printed by the program, so a
# leading or trailing space inside the string shows up between them.
add('q.int',     [], '"<"+STR$(34)+">"')
add('q.neg',     [], '"<"+STR$(-34)+">"')
add('q.frac',    [], '"<"+STR$(1.5)+">"')
add('q.big',     [], '"<"+STR$(1E9)+">"')

# --- and the same fact as a NUMBER, because a fence can be eaten by the
# capture and a length cannot.
add('l.int',     [], 'LEN(STR$(34))')
add('l.neg',     [], 'LEN(STR$(-34))')
add('l.zero',    [], 'LEN(STR$(0))')
add('l.frac',    [], 'LEN(STR$(1.5))')
add('l.small',   [], 'LEN(STR$(.5))')
add('l.big',     [], 'LEN(STR$(1E9))')

# --- round trips: VAL is now correct, so a failure here is STR$'s ----------
add('r.frac',    [], 'VAL(STR$(1.5))')
add('r.big',     [], 'VAL(STR$(1E9))')
add('r.neg',     [], 'VAL(STR$(-1.5))')

# --- 🟢 CONTROLS: the same values through PRINT, which already dispatches on
# FACTYP. If these are wrong too, the defect is the FORMATTER, not STR$.
add('ctl.frac',  [], '1.5')
add('ctl.big',   [], '1E9')
add('ctl.small', [], '.5')
add('ctl.num',   [], '1+1')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
if not ORDER or not res:
    raise SystemExit("🔴 REFUSING: empty row set or no sides — nothing to report on")
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
