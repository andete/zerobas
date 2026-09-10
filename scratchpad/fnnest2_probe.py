#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FNNEST — the exact ceiling, and the control that says WHICH quantity caps it.

`scratchpad/sstovf_bisect.py` bracketed zerobas's nested-`DEF FN` ceiling at
10 < n <= 12 with both references fine at 36, and showed `CLEAR 2000` does not
move it -- so it is not the D-CTLPOOL control-frame pool.

`fn_enter` (basic/deffn.asm) saves the LIVE part of the shadow-parameter area on
the Z80 STACK and guards it with `FN_STK_FLOOR`, raising ERR 7. The live part is
every outer frame's slots, so the cost is O(n^2) in NESTING DEPTH and O(1) in
call COUNT.

\U0001f3af THE CONTROL SEPARATES THE TWO. `s12` makes twelve SEQUENTIAL calls in
one expression -- the same number of calls, nesting depth 1. If it passes while
`n12` fails, the cap is depth, which is what the O(n^2) stack save predicts; if
it fails too, the reading is wrong and the quantity is something else
[[two-rules-that-coincide-on-every-row-you-have]].
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
    return "30 PRINT LEN(" + "FNB$(" * n + "A$" + ")" * n + ")"


def sequential(n):
    return "30 PRINT " + "+".join(["LEN(FNB$(A$))"] * n)


def prog(line):
    return ['10 A$="X"', '20 DEF FNB$(X$)=X$', line, "RUN"]


CASES = [("n09", prog(nested(9))),
         ("n10", prog(nested(10))),
         ("n11", prog(nested(11))),
         ("n12", prog(nested(12))),
         ("s12", prog(sequential(12))),
         ("s16", prog(sequential(16))),
         ("b.recurse", ['10 DEF FNA(X)=FNA(X)', '20 PRINT FNA(1)', 'RUN'])]


def main() -> int:
    SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
    out = {}
    for name, m in SIDES.items():
        out[name] = omsx_repl.run_cases(m["machine"], CASES, batch=True,
                                        boot=m["boot"], reset=m["reset"])

    def verdict(cap):
        c = (cap or "<NO DUMP>")
        for probe in ("Out of memory", "String formula", "Overflow",
                      "Illegal function call", "Type mismatch"):
            if probe in c:
                return probe
        rows = [c[j:j + 40].strip() for j in range(0, len(c), 40)]
        run = [k for k, r in enumerate(rows) if r.endswith("RUN")]
        if run:
            after = [r for r in rows[run[-1] + 1:] if r and r != "Ok"]
            return (after[0] if after else "<nothing after RUN>")
        return "<no RUN row>"

    print("D-FNNEST: n.. nested, s.. sequential (same call count, depth 1)\n")
    for i, (nm, _) in enumerate(CASES):
        cells = "  ".join(f"{s}=[{verdict(out[s][i]):22}]" for s in SIDES)
        print(f"  {nm:10} {cells}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
