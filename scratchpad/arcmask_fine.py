#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARCMASK step 5 -- resolve the reference's angle quantiser.

arcmask_rays.py established, from 34 bracketed rays on 19 measured rows:

  * the reference's kept set is an angular WEDGE on every row (checked, not
    assumed -- a non-contiguous kept set is reported as such);
  * zerobas's rays land within a QTAB step of the true angle, as designed;
  * the REFERENCE's rays are off by up to 0.05 rad -- 4.5 px at r=95, 10 px at
    r=200 -- and the error is a function of `theta mod pi/2` alone: the same
    error recurs at 1.1 in two different rows and at the matching offset in
    all four quadrants. It is a QUANTISER, not a bias: it jumps.

Five closed forms were searched against all 22 r=95 rays and all five are
REFUTED -- angle-to-N-steps-per-turn, slope-to-1/N, components-to-1/N, and
rounded/truncated/floored (m*cos, m*sin) for every m up to 800. Best partial
was 7 of 22. So stop fitting and SAMPLE the quantiser directly.

r=190 centred at (128,280) puts the visible band at |dy| in 89..190, i.e.
theta in [0.487, 2.654] -- which mod pi/2 covers the WHOLE period -- and its
adjacent-point spacing is 1/190 = 0.0053 rad, half the r=95 bracket. 30 rows x
2 rays each = 60 samples at 0.035 rad spacing across one full period.

⚠️ Same rig guards as step 3: dead subject first, byte-identical controls, and
an EXACT zerobas prediction on every row (the model is 23/23 on whole planes).

    python3 -u scratchpad/arcmask_fine.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, HERE)

import omsx_repl                                        # noqa: E402
import arcmask_model as M                               # noqa: E402
from circovf_calib import plane, reduce_plane           # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                    "C-BIOS_MSX1_EU_REPACK_DISK")
LINIT = "COLOR15,4,7:SCREEN2"
PLANE = [(0, 6144)]
OUT = os.path.join(HERE, "arcmask_fine.json")

CY, R = 280, 190

CASES = [
    ("dead_nocircle", "PSET(10,10),15", None,
     "⭐ DEAD SUBJECT, FIRST -- no CIRCLE in the program at all."),
    (f"ctl_full_r{R}", f"CIRCLE(128,{CY}),{R},15", dict(cx=128, cy=CY, r=R),
     "GREEN CONTROL: the same clipped circle with the mask disabled."),
    ("ctl_rep_r190", f"CIRCLE(128,{CY}),{R},15,1.1,2.04",
     dict(cx=128, cy=CY, r=R, start=1.1, end=2.04),
     "REPLICATION of lad_r190 from the step-3 sweep (ref 162 px c9b8628a). A "
     "second reading of a row already measured, in a different batch."),
]

# 30 fine rows; each carries TWO rays 1.05 rad apart, both inside the visible
# band, so 60 samples land across one full pi/2 period of the quantiser.
ANGLES = []
for _i in range(30):
    _a = round(0.50 + 0.035 * _i, 3)
    _b = round(_a + 1.05, 3)
    ANGLES.append((_a, _b))
    CASES.append((f"fn_{_a}", f"CIRCLE(128,{CY}),{R},15,{_a},{_b}",
                  dict(cx=128, cy=CY, r=R, start=_a, end=_b),
                  f"fine sweep: rays at {_a} and {_b} rad"))

# two radius cross-checks: the error is claimed to be ANGULAR (r-independent).
for _r, _cy in ((95, 96), (140, 200)):
    CASES.append((f"rchk_r{_r}", f"CIRCLE(128,{_cy}),{_r},15,0.85,1.9",
                  dict(cx=128, cy=_cy, r=_r, start=0.85, end=1.9),
                  f"r cross-check at r={_r}: same two angles as the fine row "
                  f"fn_0.85, so the ray must land at the same ANGLE if the "
                  f"quantiser is angular"))
CASES.append(("rchk_r190", f"CIRCLE(128,{CY}),{R},15,0.85,1.9",
              dict(cx=128, cy=CY, r=R, start=0.85, end=1.9),
              "the r=190 partner of the two cross-check rows above"))


def prog(stmts):
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


def run(machine, ops):
    # ⚠️ THE FIRST TUPLE ELEMENT IS THE DELIVERY MODE, NOT A LABEL.
    specs = [("stored", prog([LINIT, ops]))]
    return omsx_repl.run_cases(machine, specs, batch=False,
                               capture=("vram_segs", PLANE), step=12.0)[0]


def reduce_hex(hexs):
    if not hexs:
        return None
    b = bytes.fromhex(hexs)
    if len(b) != 6144:
        return ("SHORT", len(b), None)
    return reduce_plane(b)


def main():
    print("=== D-ARCMASK: fine angle sweep, r=190 ===")
    print(f"ref={REF}  zb={ZB}   rows={len(CASES)}\n")
    pred = {}
    for lbl, ops, kw, why in CASES:
        pred[lbl] = None if kw is None else reduce_plane(plane(M.draw(**kw)))
    blank = [l for l, p in pred.items() if p and p[0] == 0]
    print(f"blank-on-both (VACUOUS) rows predicted: {blank or 'none'}")
    if "--dry" in sys.argv:
        for lbl, ops, kw, why in CASES:
            print(f"  {lbl:14} {ops:36} {pred[lbl]}")
        return 0

    out, zmiss, diff = {}, 0, 0
    for lbl, ops, kw, why in CASES:
        rh, zh = run(REF, ops), run(ZB, ops)
        rr, zz = reduce_hex(rh), reduce_hex(zh)
        out[lbl] = dict(ops=ops, ref=rh, zb=zh)
        flag = ""
        if kw is not None and zz != pred[lbl]:
            zmiss += 1
            flag = "  🔴 ZEROBAS MISS -- RIG SUSPECT"
        v = "agree" if rr == zz else "DIFF "
        diff += v == "DIFF "
        print(f"  {v} {lbl:14} {ops}{flag}")
        print(f"        ref = {rr}    zb = {zz}")
    with open(OUT, "w") as f:
        json.dump(out, f)
    print(f"\n=== {diff} DIFF / {len(CASES)} rows;  zerobas misses: {zmiss} ===")
    print(f"=== planes dumped to {OUT} ===")
    return 1 if zmiss else 0


if __name__ == "__main__":
    sys.exit(main())
