#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARCMASK aside, round 2 -- the three rows round 1 could not read.

Round 1 (arcmask_time.py, N=20, step=12 s) returned NO `T=` for
`r95_arc`/`r95_arc_ell` on zerobas and for `r200_off` on the reference. That is
a RIG FAILURE, not a reading, and it is reported as one rather than as "zerobas
is unmeasurably slow": at N=20 a row that takes over ~0.6 s per call simply
does not finish inside the capture window.

⚠️ THE FAILURE IS INFORMATIVE ABOUT WHERE TO LOOK, NOT ABOUT THE ANSWER. The
rows that failed are exactly the arc rows on the machine whose cross product
D-CIRCOVF widened to 32 bits, so N drops to 5 and the window triples. The
empty-loop control is re-measured at the SAME N -- a control taken at a
different N is not a control.

    python3 -u scratchpad/arcmask_time2.py
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, HERE)

import omsx_repl                                        # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                    "C-BIOS_MSX1_EU_REPACK_DISK")

N = 5
CASES = [
    ("loop_only", ""),
    ("r95", "CIRCLE(128,96),95,15"),
    ("r95_arc", "CIRCLE(128,96),95,15,1.1,2.04"),
    ("r95_arc_ell", "CIRCLE(128,96),95,15,1.1,2.04,.5"),
    ("r200_off", "CIRCLE(128,352),200,15"),
    ("r200_off_arc", "CIRCLE(128,352),200,15,1.1,2.04"),
]


def prog(ops):
    body = ["COLOR15,4,7:SCREEN2", "T=TIME"]
    body.append(f"FORI=1TO{N}:{ops}:NEXT" if ops else f"FORI=1TO{N}:NEXT")
    body += ["U=TIME", "SCREEN0:PRINT\"T=\";U-T", "GOTO 60"]
    return body


def ticks(machine, ops):
    out = omsx_repl.run_cases(machine, [("stored", prog(ops))], batch=False,
                              step=45.0)[0]
    m = re.search(r"T=\s*(-?\d+)", out or "")
    return int(m.group(1)) if m else None


def main():
    print("=== D-ARCMASK: CIRCLE cost, round 2 ===")
    print(f"ref={REF}  zb={ZB}   N={N}, step=45 s, TIME = VDP frames\n")
    base = {}
    print(f"  {'row':14} {'reference':>11} {'zerobas':>11} {'zb/ref':>8}")
    for lbl, ops in CASES:
        r, z = ticks(REF, ops), ticks(ZB, ops)
        if lbl == "loop_only":
            base = {"ref": r, "zb": z}
            print(f"  {lbl:14} {r!s:>11} {z!s:>11}   (control, subtracted)")
            continue
        rn = None if r is None or base["ref"] is None else r - base["ref"]
        zn = None if z is None or base["zb"] is None else z - base["zb"]
        rat = f"{zn / rn:.2f}x" if rn and zn and rn > 0 else "?"
        f = 20.0 / N
        print(f"  {lbl:14} "
              f"{('%.0f ms' % (rn * f)) if rn is not None else 'NOREAD':>11} "
              f"{('%.0f ms' % (zn * f)) if zn is not None else 'NOREAD':>11} "
              f"{rat:>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
