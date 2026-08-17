#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARCMASK step 9 -- THE ORACLE, after the fix.

Every row here was measured RED (zerobas != VG-8020) before the rewrite, plus
the controls that were green and must stay green. Predictions are written by
the pair-compare model (the same arithmetic the asm implements, verified 53/54
before any asm existed) for BOTH machines -- so a zerobas MISS is a rig or
implementation fault and says which row, not just "differs".

Predicted still-DIFF: arc_big_r400 -- the spoke LINE at an off-screen endpoint,
the one open row (the arc part matches; filed separately).

    python3 -u scratchpad/arcmask_verify.py
"""
from __future__ import annotations

import math
import os
import sys
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, HERE)

import omsx_repl                                        # noqa: E402
import arcmask_model as AM                              # noqa: E402
import arcmask_asmsim2 as A                             # noqa: E402
from circovf_calib import W, H, octant, plane, reduce_plane  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                    "C-BIOS_MSX1_EU_REPACK_DISK")
LINIT = "COLOR15,4,7:SCREEN2"
PLANE = [(0, 6144)]

C15 = Decimal("1.27323954473516")


def fp15(d):
    if d == 0:
        return Decimal(0)
    return d.quantize(Decimal(1).scaleb(d.adjusted() - 14), rounding=ROUND_DOWN)


def marshal15(theta):
    q = fp15(A.bcd6(theta) * C15)
    o = int(q)
    return o, int(fp15((q - o) * 16384))


def draw_pair(cx, cy, r, asps=256, aspmaj=0, start=None, end=None,
              sneg=False, eneg=False):
    """The implemented rule: pair-compare wedge + octant-point spokes."""
    arcf = start is not None or end is not None
    if arcf:
        M = A.mmax_asm(r)
        osr, us = marshal15(abs(start or 0.0))
        oer, ue = marshal15(abs(end or 0.0))
        S, E = ((osr & 7), (us * M) >> 14), ((oer & 7), (ue * M) >> 14)
        fullw = S == E and (osr, us) != (oer, ue)
        wrap = S > E

        def keep(o, pos):
            if M:
                if pos >= M:
                    o, pos = (o + 1) & 7, pos - M
                if pos < 0:
                    o, pos = (o - 1) & 7, pos + M
            P = (o & 7, pos)
            if fullw:
                return True
            if not wrap:
                return S <= P <= E
            return P >= S or P <= E
    px = set()
    for qx, qy in octant(r):
        for (sx, sy), o, par in A.mirror8(qx, qy):
            if arcf:
                pos = qx if par == 0 else M - qx
                if not keep(o, pos):
                    continue
            if aspmaj:
                sx = AM.circ_scale(sx, asps)
            else:
                sy = AM.circ_scale(sy, asps)
            x, y = cx + sx, cy + sy
            if 0 <= x < W and 0 <= y < H:
                px.add((x, y))
    if arcf:
        for want, (o, p) in ((sneg, S), (eneg, E)):
            if not want or M == 0:
                continue
            k = p if o % 2 == 0 else M - p
            qq = A.octant_pt(k, r)
            for (vx, vy), oo, par in A.mirror8(*qq):
                if oo == o:
                    break
            if aspmaj:
                vx = AM.circ_scale(vx, asps)
            else:
                vy = AM.circ_scale(vy, asps)
            for x, y in AM.bres_line(cx, cy, cx + vx, cy + vy):
                if 0 <= x < W and 0 <= y < H:
                    px.add((x, y))
    return px


# label, ops, model kwargs, expect ("agree" / "diff-ok")
CASES = [
    ("dead_nocircle", "PSET(10,10),15", None, "agree"),
    ("ctl_full_r95", "CIRCLE(128,96),95,15", dict(cx=128, cy=96, r=95),
     "agree"),
    ("ctl_arc_r15", "CIRCLE(60,60),15,15,0,1.57",
     dict(cx=60, cy=60, r=15, start=0, end=1.57), "agree"),
    ("ctl_card_r95", "CIRCLE(128,96),95,15,0,1.5707963",
     dict(cx=128, cy=96, r=95, start=0, end=1.5707963), "agree"),
    ("arcwrap_r15", "CIRCLE(60,60),15,15,3,1",
     dict(cx=60, cy=60, r=15, start=3, end=1), "agree"),
    ("full628_r15", "CIRCLE(60,60),15,15,0,6.28",
     dict(cx=60, cy=60, r=15, start=0, end=6.28), "agree"),
    ("spoke_270", "CIRCLE(60,60),15,15,-1.57,0",
     dict(cx=60, cy=60, r=15, start=-1.57, end=0, sneg=True), "agree"),
    ("spoke_r3", "PSET(75,60),9:CIRCLE(60,60),15,6,-0.01,1.57",
     None, "agree"),                       # colour row -- pattern via model n/a
    ("sw_0.5_2.2", "CIRCLE(128,96),95,15,0.5,2.2",
     dict(cx=128, cy=96, r=95, start=0.5, end=2.2), "agree"),
    ("sw_1.1_3.6", "CIRCLE(128,96),95,15,1.1,3.6",
     dict(cx=128, cy=96, r=95, start=1.1, end=3.6), "agree"),
    ("sw_2.4_5.7", "CIRCLE(128,96),95,15,2.4,5.7",
     dict(cx=128, cy=96, r=95, start=2.4, end=5.7), "agree"),
    ("sw_0.35_1.05", "CIRCLE(128,96),95,15,0.35,1.05",
     dict(cx=128, cy=96, r=95, start=0.35, end=1.05), "agree"),
    ("lad_r24", "CIRCLE(128,96),24,15,1.1,2.04",
     dict(cx=128, cy=96, r=24, start=1.1, end=2.04), "agree"),
    ("lad_r48", "CIRCLE(128,96),48,15,1.1,2.04",
     dict(cx=128, cy=96, r=48, start=1.1, end=2.04), "agree"),
    ("lad_r190", "CIRCLE(128,280),190,15,1.1,2.04",
     dict(cx=128, cy=280, r=190, start=1.1, end=2.04), "agree"),
    ("arcctl_r200", "CIRCLE(128,352),200,15,1.1,2.04",
     dict(cx=128, cy=352, r=200, start=1.1, end=2.04), "agree"),
    ("arc_r700_a137", "CIRCLE(128,96),700,15,0,1.57,.137",
     dict(cx=128, cy=96, r=700, asps=35, start=0, end=1.57), "agree"),
    ("fn_0.885", "CIRCLE(128,280),190,15,0.885,1.935",
     dict(cx=128, cy=280, r=190, start=0.885, end=1.935), "agree"),
    ("arc_big_r400", "CIRCLE(128,96),400,15,-1.57,0",
     dict(cx=128, cy=96, r=400, start=-1.57, end=0, sneg=True), "diff-ok"),
]


def prog(stmts):
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


def run(machine, ops):
    specs = [("stored", prog([LINIT, ops]))]
    return omsx_repl.run_cases(machine, specs, batch=False,
                               capture=("vram_segs", PLANE), step=15.0)[0]


def reduce_hex(hexs):
    if not hexs:
        return None
    b = bytes.fromhex(hexs)
    return ("SHORT", len(b), None) if len(b) != 6144 else reduce_plane(b)


def main():
    print("=== D-ARCMASK: the oracle, after the rewrite ===")
    print(f"ref={REF}  zb={ZB}\n")
    zmiss = unexpected = 0
    for lbl, ops, kw, expect in CASES:
        pred = None if kw is None else reduce_plane(plane(draw_pair(**kw)))
        rr, zz = reduce_hex(run(REF, ops)), reduce_hex(run(ZB, ops))
        v = "agree" if rr == zz else "DIFF "
        pm = ""
        if pred is not None and zz != pred:
            zmiss += 1
            pm = f"  🔴 ZEROBAS != MODEL (model {pred})"
        bad = (v == "DIFF ") != (expect == "diff-ok")
        unexpected += bad
        mark = "🔴" if bad or pm else "  "
        print(f"{mark}{v} {lbl:14} {ops}{pm}")
        print(f"        ref = {rr}")
        print(f"        zb  = {zz}")
    print(f"\n=== zerobas-vs-model misses: {zmiss};  "
          f"unexpected agree/diff: {unexpected} ===")
    return 1 if (zmiss or unexpected) else 0


if __name__ == "__main__":
    sys.exit(main())
