#!/usr/bin/env python3
r"""Closing demo — the PRINT USING format specifiers, as MSX BASIC a user types.

The six lines are the program from the session summary, run on the Philips
VG-8020, the National CF-3300, and BOTH zerobas builds (with and without the
disk ROM). PRINT USING is not disk-related, so the two zerobas columns must
agree with each other as well as with the references.

🔴 BRACKETING THE OUTPUT IS NOT ENOUGH, AND THE FIRST CUT OF THIS DEMO GOT IT
WRONG. These fields are right-justified and their LEADING SPACES are the answer
-- ` 1.50` and `1.50` are different results -- but the shared harness normalises
a capture with `" ".join(m.group(1).split())`, which strips exactly that. The
readout printed a clean four-way SAME while being blind to the property it
existed to show.

So each row also carries `POS(0)`, the cursor column after the field, INSIDE the
same bracket pair: a NUMBER, which survives whitespace collapsing. Matching text
AND matching width together pin the leading spaces that neither does alone.

The `before` column is what zerobas printed before this arc (d78c421..41b2727);
it is quoted from the recorded probe runs, not re-measured here, and is labelled
as such.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

# the diskless build is an official target, so the demo runs on it too
D.SIDES["zb-nodisk"] = dict(machine="C-BIOS_MSX1_EU_REPACK_NODISK", boot=8.0,
                            reset=("NEW",))

PROG = [
    ("10  ##.##      1.5",     '"##.##";1.5'),
    ("20  #,###      1234",    '"#,###";1234'),
    ("30  ##.##^^^^  1.5",     '"##.##^^^^";1.5'),
    ("40  .##        .5",      '".##";.5'),
    ("50  **##       5",       '"**##";5'),
    ("60  #######    1234567", '"#######";1234567'),
]
ORDER = []
for lab, usg in PROG:
    D.DIRECT[lab] = [f'CLS:PRINT"[";:PRINT USING{usg};:PRINT"|";POS(0);"]"']
    ORDER.append(lab)

BEFORE = {
    "10  ##.##      1.5":     "[ 1]        no decimal specifier at all",
    "20  #,###      1234":    "[%1234,]    the `,` was a literal, and it overflowed",
    "30  ##.##^^^^  1.5":     "[ 1.50^^^^] the carets were literal",
    "40  .##        .5":      "[. 1]       a literal `.` then a separate ## field",
    "50  **##       5":       "[** 5]      the `**` was literal, no fill",
    "60  #######    1234567": "[      0]   SILENTLY WRONG: no float renderer",
}

sides = ["vg8020", "cf3300", "zb", "zb-nodisk"]
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"\n{'PRINT USING':<{w}}  " + "  ".join(f"{s:>14}" for s in sides)
      + "   verdict        (text | column after the field)")
bad = 0
for l in ORDER:
    vals = [str(res[s].get(l)) for s in sides]
    same = len(set(vals)) == 1
    bad += not same
    print(f"{l:<{w}}  " + "  ".join(f"{v:>12}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\n{len(ORDER) - bad}/{len(ORDER)} rows identical across all four machines")
print("\nzerobas BEFORE this arc (quoted from the recorded pre-fix runs):")
for l in ORDER:
    print(f"  {l:<{w}}  {BEFORE[l]}")
print("done")
