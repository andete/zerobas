#!/usr/bin/env python3
r"""D-INTERPSPEED — is zerobas's interpreter uniformly slower, or is it FOR/NEXT?

Found 2026-09-02 while VALIDATING a different instrument. D-PUTTIME added a
pure-CPU control -- `FOR I=1 TO 2000:NEXT` -- only to prove that `TIME` can see
CPU work at all. It can, and the control was the finding:

    CF-3300   201 jiffies then 200      zerobas   623 then 622      3.1x

Both linear. That is CORE INTERPRETER cost, not disk and not graphics, and the
tree has no item for it -- `PAINT` (1.9-2.0x) and arcs (5-6x, closed) are the
only speed items, both graphics.

🎯 AND IT WOULD REFRAME `PAINT`. If the interpreter baseline is ~3x, then PAINT
at 1.9x is FASTER than the machine it runs on, and its item is measuring the gap
against the wrong zero.

🔴 SO THE CLAIM HAS TO BE NARROWED BEFORE IT IS MADE. One loop, one size, one
construct is not "the interpreter". These rows vary all three:
  * SIZE (1000 / 2000 / 4000) -- a constant offset vs a true ratio. If the ratio
    holds across sizes the cost is per-iteration, not per-statement setup.
  * CONSTRUCT -- FOR/NEXT against a GOTO loop (no FOR machinery at all), an
    empty FOR, and a FOR whose body does arithmetic. If only FOR/NEXT is slow
    the finding is `ex_for`/`ex_next`; if everything is, it is dispatch.
  * a STRING body, because the string engine is a different subsystem again.

⚠️ EVERY ROW IS PURE CPU -- no disk, no VDP beyond the final PRINT -- so nothing
here depends on the fixture that confused D-PUT3.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_fldwidth as F                                  # noqa: E402

STEP = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
for s in ("zb", "cf3300", "vg8020"):
    F.SIDES[s] = dict(F.SIDES[s], step=STEP)

def t(body):
    return ['TIME=0', body, 'PRINT"[";TIME;"]"']

CASES = [
    # --- SIZE: is it a ratio or an offset? ----------------------------------
    ("s.for1k",  "run", t('FOR I=1 TO 1000:NEXT')),
    ("s.for2k",  "run", t('FOR I=1 TO 2000:NEXT')),
    ("s.for4k",  "run", t('FOR I=1 TO 4000:NEXT')),
    # --- CONSTRUCT: FOR/NEXT vs a loop with no FOR machinery at all ---------
    # 🔴 MY OWN BUG, KEPT WITH ITS FIX. The first cut said `THEN 20`, and the
    # harness numbers body lines 10,20,30... -- so 20 is `I=0` and the loop
    # reset its own counter forever. The CF-3300 row read
    # `<UNREADABLE: |||...color auto goto list r>` (the function-key row, i.e.
    # a machine sitting at the prompt after a runaway) and zb read blank. Worth
    # noting that the `<UNREADABLE:` fallback added earlier the same day is what
    # made it diagnosable at a glance instead of another anonymous blank.
    ("c.goto2k", "run", ['TIME=0', 'I=0', 'I=I+1:IF I<2000 THEN 30',
                         'PRINT"[";TIME;"]"']),
    ("c.while",  "run", t('I=0:FOR J=1 TO 2000:I=I+1:NEXT')),
    ("c.arith",  "run", t('FOR I=1 TO 2000:X=I*2+1:NEXT')),
    ("c.str",    "run", t('FOR I=1 TO 500:A$="AB"+"CD":NEXT')),
    # --- 🟢 CONTROL: no loop at all. Whatever this costs is the floor, and if
    # --- it is not ~0 on both machines the timing fixture itself is suspect.
    ("z.none",   "run", t('X=1')),
]

F.CASES = CASES
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
res = {s: F.run_side(s, []) for s in sides}
w = max(len(l) for l, _, _ in CASES)
print(f"\nstep={STEP}s   JIFFIES (60 Hz) for the whole construct")
print(f"{'row':<{w}}  " + "  ".join(f"{s:>14}" for s in sides) + "   ratio zb/cf")
for label, _, _ in CASES:
    vals = [str(res[s].get(label)) for s in sides]
    r = ""
    try:
        a = float(res["cf3300"][label]); b = float(res["zb"][label])
        r = f"{b/a:.2f}x" if a else "-"
    except Exception:
        r = "-"
    print(f"{label:<{w}}  " + "  ".join(f"{v:>14}" for v in vals) + f"   {r}")
