#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-NMFAIL control — IS THE DRIVE ACTUALLY EMPTY?

`scratchpad/nmfail_probe.py` reports that with `diska=None` the CF-3300 answers
ERR 70 to NAME/KILL/FILES/LOAD/SAVE while zerobas answers NO ERROR to all five.
A silent success for `NAME "A.BAS" AS "B.BAS"` on an empty drive is not a
plausible bug shape -- it is the shape of an APPARATUS that still has a disk in
it. The row set is worthless until that is excluded, so this asks the machine
what it can see rather than assuming the mount followed the parameter
[[apparatus-is-part-of-the-measurement]].

Raw screen, no fence, no scoring: read it.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                              # noqa: E402
import probe_sides                                            # noqa: E402

CASES = [("look", ["10 CLS", "20 FILES", '30 PRINT"<<END>>"', "RUN"])]


def main() -> int:
    SIDES = probe_sides.sides("cf3300", "zb")
    for name, m in SIDES.items():
        caps = omsx_repl.run_cases(m["machine"], CASES, batch=True,
                                   boot=m["boot"], reset=m["reset"],
                                   diska=probe_sides.diska(name, None))
        c = caps[0] or "<NO DUMP>"
        rows = [c[k:k + 40].rstrip() for k in range(0, len(c), 40)]
        print(f"=== {name} ({m['machine']}), diska="
              f"{probe_sides.diska(name, None)!r}")
        for r in rows:
            if r.strip():
                print(f"    |{r}|")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
