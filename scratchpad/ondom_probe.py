#!/usr/bin/env python3
r"""D-ONDOM — the VALUE domain of `ON n GOTO` / `ON n GOSUB`.

`scratchpad/missop3_probe.py` covers `ON 1 GOTO` with the target list MISSING.
Nothing covers the SELECTOR's domain: what `n` may be, what happens when it
selects past the end of the list, and what a non-integer or out-of-range `n`
does.

⚠️ THE INTERESTING HALF IS THE ONE THAT DOES NOT RAISE. MSX BASIC's rule is that
`n` out of the list's range simply falls through to the next statement -- so a
wrong answer here is SILENT (the branch is not taken, or the wrong one is), which
this project ranks worse than a refusal. There is no error code to notice.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# The fixture puts setup at 20/30/40/50 and the value at 60. A row that BRANCHES
# lands on 60 and prints its value; a row that FALLS THROUGH reaches the next
# setup line first, so the two are told apart by what the value says.

# --- selecting within the list ---------------------------------------------
add('s.first',   ['ON 1 GOTO 60'],                    '"took-1"')
add('s.second',  ['ON 2 GOTO 40,60', 'A=0'],          '"took-2"')

# --- 🔴 selecting PAST the list: falls through, no error --------------------
add('s.past',    ['ON 3 GOTO 60', 'B$="fell"'],       'B$')
add('s.zero',    ['ON 0 GOTO 60', 'B$="fell"'],       'B$')

# --- the selector's own domain ----------------------------------------------
add('d.neg',     ['ON -1 GOTO 60', 'B$="fell"'],      'B$')
add('d.frac',    ['ON 1.7 GOTO 40,60', 'A=0'],        '"took"')
add('d.frac4',   ['ON 1.4 GOTO 60,40', 'A=0'],        '"took"')
add('d.big',     ['ON 256 GOTO 60', 'B$="fell"'],     'B$')
add('d.over',    ['ON 32768 GOTO 60', 'B$="fell"'],   'B$')
add('d.expr',    ['A=2', 'ON A GOTO 40,60', 'B=0'],   '"took-expr"')

# --- 🔴 the ORDERING twin: a fault in the selector must win -----------------
add('o.pend',    ['ON 0*(1/0)+1 GOTO 60', 'B$="fell"'], 'B$')

# --- GOSUB's mirror ----------------------------------------------------------
add('g.gosub',   ['A=0', 'ON 1 GOSUB 50', 'GOTO 60', 'A=7:RETURN'], 'A')
add('g.gospast', ['A=9', 'ON 5 GOSUB 50', 'GOTO 60', 'A=7:RETURN'], 'A')

# --- 🟢 controls ------------------------------------------------------------
add('ctl.num',   [], '1+1')
add('ctl.goto',  ['GOTO 60'], '"plain"')

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
