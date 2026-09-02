#!/usr/bin/env python3
r"""D-PRINTZONE — `PRINT`'s own surface, which nothing gates.

Review tier, arc-covered group `print/lprint/llist`, claimed cover "LPT arc +
print specs". Verifying that name the way D-IFSEM did:

  * `spec-basic-print-unparen-compare.md` is ONE corner (unparenthesised
    comparison); `spec-print-hash-using.md` is `PRINT# USING`;
    `lptverb-acceptance` is the LPRINT/LLIST VERB surface.
  * There is NO general PRINT spec and NO `print-acceptance`.
  * And every probe in this tree prints with SEMICOLONS (`PRINT"[";x;"]"`), so
    the COMMA-ZONE, TAB, SPC and trailing-separator behaviour is barely
    exercised by anything.

Same shape as `IF`: the statement the whole battery leans on, measured almost
nowhere. (Comma zones ARE tested for LPRINT — `runtail`'s `lpr-comma` — which is
the printer path, not this one.)

🔴 ROUND 1'S READOUT WAS STRUCTURALLY BLIND, AND ITS CONTROL SAID SO. The rows
first read `POS(0)` as the harness EXPRESSION -- but the fixture emits
`60 CLS:PRINT"[";<expr>;"]"`, and that **CLS resets the cursor** before the read.
All 21 rows returned 1, `p.ctl` (`PRINT"AB";` -> expected 3) included. A row set
whose geometry cannot reach the case, caught by the one row written to fail if
the instrument was wrong. The read now happens ON THE SAME LINE as the print,
into a variable the harness then reports.
[[a-coverage-row-whose-geometry-cannot-reach-the-case]]

🎯 THE INSTRUMENT IS `POS(0)`, NOT THE SCREEN TEXT. A column is a NUMBER; read as
text it collapses under any whitespace-normalising face, which is exactly how a
pad-width divergence hid in D-LSETREF until `LEN` was used instead. `POS(0)` is
also independently sound here: its argument is parsed and DISCARDED (measured,
expr.asm), and `p.ctl` pins it.

⚠️ EVERY ROW IS SCREEN PRINT (no `#`), so nothing here depends on the disk or
printer fixtures.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# --- 🟢 CONTROLS: POS(0) itself, and the semicolon path everything uses -----
add('p.ctl', ['PRINT"AB";'+':X=POS(0)'], 'X')
add('p.ctl0', ['PRINT"";'+':X=POS(0)'], 'X')
add('p.semi', ['PRINT 1;'+':X=POS(0)'], 'X')

# --- COMMA ZONES: the surface nothing exercises ----------------------------
add('z.comma', ['PRINT"A",'+':X=POS(0)'], 'X')
add('z.comma2', ['PRINT"A","B",'+':X=POS(0)'], 'X')
add('z.commanum', ['PRINT 1,'+':X=POS(0)'], 'X')
add('z.commawide', ['PRINT"ABCDEFGHIJKLMNOP",'+':X=POS(0)'], 'X')
add('z.commaempty', ['PRINT ,'+':X=POS(0)'], 'X')
add('z.twocomma', ['PRINT"A",,'+':X=POS(0)'], 'X')

# --- TAB(): absolute column, including BACKWARDS ---------------------------
add('t.tab', ['PRINT TAB(10);'+':X=POS(0)'], 'X')
add('t.tab0', ['PRINT TAB(0);'+':X=POS(0)'], 'X')
add('t.tab1', ['PRINT TAB(1);'+':X=POS(0)'], 'X')
add('t.tabback', ['PRINT"ABCDEF";TAB(3);'+':X=POS(0)'], 'X')
add('t.tabwide', ['PRINT TAB(45);'+':X=POS(0)'], 'X')
# 🔴 THE TWO REFERENCES DISAGREE on t.tabwide/s.spcwide (vg8020 8, cf3300 6) and
# zerobas matches the CF-3300. A column past the line WRAPS, so the answer is a
# function of the machine's boot WIDTH -- a configuration difference, not TAB or
# SPC semantics. These rows pin the width FIRST, which is what turns a
# references-disagree row into a scorable one.
# [[no-oracle-is-about-the-comparison]]
add('w.tabw39', ['WIDTH 39:PRINT TAB(45);'+':X=POS(0)'], 'X')
add('w.spcw39', ['WIDTH 39:PRINT SPC(45);'+':X=POS(0)'], 'X')
add('w.tabw32', ['WIDTH 32:PRINT TAB(45);'+':X=POS(0)'], 'X')
# 🟢 CONTROL: same explicit width, IN-RANGE column -- must agree everywhere, and
# says the WIDTH statement itself is not the variable.
add('w.ctl39', ['WIDTH 39:PRINT TAB(10);'+':X=POS(0)'], 'X')

# --- SPC(): relative -------------------------------------------------------
add('s.spc', ['PRINT SPC(5);'+':X=POS(0)'], 'X')
add('s.spc0', ['PRINT SPC(0);'+':X=POS(0)'], 'X')
add('s.spcwide', ['PRINT SPC(45);'+':X=POS(0)'], 'X')

# --- numeric formatting: the leading/trailing space rule -------------------
add('n.pos', ['PRINT 1;'+':X=POS(0)'], 'X')
add('n.neg', ['PRINT -1;'+':X=POS(0)'], 'X')
add('n.zero', ['PRINT 0;'+':X=POS(0)'], 'X')
add('n.float', ['PRINT 1.5;'+':X=POS(0)'], 'X')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>16}" for s in sides) + "   verdict")
diff = []
for l in ORDER:
    vals = [str(res[s].get(l)) for s in sides]
    same = len(set(vals)) == 1
    if not same: diff.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{v:>16}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF: {len(diff)}/{len(ORDER)}  " + " ".join(diff))
