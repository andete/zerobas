#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARCMASK aside -- how LONG does CIRCLE take, reference vs zerobas?

Measured in the machine's own units: `TIME` is the VDP interrupt counter, so
one tick is one frame (20 ms on a 50 Hz EU machine -- both machines here are
EU, so the units are directly comparable).

⚠️ THE LOOP IS PART OF THE MEASUREMENT. Every row is run as N iterations inside
a FOR loop, and an EMPTY loop of the same N is measured on the same machine and
subtracted -- BASIC's own FOR/NEXT costs real ticks, and on two different ROMs
it costs DIFFERENT ticks. A row reported without that control would be
comparing interpreter overhead as much as CIRCLE.

⚠️ `r_zero` is the DEAD SUBJECT: CIRCLE with r=0 draws one point, so whatever
it costs is the fixed per-call overhead, not the rasteriser.

    python3 -u scratchpad/arcmask_time.py
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

N = 20
CASES = [
    ("loop_only", "", "⭐ CONTROL: the empty FOR/NEXT. Subtracted from every "
                      "row below, per machine."),
    ("r_zero", "CIRCLE(128,96),0,15", "⭐ DEAD SUBJECT: r=0 is one point, so "
                                      "this is the fixed per-call cost."),
    ("r20", "CIRCLE(128,96),20,15", "the gate's own working size"),
    ("r48", "CIRCLE(128,96),48,15", "mid"),
    ("r95", "CIRCLE(128,96),95,15", "the largest fully visible circle"),
    ("r95_arc", "CIRCLE(128,96),95,15,1.1,2.04",
     "the same circle with the ARC MASK on -- every point pays two cross "
     "products. zerobas widened those to 32 bits in D-CIRCOVF."),
    ("r95_ell", "CIRCLE(128,96),95,15,,,.5",
     "the same circle with the minor-axis SCALE on -- every point pays a "
     "multiply. D-CIRCOVF widened that one too."),
    ("r95_arc_ell", "CIRCLE(128,96),95,15,1.1,2.04,.5",
     "both at once: the most expensive path in the tenant."),
    ("r200_off", "CIRCLE(128,352),200,15",
     "r=200 with the centre off screen -- most points are CLIPPED, so this "
     "separates rasterising cost from plotting cost."),
]


def prog(ops):
    body = ["COLOR15,4,7:SCREEN2", "T=TIME"]
    body.append(f"FORI=1TO{N}:{ops}:NEXT" if ops else f"FORI=1TO{N}:NEXT")
    body += ["U=TIME", "SCREEN0:PRINT\"T=\";U-T", "GOTO 60"]
    return body


def ticks(machine, ops):
    out = omsx_repl.run_cases(machine, [("stored", prog(ops))], batch=False,
                              step=12.0)[0]
    m = re.search(r"T=\s*(-?\d+)", out or "")
    return int(m.group(1)) if m else None


def main():
    print("=== D-ARCMASK: CIRCLE cost, reference vs zerobas ===")
    print(f"ref={REF}  zb={ZB}   {N} iterations per row, TIME = VDP frames\n")
    base = {}
    res = []
    for lbl, ops, why in CASES:
        r, z = ticks(REF, ops), ticks(ZB, ops)
        if lbl == "loop_only":
            base = {"ref": r, "zb": z}
            print(f"  {lbl:12} raw ref={r} zb={z}   (subtracted below)")
            print(f"        why: {why}")
            continue
        rn = None if r is None or base["ref"] is None else r - base["ref"]
        zn = None if z is None or base["zb"] is None else z - base["zb"]
        rat = (f"{zn / rn:.2f}x" if rn and zn and rn > 0 else "-")
        res.append((lbl, rn, zn, rat))
        print(f"  {lbl:12} ref={rn!s:>5} zb={zn!s:>5} frames/{N}  "
              f"-> zerobas is {rat} the reference's time")
        print(f"        why: {why}")
    print("\n=== per single call, in milliseconds (50 Hz -> 20 ms/frame) ===")
    print(f"  {'row':12} {'reference':>10} {'zerobas':>10} {'ratio':>7}")
    for lbl, rn, zn, rat in res:
        f = 20.0 / N
        print(f"  {lbl:12} {('%.1f ms' % (rn * f)) if rn is not None else '?':>10}"
              f" {('%.1f ms' % (zn * f)) if zn is not None else '?':>10} {rat:>7}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
