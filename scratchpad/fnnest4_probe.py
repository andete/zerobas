#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FNNEST — the confirmed ceiling, with a control for the READOUT itself.

\U0001f534 TWO READINGS WITHDRAWN BEFORE THIS RUN, BOTH MINE, BOTH FROM THE SAME
DEFECT -- and the defect was in the probe, not the ROM.

`scratchpad/fnnest2_probe.py` scored a case by searching the WHOLE flat screen
dump for "Out of memory" before it looked at anything else. In BATCH mode the
screen is not cleared between cases, so that search finds the PREVIOUS case's
error text and reports it as this case's answer. It made a flat 12-call
expression look like a failure (it is not: `scratchpad/fnnest3_probe.py`, and
again `a.alone` here), which in turn made me read the ceiling as call COUNT
rather than nesting depth, and then made me suspect an ERR 7 surviving `NEW` --
`scratchpad/fnleak_probe.py` put that on the machine as an A/B and it is FALSE,
all three arms answer 12. [[readout-blind-to-its-own-subject]]

\U0001f3af SO THE READOUT IS ANCHORED, AND THE ANCHOR HAS ITS OWN ROW. Every
verdict is taken from the rows AFTER the last `RUN`, and `n10r` re-runs a
PASSING depth immediately after a failing one: it must read `1`, with the
previous case's `Out of memory` still on the glass. A readout that cannot pass
that row cannot be trusted on the rows that matter.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                              # noqa: E402
import probe_sides                                            # noqa: E402


def nested(n):
    return ['10 A$="X"', '20 DEF FNB$(X$)=X$',
            "30 PRINT LEN(" + "FNB$(" * n + "A$" + ")" * n + ")", "RUN"]


CASES = ([(f"n{n:02d}", nested(n)) for n in (8, 9, 10, 11, 12, 36)]
         + [("n10r", nested(10))])       # ← the READOUT's own control


def last_result(cap):
    c = cap or ""
    if not c:
        return "<NO DUMP>"
    rows = [c[j:j + 40].strip() for j in range(0, len(c), 40)]
    run = [k for k, r in enumerate(rows) if r.endswith("RUN")]
    if not run:
        return "<no RUN row>"
    after = [r for r in rows[run[-1] + 1:]
             if r and r != "Ok" and "color" not in r]
    return after[0] if after else "<nothing after RUN>"


def main() -> int:
    SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
    out = {}
    for name, m in SIDES.items():
        out[name] = omsx_repl.run_cases(m["machine"], CASES, batch=True,
                                        boot=m["boot"], reset=m["reset"])
    got = {s: [last_result(out[s][i]) for i in range(len(CASES))]
           for s in SIDES}

    print("D-FNNEST: nested FN depth, anchored readout "
          "(n10r = the readout's control)\n")
    for i, (nm, _) in enumerate(CASES):
        cells = "  ".join(f"{s}=[{got[s][i]:22}]" for s in SIDES)
        print(f"  {nm:6} {cells}")

    ctl = len(CASES) - 1
    print()
    if any(got[s][ctl] != "1" for s in SIDES):
        print("\U0001f534 THE READOUT'S OWN CONTROL FAILED -- n10r must read 1 on "
              "every side with the previous case's error still on screen. "
              "Every row above is UNADJUDICATED; fix the readout first.")
        return 2
    print("✅ readout control passes: n10r reads 1 on all three sides with "
          "an `Out of memory` from n12 still on the glass.")
    bad = [nm for i, (nm, _) in enumerate(CASES)
           if got["zb"][i] != got["vg8020"][i]
           or got["zb"][i] != got["cf3300"][i]]
    print(f"\n=== {len(bad)} row(s) where zerobas differs from BOTH "
          f"references: {bad or 'none'} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
