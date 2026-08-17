#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARCMASK step 4 -- read the reference's BOUNDARY RAY off every measured row.

arcmask_sweep.json holds the whole 6144-byte plane for 19 rows on both machines
(rig clean: the dead subject reads 1 px, both byte-identical controls held, and
the zerobas model predicted all 18 CIRCLE rows exactly). So the reference's kept
PIXEL SET is in hand -- no searching, no hashing. Map it back onto the octant
loop's emitted offsets and the two boundary rays fall out as brackets:

    last kept point   <   the ray   <   first dropped point   (in angle)

Then ask what function of (theta, r) lands in every bracket at once.

⚠️ A bracket is an INTERVAL, not a reading. A model is refuted only when it
falls OUTSIDE one; a model inside every bracket is consistent, not proven.

    python3 -u scratchpad/arcmask_rays.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import arcmask_model as M
import arcmask_sweep as S
from circovf_calib import W, H, octant, mirrors

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "arcmask_sweep.json")))


def unpack(hexs):
    """SCREEN 2 pattern plane -> set of lit (x, y)."""
    b = bytes.fromhex(hexs)
    px = set()
    for i, v in enumerate(b):
        if not v:
            continue
        row, rest = i // 256, i % 256
        col, y = rest // 8, row * 8 + (rest % 8)
        for bit in range(8):
            if v & (0x80 >> bit):
                px.add((col * 8 + bit, y))
    return px


def emitted(cx, cy, r, asps, aspmaj):
    """Every visible (scaled offset -> pixel) the UNMASKED figure emits."""
    out = {}
    for qx, qy in octant(r):
        for dx, dy in mirrors(qx, qy):
            if aspmaj:
                sx, sy = M.circ_scale(dx, asps), dy
            else:
                sx, sy = dx, M.circ_scale(dy, asps)
            x, y = cx + sx, cy + sy
            if 0 <= x < W and 0 <= y < H:
                out.setdefault((sx, sy), (x, y))
    return out


def basic_angle(sx, sy):
    """BASIC angle of a screen offset (screen convention: Vy = -sin)."""
    return math.atan2(-sy, sx) % (2 * math.pi)


def rays(kept, emit):
    """Bracket the two boundary rays of a contiguous angular wedge."""
    offs = sorted(emit, key=lambda o: basic_angle(*o))
    n = len(offs)
    inw = [emit[o] in kept for o in offs]
    if all(inw) or not any(inw):
        return None
    # rotate to a wedge start: index i where inw[i] and not inw[i-1]
    st = next(i for i in range(n) if inw[i] and not inw[i - 1])
    en = next(i for i in range(n) if inw[i] and not inw[(i + 1) % n])
    run = [offs[(st + k) % n] for k in range((en - st) % n + 1)]
    if not all(emit[o] in kept for o in run) or len(run) != sum(inw):
        return "NOT-CONTIGUOUS"
    lo_kept, lo_drop = offs[st], offs[st - 1]
    hi_kept, hi_drop = offs[en], offs[(en + 1) % n]
    return (basic_angle(*lo_drop), basic_angle(*lo_kept),
            basic_angle(*hi_kept), basic_angle(*hi_drop))


def main():
    print("=== D-ARCMASK: the reference's boundary rays, bracketed ===\n")
    print(f"{'row':14} {'r':>4} {'asked':>8}  reference ray bracket        "
          f"zerobas ray        exact r*(cos,sin) ray")
    out = []
    for lbl, ops, kw, why in S.CASES:
        if kw is None or "start" not in kw:
            continue
        d = DATA[lbl]
        r = kw["r"]
        asps, aspmaj = kw.get("asps", 256), kw.get("aspmaj", 0)
        emit = emitted(kw["cx"], kw["cy"], r, asps, aspmaj)
        for who, hexs in (("ref", d["ref"]), ("zb", d["zb"])):
            res = rays(unpack(hexs), emit)
            if res == "NOT-CONTIGUOUS":
                print(f"  🔴 {lbl} {who}: kept set is NOT an angular wedge")
        rr = rays(unpack(d["ref"]), emit)
        zr = rays(unpack(d["zb"]), emit)
        if rr is None or zr is None or rr == "NOT-CONTIGUOUS":
            print(f"  {lbl:14} (no readable boundary)")
            continue
        # boundary S (the "start" ray) is the low-angle edge of the wedge
        for side, (dropA, keptA), (zd, zk) in (
                ("start", (rr[0], rr[1]), (zr[0], zr[1])),
                ("end", (rr[3], rr[2]), (zr[3], zr[2]))):
            asked = kw["start"] if side == "start" else kw["end"]
            lo, hi = sorted((dropA, keptA))
            zlo, zhi = sorted((zd, zk))
            print(f"  {lbl:14} {r:>4} {asked:>8}  {side:5} "
                  f"({lo:.5f},{hi:.5f})   ({zlo:.5f},{zhi:.5f})")
            out.append(dict(row=lbl, r=r, asps=asps, aspmaj=aspmaj,
                            side=side, asked=abs(asked),
                            ref=(lo, hi), zb=(zlo, zhi)))
    with open(os.path.join(HERE, "arcmask_rays.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(f"\n=== {len(out)} bracketed rays -> arcmask_rays.json ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
