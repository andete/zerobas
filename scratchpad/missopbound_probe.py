#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-MISSOPBOUND — WHERE does the reference switch from `Missing operand` to
`Syntax error` in a factor slot?

`cursor-acceptance` (which the battery does not collect -- D-UNCOLLECTED) fails
three rows: `X=TAB(5)`, `X=SPC(5)`, `IF TAB(5)=0` read `Missing operand` here and
`Syntax error` on both references.

zerobas has ONE answer for the whole class. `basic/expr.asm` ev_f falls through
every arm to `ev_f_var`, which requires a LETTER and otherwise jumps to
`ev_f_missop` -- so every non-letter token that reaches a factor slot is
`Missing operand`. D-MISSOP measured that as correct **at 16 slots**.

🔴 SO TWO RULES FIT EVERY ROW EITHER SIDE HAS:
  (a) "a factor slot that cannot start a factor is Missing operand, except
       TAB(/SPC( which are Syntax error"   -- a special case, and
  (b) "NOTHING there (EOL / ':' / an operator) is Missing operand; a real TOKEN
       in the wrong place is Syntax error" -- a boundary.
Pick (a) and a fix is 8 bytes of special case that is wrong for every other
keyword. Pick (b) and it is wrong if the reference really does special-case
TAB(. **The rows below are chosen to SEPARATE them**
[[two-rules-that-coincide-on-every-row-you-have]].

Every row carries the `X=99` sentinel first: without it, "X left at 0" and
"errored with X already 0" are the same reading (cursor-acceptance's own note).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D                                    # noqa: E402

CASES, ORDER = {}, []
def add(lab, setup, expr='X'):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# 🟢 CONTROLS: the slot works, and the harness can see a value AND an error.
add('ctl.ok',    ['X=99', 'X=5'])
add('ctl.div0',  ['X=99', 'X=1/0'])

# --- the D-MISSOP side: NOTHING is there ------------------------------------
add('n.eol',     ['X=99', 'X='])
add('n.colon',   ['X=99', 'X=:PRINT 1'])
add('n.op',      ['X=99', 'X=*5'])
add('n.comma',   ['X=99', 'X=,5'])
add('n.close',   ['X=99', 'X=)'])

# --- the disputed rows -------------------------------------------------------
add('t.tab',     ['X=99', 'X=TAB(5)'])
add('t.spc',     ['X=99', 'X=SPC(5)'])
add('t.tabif',   ['X=99', 'IF TAB(5)=0 THEN Z=1'])

# --- OTHER real tokens in a factor slot: the rows that SEPARATE (a) from (b) --
# If these read `Syntax error` on the reference, the rule is (b) -- a boundary --
# and a TAB-only special case would be wrong at every one of them.
add('k.then',    ['X=99', 'X=THEN'])
add('k.to',      ['X=99', 'X=TO'])
add('k.step',    ['X=99', 'X=STEP'])
add('k.goto',    ['X=99', 'X=GOTO'])
add('k.print',   ['X=99', 'X=PRINT'])
add('k.input',   ['X=99', 'X=INPUT'])
add('k.using',   ['X=99', 'X=USING'])
add('k.else',    ['X=99', 'X=ELSE'])

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  {'typed':<22}  " + "  ".join(f"{s:>22}" for s in sides))
diff, blind = [], []
for l in ORDER:
    typed = CASES[l][0][-1]
    cells = [str(res[s].get(l)) for s in sides]
    zb = cells[-1] if "zb" in sides else None
    refs = [c for s, c in zip(sides, cells) if s != "zb"]
    same = all(r == zb for r in refs) if zb is not None else True
    if not same:
        diff.append(l)
    if any("<NO" in c for c in cells):
        blind.append(l)
    print(f"{l:<{w}}  {typed:<22}  " + "  ".join(f"{c:>22}" for c in cells)
          + ("" if same else "   DIFF"))
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}"
      + ("  " + " ".join(diff) if diff else ""))
print("\nREAD THE k.* ROWS: if the references say Syntax error there too, the "
      "rule is a BOUNDARY (a real token in a factor slot), not a TAB/SPC "
      "special case -- and the fix is a different shape.")
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
raise SystemExit(1 if diff else 0)
