#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARCMASK step 6 -- a FORWARD model of the reference, scored on whole planes.

What the 60-sample fine sweep says (arcmask_fine.json, r=190, brackets 0.0026
rad, rig clean: dead subject 1 px, controls byte-identical, zerobas predicted
exactly on all 36 rows):

Fold the boundary angle to the nearest axis, f = distance to that axis, in
[0, pi/4]. Read the reference's boundary as the octant loop's STEP INDEX k --
min(|dx|,|dy|) of the last kept point. Then, measured:

    k advances by a CONSTANT 6 steps for every 0.035 rad of f, across the
    whole octant, on both the start and the end side, over 44 samples.

k is LINEAR in f. The correct value is r*sin(f), which is not. The slope is
r*(2*sqrt(2)/pi): the linear map is exact at f=0 and at f=pi/4 (where
r*sin(pi/4) = 0.7071r is the octant's own step count) and wrong in between, by
up to 0.032 rad -- 6 px at r=190, under a pixel at r=15.

⚠️ THAT IS WHY THE CORPUS COULD NOT SEE IT. Every arc the G4 fit was validated
against is r=15 (g4_pointsets.json: radii 4..20, arcs all r=15), where 0.032
rad is 0.5 px. The fit assumed `(round(r*cos), -round(r*sin))` -- exact rays --
and at r=15 that assumption is indistinguishable from the truth.

So zerobas is MORE ACCURATE than the reference, and under a faithful-MSX1
charter that is the defect.

    python3 -u scratchpad/arcmask_refmodel.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import arcmask_model as M
from circovf_calib import W, H, octant, mirrors, plane, reduce_plane

HERE = os.path.dirname(os.path.abspath(__file__))
TAU = 2 * math.pi
PI2 = math.pi / 2
C_LIN = math.sin(math.pi / 4) / (math.pi / 4)      # 2*sqrt(2)/pi = 0.900316


def step_of(sx, sy):
    """The octant loop's step index of an offset: its smaller |coordinate|."""
    return min(abs(sx), abs(sy))


def pos_of_angle(theta, k, r):
    """Circular position of a boundary: nearest axis + side*asin(k/r)."""
    axis = round(theta / PI2) * PI2
    side = 1.0 if (theta - axis) >= 0 else -1.0
    return (axis + side * math.asin(min(1.0, k / r))) % TAU


def pos_of_point(sx, sy, r):
    """The same scale applied to an emitted point, so ties are exact."""
    th = math.atan2(-sy, sx) % TAU
    axis = round(th / PI2) * PI2
    side = 1.0 if ((th - axis + math.pi) % TAU - math.pi) >= 0 else -1.0
    return (axis + side * math.asin(min(1.0, step_of(sx, sy) / r))) % TAU


def boundary_k(theta, r, mode):
    """The reference's boundary step index for angle theta at radius r."""
    axis = round(theta / PI2) * PI2
    f = abs(theta - axis)
    if mode == "linear":                       # the measured rule
        return int(math.floor(C_LIN * r * f + 0.5))
    return int(math.floor(r * math.sin(f) + 0.5))   # "exact" -- what G4 assumed


def draw_ref(cx, cy, r, asps=256, aspmaj=0, start=None, end=None,
             sneg=False, eneg=False, mode="linear", inc_s=True, inc_e=True):
    arcf = start is not None or end is not None
    px = set()
    if arcf:
        ts, te = abs(start or 0.0), abs(end or 0.0)
        ps = pos_of_angle(ts, boundary_k(ts, r, mode), r)
        pe = pos_of_angle(te, boundary_k(te, r, mode), r)
        span = (pe - ps) % TAU
    for qx, qy in octant(r):
        for dx, dy in mirrors(qx, qy):
            if aspmaj:
                sx, sy = M.circ_scale(dx, asps), dy
            else:
                sx, sy = dx, M.circ_scale(dy, asps)
            if arcf:
                # the mask runs on the RAW octant point (the scale is applied
                # to the plotted offset, not to the step index)
                d = (pos_of_point(dx, dy, r) - ps) % TAU
                eps = 1e-9
                if not ((d >= -eps if inc_s else d > eps)
                        and (d <= span + eps if inc_e else d < span - eps)):
                    continue
            x, y = cx + sx, cy + sy
            if 0 <= x < W and 0 <= y < H:
                px.add((x, y))
    if arcf:
        for want, th in ((sneg, abs(start or 0.0)), (eneg, abs(end or 0.0))):
            if not want:
                continue
            p = pos_of_angle(th, boundary_k(th, r, mode), r)
            vx, vy = round(r * math.cos(p)), -round(r * math.sin(p))
            for x, y in M.bres_line(cx, cy, cx + vx, cy + vy):
                if 0 <= x < W and 0 <= y < H:
                    px.add((x, y))
    return px


def corpus():
    """Every measured REFERENCE plane the tree holds, as (label, kw, sha1)."""
    import arcmask_sweep as S
    import arcmask_fine as F
    rows = []
    for mod, fn in ((S, "arcmask_sweep.json"), (F, "arcmask_fine.json")):
        data = json.load(open(os.path.join(HERE, fn)))
        for lbl, ops, kw, why in mod.CASES:
            if kw is None or "start" not in kw:
                continue
            b = bytes.fromhex(data[lbl]["ref"])
            rows.append((f"{fn[9:-5]}:{lbl}", kw, reduce_plane(b)))
    return rows


def main():
    rows = corpus()
    print("=== D-ARCMASK: forward model of the VG-8020, whole-plane sha1 ===")
    print(f"{len(rows)} measured reference rows\n")
    best = []
    for mode in ("linear", "exact"):
        for inc_s in (True, False):
            for inc_e in (True, False):
                ok = miss = 0
                for lbl, kw, want in rows:
                    got = reduce_plane(plane(draw_ref(mode=mode, inc_s=inc_s,
                                                      inc_e=inc_e, **kw)))
                    ok += got == want
                    miss += got != want
                best.append((ok, mode, inc_s, inc_e))
                print(f"  {mode:7} inc_start={inc_s!s:5} inc_end={inc_e!s:5}"
                      f"  ->  {ok}/{len(rows)} planes exact")
    best.sort(reverse=True)
    ok, mode, inc_s, inc_e = best[0]
    print(f"\n=== best: {mode}, inc_start={inc_s}, inc_end={inc_e} "
          f"-> {ok}/{len(rows)} ===")
    if ok < len(rows):
        print("\n--- rows the best variant still misses ---")
        for lbl, kw, want in rows:
            got = reduce_plane(plane(draw_ref(mode=mode, inc_s=inc_s,
                                              inc_e=inc_e, **kw)))
            if got != want:
                print(f"  {lbl:28} model={got[0]:4} {got[2]}  "
                      f"ref={want[0]:4} {want[2]}   {kw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
