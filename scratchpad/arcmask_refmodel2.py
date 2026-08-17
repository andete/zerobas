#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARCMASK step 7 -- the OCTANT-ASYMMETRIC reference model, scored on planes.

Step 6 got 22/51 with "the boundary step index is linear in the distance to the
nearest axis". Its residuals were not noise: at r=190 they ALTERNATE between the
two interleaved sub-sequences of the fine sweep -- the rays just BELOW pi/2 and
the rays just ABOVE it. The reference is not symmetric about the axis, which is
what folding to |theta - axis| threw away.

Restated in octants instead: with `o = floor(theta/(pi/4))` and `u` the fraction
into that octant, the octant loop's step index RISES with theta in even octants
and FALLS in odd ones, so a single `floor` lands on opposite sides of the two.

    pos = floor(u * M),    M = floor(r/sqrt(2))
    k   = pos              in an even octant
    k   = M - pos          in an odd octant

That is **parameter-free** -- no fitted constant, no per-side offset -- and it
reproduces 80/80 of the integer boundaries extracted from the measured planes.

⚠️ 80/80 ON THE FIRST RUN IS THE SHAPE TO DISTRUST, and those 80 rays are what
the rule was fitted on. THIS file is the independent test: score it on the whole
6144-byte plane of all 51 measured reference arc rows -- which includes the rows
whose boundary was NOT a clean single step (dropped from the fit), the ARCBIG
wraps, the deferred spokes, and the aspect row, none of which the fit ever saw.

    python3 -u scratchpad/arcmask_refmodel2.py
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
PI4 = math.pi / 4


def mmax(r):
    """M -- the octant's top step index."""
    return int(math.floor(r / math.sqrt(2)))


def gpos_angle(theta, r):
    """Global arc position (0..8M) of a BOUNDARY at angle theta."""
    t = theta % TAU
    o = int(t // PI4) % 8
    u = (t - (t // PI4) * PI4) / PI4
    return o * mmax(r) + int(math.floor(u * mmax(r)))


def gpos_point(sx, sy, r):
    """Global arc position of an EMITTED point, on the same scale."""
    t = math.atan2(-sy, sx) % TAU
    o = int(t // PI4) % 8
    step = min(abs(sx), abs(sy))
    pos = step if o % 2 == 0 else mmax(r) - step
    return o * mmax(r) + pos


def octant_point(o, pos, r):
    """The (sx, sy) the loop emits at octant `o`, in-octant position `pos`."""
    step = pos if o % 2 == 0 else mmax(r) - pos
    best = None
    for qx, qy in octant(r):
        if qx == max(0, min(step, mmax(r))):
            best = (qx, qy)
            break
    if best is None:
        return None
    qx, qy = best
    # place (qx,qy) into octant o
    tbl = {0: (qy, -qx), 1: (qx, -qy), 2: (-qx, -qy), 3: (-qy, -qx),
           4: (-qy, qx), 5: (-qx, qy), 6: (qx, qy), 7: (qy, qx)}
    return tbl[o]


def draw_ref2(cx, cy, r, asps=256, aspmaj=0, start=None, end=None,
              sneg=False, eneg=False):
    arcf = start is not None or end is not None
    px = set()
    if arcf:
        ts, te = abs(start or 0.0), abs(end or 0.0)
        gs, ge = gpos_angle(ts, r), gpos_angle(te, r)
        total = 8 * mmax(r)
        span = (ge - gs) % total
    for qx, qy in octant(r):
        for dx, dy in mirrors(qx, qy):
            if aspmaj:
                sx, sy = M.circ_scale(dx, asps), dy
            else:
                sx, sy = dx, M.circ_scale(dy, asps)
            if arcf and (gpos_point(dx, dy, r) - gs) % total > span:
                continue
            x, y = cx + sx, cy + sy
            if 0 <= x < W and 0 <= y < H:
                px.add((x, y))
    if arcf:
        for want, th in ((sneg, abs(start or 0.0)), (eneg, abs(end or 0.0))):
            if not want:
                continue
            g = gpos_angle(th, r)
            v = octant_point(g // mmax(r) % 8, g % mmax(r), r)
            if v is None:
                continue
            vx, vy = v
            if aspmaj:
                vx = M.circ_scale(vx, asps)
            else:
                vy = M.circ_scale(vy, asps)
            for x, y in M.bres_line(cx, cy, cx + vx, cy + vy):
                if 0 <= x < W and 0 <= y < H:
                    px.add((x, y))
    return px


def corpus():
    import arcmask_sweep as S
    import arcmask_fine as F
    rows = []
    for mod, fn in ((S, "arcmask_sweep.json"), (F, "arcmask_fine.json")):
        data = json.load(open(os.path.join(HERE, fn)))
        for lbl, ops, kw, why in mod.CASES:
            if kw is None or "start" not in kw:
                continue
            rows.append((lbl, kw, reduce_plane(bytes.fromhex(data[lbl]["ref"])),
                         reduce_plane(bytes.fromhex(data[lbl]["zb"]))))
    # the three rows D-CIRCOVF §6.1 filed, which no run this slice re-measured
    for lbl, kw, want in (
        ("§6.1 arcctl_r200", dict(cx=128, cy=352, r=200, start=1.1, end=2.04),
         (170, "386f8fb8")),
        ("§6.1 arc_r700_a137", dict(cx=128, cy=96, r=700, asps=35, start=0,
                                    end=1.57), (127, "ebfd085b")),
        ("§6.1 arc_big_r400", dict(cx=128, cy=96, r=400, start=-1.57, end=0,
                                   sneg=True), (97, "cd7e5368")),
    ):
        rows.append((lbl, kw, (want[0], None, want[1]), None))
    return rows


def main():
    rows = corpus()
    print("=== D-ARCMASK: octant-asymmetric reference model, whole planes ===")
    print(f"{len(rows)} measured reference arc rows "
          f"(48 from this slice's sweeps + the 3 filed by D-CIRCOVF §6.1)\n")
    ok = miss = 0
    bad = []
    for lbl, kw, want, zb in rows:
        got = reduce_plane(plane(draw_ref2(**kw)))
        hit = got[2] == want[2] and got[0] == want[0]
        ok += hit
        miss += not hit
        if not hit:
            bad.append((lbl, kw, got, want, zb))
    print(f"=== {ok} / {len(rows)} whole 6144-byte planes EXACT ===")
    print(f"    (step 6's axis-folded model: 22/51;  exact rays: 2-4/51)\n")
    for lbl, kw, got, want, zb in bad:
        print(f"  MISS {lbl:22} model={got[0]:4} {got[2]}  ref={want[0]:4} "
              f"{want[2]}" + (f"  zb={zb[0]} {zb[2]}" if zb else ""))
        print(f"       {kw}")
    return 0 if not miss else 1


if __name__ == "__main__":
    sys.exit(main())
