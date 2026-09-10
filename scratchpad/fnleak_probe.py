#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FNLEAK — does a program that died of ERR 7 poison the NEXT program?

\U0001f534 THE OBSERVATION THAT FORCED THIS, AND IT IS A DISAGREEMENT BETWEEN TWO
OF MY OWN RUNS. The identical 12-call flat expression

    10 A$="X" : 20 DEF FNB$(X$)=X$ : 30 PRINT LEN(FNB$(A$))+...  (12 terms)

answered `Out of memory` in `scratchpad/fnnest2_probe.py`, where the cases
before it were nested depths 11 and 12 that BOTH died of ERR 7, and answered
`12` in `scratchpad/fnnest3_probe.py`, where every case before it passed. Same
typed program, same machine, same emulator -- so the variable is what ran
BEFORE, across the harness's `NEW`.

⚠️ THAT IS A READING, NOT YET A FACT, and inferring the mechanism from the one
coincidence is exactly the failure this tree keeps catching
[[a-mechanism-inferred-from-one-observation]]. So it is put on the machine as an
A/B with everything else held identical:

    a.alone        the 12-call program, nothing before it
    b.after_fail   a depth-12 program that dies of ERR 7, then NEW, then the
                   SAME 12-call program, in ONE case so no harness reset
                   intervenes
    c.after_ok     a depth-4 program that SUCCEEDS, then NEW, then the same --
                   the control that separates "a previous program" from "a
                   previous FAILED program"

If b diverges from a and c agrees with a, the poison is the ERR 7 and `NEW` does
not clear it. If b and c both diverge, the fault is plain carry-over and has
nothing to do with the error.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                              # noqa: E402
import probe_sides                                            # noqa: E402

SEQ12 = "30 PRINT " + "+".join(["LEN(FNB$(A$))"] * 12)


def victim():
    return ['10 A$="X"', '20 DEF FNB$(X$)=X$', SEQ12, "RUN"]


def nested(n):
    return ['10 A$="X"', '20 DEF FNB$(X$)=X$',
            "30 PRINT LEN(" + "FNB$(" * n + "A$" + ")" * n + ")", "RUN"]


CASES = [
    ("a.alone", victim()),
    ("b.after_fail", nested(12) + ["NEW"] + victim()),
    ("c.after_ok", nested(4) + ["NEW"] + victim()),
]


def main() -> int:
    SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
    out = {}
    for name, m in SIDES.items():
        out[name] = omsx_repl.run_cases(m["machine"], CASES, batch=True,
                                        boot=m["boot"], reset=m["reset"])

    def last_result(cap):
        """The first non-empty, non-Ok row after the LAST `RUN` row.

        \\u26a0\\ufe0f The capture is a flat 40-column dump with NO newlines, so
        this splits on the column width rather than matching line anchors
        (D-RUNLINE2 got that wrong twice).
        """
        c = (cap or "")
        if not c:
            return "<NO DUMP>"
        rows = [c[j:j + 40].strip() for j in range(0, len(c), 40)]
        run = [k for k, r in enumerate(rows) if r.endswith("RUN")]
        if not run:
            return "<no RUN row>"
        after = [r for r in rows[run[-1] + 1:]
                 if r and r != "Ok" and "color" not in r]
        return after[0] if after else "<nothing after RUN>"

    print("D-FNLEAK: does an ERR 7 survive NEW and poison the next program?\n")
    for i, (nm, _) in enumerate(CASES):
        cells = "  ".join(f"{s}=[{last_result(out[s][i]):22}]" for s in SIDES)
        print(f"  {nm:13} {cells}")
    zb = [last_result(out["zb"][i]) for i in range(len(CASES))]
    print()
    if zb[0] == zb[2] and zb[1] != zb[0]:
        print(f"\U0001f3af MEASURED: the ERR 7 is the variable. Alone and after a "
              f"SUCCESSFUL program the answer is {zb[0]!r}; after a program that "
              f"died of ERR 7 it is {zb[1]!r}, across a NEW.")
    elif zb[0] == zb[1] == zb[2]:
        print("\U0001f534 NO CARRY-OVER: all three agree, so the fnnest2/fnnest3 "
              "disagreement has a DIFFERENT cause and the reading is withdrawn.")
    else:
        print(f"⚠️ NEITHER SHAPE: {zb} -- read the rows, do not "
              "summarise them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
