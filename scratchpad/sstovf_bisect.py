#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FNNEST — where does nested `DEF FN` give out, and is the pool the reason?

`scratchpad/sstovf_probe.py` went looking for `sst_overflow` (one of the four
D-DUPOBS2 sites no gate reaches) and found something else on the way: at nesting
depth 16 zerobas answers `Out of memory in 30` while BOTH references print `1`,
and they still print `1` at depth 36. That is a live wrong answer, not an
apparatus artefact -- the identical typed program runs on all three sides.

TWO QUESTIONS, and the second is the one that says what to fix:

  1. WHERE is the boundary? The first probe only bracketed it as 4 < n <= 16.
  2. IS IT THE CONTROL-FRAME POOL? D-CTLPOOL made GOSUB depth linear in `CLEAR`
     by moving frames into a pool at STKTOP. If a `DEF FN` call takes a frame
     from that pool, `CLEAR 1000` raises the ceiling and the answer is a pool
     SIZE; if the ceiling does not move, the frames are somewhere else and a
     size fix would have been the wrong fix.

⚠️ A CLEAR THAT CHANGES NOTHING IS AS MUCH OF A RESULT AS ONE THAT DOES -- it
is the arm that separates "the pool is too small" from "these frames are not in
the pool at all" [[two-rules-that-coincide-on-every-row-you-have]].
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                              # noqa: E402
import probe_sides                                            # noqa: E402

DEPTHS = [5, 6, 7, 8, 10, 12, 14, 15, 16]
CLEARED = [16, 24, 36]          # same depths, but with a big CLEAR first


def prog(n: int, clear: int | None):
    expr = "FNB$(" * n + "A$" + ")" * n
    lines = []
    if clear is not None:
        lines.append(f"5 CLEAR {clear}")
    lines += ['10 A$="X"', '20 DEF FNB$(X$)=X$',
              "30 PRINT LEN(" + expr + ")", "RUN"]
    return lines


def main() -> int:
    cases = [(f"n{n:02d}", prog(n, None)) for n in DEPTHS]
    cases += [(f"c{n:02d}", prog(n, 2000)) for n in CLEARED]
    SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
    out = {}
    for name, m in SIDES.items():
        out[name] = omsx_repl.run_cases(m["machine"], cases, batch=True,
                                        boot=m["boot"], reset=m["reset"])

    def verdict(cap):
        c = (cap or "<NO DUMP>")
        if "Out of memory" in c:
            return "Out of memory"
        if "String formula" in c:
            return "String formula too complex"
        rows = [c[j:j + 40].strip() for j in range(0, len(c), 40)]
        run = [k for k, r in enumerate(rows) if r.endswith("RUN")]
        if run:
            after = [r for r in rows[run[-1] + 1:] if r and r != "Ok"]
            return (after[0] if after else "<nothing after RUN>")
        return "<no RUN row>"

    print(f"D-FNNEST: {len(cases)} case(s)  "
          f"(n.. = plain, c.. = after CLEAR 2000)\n")
    for i, (nm, _) in enumerate(cases):
        cells = "  ".join(f"{s}=[{verdict(out[s][i]):26}]" for s in SIDES)
        print(f"  {nm:5}  {cells}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
