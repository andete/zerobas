#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARCMASK step 2 -- INVERT the reference reading into a boundary.

arcmask_ref.py refutes every forward hypothesis on `arcctl_r200`: zerobas 181,
H1 (exact trig) 182, H4 183 -- and the VG-8020 draws 170. Nothing that only
sharpens the boundary VECTOR moves 11 pixels. So stop guessing the arithmetic
and ask the reading directly: WHICH angular window did the reference keep?

The mask keeps P iff cross(P,S)>=0 and cross(E,P)>=0 -- for exact rays that is
exactly "the direction of P lies in the closed angular window [S,E]". So the
kept set of any wedge mask is a CONTIGUOUS RUN of the full circle's points in
angle order. Enumerate every contiguous run, keep the ones whose whole 6144-byte
plane hashes to the reference's sha1, and read the boundary off the answer.

⚠️ This can only speak for masks that ARE angular wedges. If no run matches,
that is itself the finding -- the reference's mask is not a wedge, and no
sharpening of S/E can ever reproduce it.

    python3 -u scratchpad/arcmask_invert.py
"""
from __future__ import annotations

import math
import sys

import arcmask_model as M
from circovf_calib import W, H, octant, mirrors, plane, reduce_plane

CASES = [
    # label, cx, cy, r, asps, aspmaj, ref(px, sha1), zb(px, sha1), extra px
    ("arcctl_r200", 128, 352, 200, 256, 0, (170, "386f8fb8"), (181, "7956e005"),
     frozenset()),
    ("arc_r700_a137", 128, 96, 700, 35, 0, (127, "ebfd085b"), (126, "752131e6"),
     frozenset()),
]


def full_points(cx, cy, r, asps, aspmaj):
    """Every (scaled offset, screen pixel) the unmasked figure emits."""
    out = []
    seen = set()
    for qx, qy in octant(r):
        for dx, dy in mirrors(qx, qy):
            if aspmaj:
                sx, sy = M.circ_scale(dx, asps), dy
            else:
                sx, sy = dx, M.circ_scale(dy, asps)
            if (sx, sy) in seen:
                continue
            seen.add((sx, sy))
            x, y = cx + sx, cy + sy
            if 0 <= x < W and 0 <= y < H:
                out.append((sx, sy, x, y))
    return out


def main():
    print("=== D-ARCMASK: invert the reference reading into a wedge ===\n")
    rc = 0
    for lbl, cx, cy, r, asps, aspmaj, ref, zb, extra in CASES:
        pts = full_points(cx, cy, r, asps, aspmaj)
        # order by direction. atan2(sy, sx) is the SCREEN direction; the mask's
        # own orientation does not matter, only that the wedge is contiguous.
        pts.sort(key=lambda p: math.atan2(p[1], p[0]))
        n = len(pts)
        print(f"--- {lbl}: {n} visible unmasked points, "
              f"ref {ref[0]} px {ref[1]}, zb {zb[0]} px {zb[1]}")
        hits = []
        for i in range(n):
            px = set()
            for k in range(n):
                sx, sy, x, y = pts[(i + k) % n]
                px.add((x, y))
                if len(px) != ref[0]:
                    continue
                red = reduce_plane(plane(px))
                if red[2] == ref[1]:
                    a0 = math.atan2(pts[i][1], pts[i][0])
                    a1 = math.atan2(pts[(i + k) % n][1], pts[(i + k) % n][0])
                    hits.append((i, k, a0, a1, pts[i][:2], pts[(i + k) % n][:2]))
        if not hits:
            print("    NO CONTIGUOUS WEDGE REPRODUCES THE REFERENCE PLANE.")
            print("    -> the reference's arc mask is NOT an angular wedge over")
            print("       this point set; sharpening S/E cannot reach it.")
            rc = 1
        for i, k, a0, a1, p0, p1 in hits:
            print(f"    WEDGE first={p0} ({a0:+.5f} rad)  last={p1} "
                  f"({a1:+.5f} rad)  span={k + 1} emitted pts")
            # screen convention: the BASIC angle theta has Vy = -sin(theta)
            print(f"          -> BASIC angles: start {-a1:+.5f} rad, "
                  f"end {-a0:+.5f} rad")
        print()
    return rc


if __name__ == "__main__":
    sys.exit(main())
