#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FNNEST — what quantity actually caps `FN` calls, measured three ways.

\U0001f534 MY FIRST READING WAS REFUTED BY MY OWN CONTROL. `fn_enter` saves the
live shadow-parameter area on the Z80 stack, so I read the ceiling as NESTING
DEPTH and predicted that a flat chain of the same call count would pass. It does
not: `s12` -- twelve calls at depth 1 -- is `Out of memory` too, while both
references print 12. Whatever is exhausted is not the nesting stack.

THREE LADDERS, so the answer names a quantity instead of a symptom:

  n..  nested       depth n, n calls        (measured ceiling 10)
  s..  sequential   depth 1, n calls in ONE expression
  L..  looped       depth 1, n calls in n SEPARATE statements

If `s` gives out at the same count as `n`, the quantity is CALLS PER EXPRESSION
and depth is irrelevant. If `L` also gives out, nothing is released per
statement either and the quantity is calls per RUN -- a leak, not a ceiling. A
`L` that survives 200 calls says the release happens at end-of-statement and
puts the fault inside one expression's lifetime.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                              # noqa: E402
import probe_sides                                            # noqa: E402


def prog(line):
    return ['10 A$="X"', '20 DEF FNB$(X$)=X$', line, "RUN"]


CASES = [(f"s{n:02d}", prog("30 PRINT " + "+".join(["LEN(FNB$(A$))"] * n)))
         for n in (8, 9, 10, 11, 12)]
CASES += [("L200", prog("30 FOR I=1 TO 200:A=LEN(FNB$(A$)):NEXT:PRINT A")),
          ("num10", ['10 DEF FNC(X)=X+1',
                     "20 PRINT " + "+".join(["FNC(1)"] * 10), "RUN"]),
          ("num12", ['10 DEF FNC(X)=X+1',
                     "20 PRINT " + "+".join(["FNC(1)"] * 12), "RUN"])]


def main() -> int:
    SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
    out = {}
    for name, m in SIDES.items():
        out[name] = omsx_repl.run_cases(m["machine"], CASES, batch=True,
                                        boot=m["boot"], reset=m["reset"])

    def verdict(cap):
        c = (cap or "<NO DUMP>")
        for probe in ("Out of memory", "String formula", "Overflow",
                      "Illegal function call", "Type mismatch", "Syntax error"):
            if probe in c:
                return probe
        rows = [c[j:j + 40].strip() for j in range(0, len(c), 40)]
        run = [k for k, r in enumerate(rows) if r.endswith("RUN")]
        if run:
            after = [r for r in rows[run[-1] + 1:] if r and r != "Ok"
                     and "color" not in r]
            return (after[0] if after else "<nothing after RUN>")
        return "<no RUN row>"

    print("D-FNNEST: s.. sequential-in-one-expression, "
          "L.. one call per statement, num.. numeric FN\n")
    for i, (nm, _) in enumerate(CASES):
        cells = "  ".join(f"{s}=[{verdict(out[s][i]):22}]" for s in SIDES)
        print(f"  {nm:7} {cells}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
