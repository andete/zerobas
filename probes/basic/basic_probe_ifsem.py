#!/usr/bin/env python3
r"""D-IFSEM — the review tier reaches `IF`, whose EXECUTION is untested.

Joost's standing tier says: when the 🤖 queue drains, review each statement's
implementation in full. The queue drained 2026-09-02. The thin section is
already walked, so what is left is the "covered by an arc under another name"
groups — with the worklist's own instruction: **verify the arc actually reads
the MECHANISM before trusting the name.**

🎯 WHY `IF` FAILS THAT TEST. Its claimed cover is "interp.asm core: lineerr +
unit tests". `lineerr` is about LINE ENTRY. `lnblank` has ELSE rows
(`expk-else`, `ref-else`, `lnr-else`, `lnrd-else`) but they are about how ELSE
CRUNCHES. There is no `spec-basic-if.md`, and `IF` appears in dozens of probes
as FIXTURE SCAFFOLDING rather than as a subject — `direct_ctrl`'s single
`if_then` row is the whole execution surface. A statement the entire battery
leans on is measured by almost nothing.

Two mechanism smells from reading `ex_if` + `if_skip_to_else` + `tok_skip`:

  S1  NO TYPE CHECK ON A STRING CONDITION. Truthiness is `FACTYP==2 ? DE :
      (FAC lead byte != 0)`, and sysvars.inc says FACTYP is `2=int / 4=single /
      8=double` — there is NO string value. So a string condition cannot be
      recognised there; it would have a descriptor read as a float exponent.
      `check_expr_errors` runs first and catches `IF A$<5` (a comparison), but a
      BARE `IF A$ THEN` is a different shape.

  S2  DANGLING `ELSE`. `if_skip_to_else` scans for the first ELSE token with NO
      IF-NESTING AWARENESS, so on a false outer condition in
      `IF a THEN IF b THEN x ELSE y` it lands on the INNER IF's ELSE.

🟢 `tok_skip` itself is SOUND and is not the suspicion: it is quote-aware
(`tsk_str`), REM-aware, DATA-aware and carries float-mantissa strides — the
D-DATACOLON lesson visibly applied. Recorded so nobody re-walks it.

🔴 PREDICTIONS:
  P1  the string-condition rows raise `Type mismatch` on BOTH machines — eval
      rejects it before truthiness is reached. If zerobas instead prints a
      branch, S1 is a real defect.
  P2  the dangling-ELSE rows AGREE, because MSX BASIC's `IF` is famously flat
      and a flat scan is what the reference does too. A disagreement here would
      be the more interesting outcome.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- 🟢 CONTROLS: the shapes everything else is read against ---------------
add('c.true',    ['IF 1 THEN A=1 ELSE A=2'],            'A')
add('c.false',   ['IF 0 THEN A=1 ELSE A=2'],            'A')
add('c.noelse',  ['A=9', 'IF 0 THEN A=1'],              'A')
add('c.goto',    ['IF 1 GOTO 40', 'A=1'],               '"unreached"')
add('c.float',   ['IF .5 THEN A=1 ELSE A=2'],           'A')
add('c.negfloat',['IF -.5 THEN A=1 ELSE A=2'],          'A')

# --- S1: a STRING condition ------------------------------------------------
add('s.strvar',  ['A$="X"', 'IF A$ THEN B=1 ELSE B=2'], 'B')
add('s.strempty',['A$=""',  'IF A$ THEN B=1 ELSE B=2'], 'B')
add('s.strlit',  ['IF "X" THEN B=1 ELSE B=2'],          'B')

# --- S2: DANGLING ELSE, nested IF ------------------------------------------
# outer FALSE: does the scan stop at the INNER if's ELSE and run it?
add('n.dangle',  ['B=9', 'IF 0 THEN IF 1 THEN B=1 ELSE B=2'], 'B'),
# outer TRUE, inner FALSE: the ELSE plainly belongs to the inner IF
add('n.dangle2', ['B=9', 'IF 1 THEN IF 0 THEN B=1 ELSE B=2'], 'B'),
# outer TRUE, inner TRUE
add('n.dangle3', ['B=9', 'IF 1 THEN IF 1 THEN B=1 ELSE B=2'], 'B'),
# and the statement AFTER a taken/untaken nested IF on the same line
add('n.after',   ['B=9', 'IF 0 THEN IF 1 THEN B=1 ELSE B=2:B=B+100'], 'B'),

# 🔴 TWO RULES FIT THE ROWS ABOVE AND THEY SEPARATE HERE.
#   R1  "a FALSE `IF` ends the LINE" -- an ELSE anywhere after it is dead.
#   R2  "the scan COUNTS NESTING" -- each nested IF consumes one ELSE, so an
#       ELSE at the OUTER level still catches.
# Both predict refs=9 for n.dangle. They differ when there IS an outer ELSE:
# R1 -> B stays 9, R2 -> B=3. Getting this wrong picks the wrong fix.
# [[two-rules-that-coincide-on-every-row-you-have]]
add('n.outerelse', ['B=9', 'IF 0 THEN IF 1 THEN B=1 ELSE B=2 ELSE B=3'], 'B'),
# the same shape with the INNER if false, so the inner ELSE is the live one
add('n.outerelse2',['B=9', 'IF 0 THEN IF 0 THEN B=1 ELSE B=2 ELSE B=3'], 'B'),
# 🟢 CONTROL: a plain outer ELSE with NO nesting -- must be 3 everywhere, and
# if it is not, the fixture cannot express the question at all.
add('n.plainelse', ['B=9', 'IF 0 THEN B=1 ELSE B=3'], 'B'),

# --- ROUND 2: the rest of the interp.asm core group, and DEPTH-2 regression --
# 🎯 DEPTH 2 IS THE ROW THE FIX ITSELF NEEDS. D-IFSEM's counter was validated at
# depth 1 only; two nested IFs must consume TWO ELSEs before the outer one
# catches. A counter that saturated, or a boolean instead of a count, passes
# every depth-1 row and fails here.
add('d.depth2',  ['B=9', 'IF 0 THEN IF 1 THEN IF 1 THEN B=1 ELSE B=2 ELSE B=3 ELSE B=4'], 'B'),
add('d.depth2b', ['B=9', 'IF 1 THEN IF 0 THEN IF 1 THEN B=1 ELSE B=2 ELSE B=3 ELSE B=4'], 'B'),
# --- REM / apostrophe swallow the rest of the line -- INCLUDING an ELSE? -----
# tok_skip's tsk_rem consumes to EOL, so the scan cannot see an ELSE behind a
# REM. Whether that is RIGHT is a reference question, not a code question.
add('r.rem',     ['B=9', "IF 0 THEN REM ELSE B=1"],   'B'),
add('r.quote',   ['B=9', "IF 0 THEN 'X ELSE B=1"],    'B'),
add('r.remtrue', ['B=9', "IF 1 THEN REM ELSE B=1"],   'B'),
# --- the IF <expr> GOTO form, with an ELSE after it --------------------------
add('g.gotoelse',['B=9', 'IF 0 GOTO 900 ELSE B=1'],   'B'),
# --- a nested IF in the ELSE BRANCH (taken path, not the skip path) ----------
add('e.nestelse',['B=9', 'IF 0 THEN B=1 ELSE IF 1 THEN B=2 ELSE B=3'], 'B'),
add('e.nestelse2',['B=9','IF 0 THEN B=1 ELSE IF 0 THEN B=2 ELSE B=3'], 'B'),
# --- END / STOP inside a branch ---------------------------------------------
add('x.endelse', ['B=9', 'IF 1 THEN B=5 ELSE END'],   'B'),

D.CASES.update(CASES)
GATE = "--gate" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
sides = (args[0] if args else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>18}" for s in sides) + "   verdict")
diff = []
for l in ORDER:
    vals = [str(res[s].get(l)) for s in sides]
    same = len(set(vals)) == 1
    if not same: diff.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{v:>18}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
# ⚠️ NOT `DIFF <n>/<m>`: `filed_row_sweep.py`'s MARKER counts a line
# starting `DIFF ` as one more DIVERGING ROW, so a summary in that shape
# inflates the count -- and with a colon it matches NOTHING and the sweep
# reads the probe's pinned rows as no longer diverging. Fourth, fifth and
# sixth instances of a class that had already bitten three times;
# `rowshape-check` enforces it now (D-MARKERWORD).
print(f"\n{len(diff)}/{len(ORDER)} rows diverging  " + " ".join(diff))
print("🟢 CONTROLS: c.* are the shapes every other row is read against -- float\n"
      "   truthiness (IF .5 / IF -.5), the plain no-nesting ELSE, and the\n"
      "   no-ELSE line-end. If one of those reddens, no n.* row means anything.")
if GATE:
    sys.exit(1 if diff else 0)
