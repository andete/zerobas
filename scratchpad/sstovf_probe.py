#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-SSTOVF — can a BASIC program reach `sst_overflow` at all?

D-DUPOBS2 (2026-09-10) scored all 21 D-DUPSPAN2 canonicals against the emulator
tier and found FOUR that no behavioural gate reaches. `sst_overflow`
(`basic/str-engine.asm`, aliased by `shxf_overflow`) is the cheapest of them to
attack because it needs no fixture: it fires when a SNAPSHOT into the
temp-descriptor stack finds the stack full (`SH_ERR=2` from
`sh_temp_push_alloc`, `sub/strheap.asm`), and the stack is `TEMPD = 32` slots
deep (`basic/sysvars.inc`).

\U0001f3af THE LEVER IS `DEF FN` WITH A STRING ARGUMENT, because it is the
CHEAPEST TEXT PER TEMP in the language. Every construct that snapshots costs
8-11 characters a level (`MID$(x,1)` and friends) against a 255-character line,
which tops out around 23 temps -- below the 32 the stack holds. `FNB$(` + `)` is
SIX, so 35 nested calls fit in one line with room to spare, and `deffn.asm:344`
snapshots the argument on every call.

⚠️ THIS IS A SURVEY, NOT A GATE. It asks the two references and zerobas the
same ramp and prints what each says. The question it answers is "what is the
depth at which each machine gives up, and does it give up the same WAY" -- the
row set comes after, from the answer.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                              # noqa: E402
import probe_sides                                            # noqa: E402

DEPTHS = [1, 4, 16, 24, 28, 30, 31, 32, 33, 36]


# \U0001f534 `DEF FN` MUST BE IN A PROGRAM, AND THE FIRST CUT OF THIS PROBE PUT IT
# IN DIRECT MODE -- where all three machines answered `Undefined user function`
# for a reason that has nothing to do with the temp stack: the definition's TEXT
# lives in the direct-mode line buffer, which the very next line overwrites. An
# apparatus that fails identically on every side still measures nothing.
def case(n: int):
    expr = "FNB$(" * n + "A$" + ")" * n
    line = "30 PRINT LEN(" + expr + ")"
    return [
        '10 A$="X"',
        '20 DEF FNB$(X$)=X$',
        line,
        'RUN',
    ], len(line)


def main() -> int:
    cases = []
    for n in DEPTHS:
        lines, ln = case(n)
        if ln > 250:
            print(f"\U0001f534 depth {n} needs a {ln}-char line -- over the "
                  f"255-char BASIC line limit; the ramp stops here.")
            break
        cases.append((f"n{n:02d}", lines))
    print(f"D-SSTOVF: {len(cases)} depth(s), longest line "
          f"{max(len(c[1][-1]) for c in cases)} chars\n")

    SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
    out = {}
    for name, m in SIDES.items():
        out[name] = omsx_repl.run_cases(m["machine"], cases, batch=True,
                                        boot=m["boot"], reset=m["reset"])

    for i, (nm, lines) in enumerate(cases):
        print(f"  {nm:5}")
        for s in SIDES:
            # \u26a0\ufe0f THE CAPTURE IS A FLAT 40-COLUMN SCREEN DUMP WITH NO
            # NEWLINES -- a line-anchored regex reads nothing here (D-RUNLINE2
            # got this wrong twice). Print the raw tail and read it.
            cap = (out[s][i] or "<NO DUMP>")
            rows = [cap[j:j + 40].rstrip()
                    for j in range(0, len(cap), 40)]
            rows = [r for r in rows if r.strip()
                    and "color" not in r and "auto" not in r]
            print(f"       {s:7} |" + " / ".join(rows[-4:]) + "|")
    return 0


if __name__ == "__main__":
    sys.exit(main())
