#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARCMASK step 1 -- WHAT DOES THE REFERENCE DO? Hypotheses, scored offline.

arcmask_model.py reproduces zerobas exactly on every arc reading the tree has
(5/5, whole 6144-byte planes at sha1 + two r=15 point sets). This asks the
other half: which arithmetic reproduces the VG-8020?

The corpus, and what each row can and cannot decide:

  DISCRIMINATING (docs/circovf-msx1-oracle.md §6.1, whole-plane sha1, RED):
    arcctl_r200    ref 170 px 386f8fb8   zb 181 px 7956e005
    arc_r700_a137  ref 127 px ebfd085b   zb 126 px 752131e6
    arc_big_r400   ref  97 px cd7e5368   zb  97 px 76352feb

  NON-DISCRIMINATING BUT BINDING (scratchpad/g4_arc_boundary_capture.json,
  r=15, VG-8020 point sets that zerobas ALREADY matches): a candidate that
  breaks these is refuted even if it fixes the three above.

⚠️ Both-blank is not agreement, and neither is both-green: the r=15 rows agree
because r=15 cannot resolve a boundary error of under half a pixel. They are
kept as a REGRESSION floor, not as evidence.

    python3 -u scratchpad/arcmask_ref.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import arcmask_model as M
from circovf_calib import W, H, octant, mirrors, plane, reduce_plane

HERE = os.path.dirname(os.path.abspath(__file__))

# --- the reference corpus --------------------------------------------------
# label, draw kwargs, ref (px, sha1)
REF_PLANES = [
    ("arcctl_r200", dict(cx=128, cy=352, r=200, start=1.1, end=2.04),
     (170, "386f8fb8")),
    ("arc_r700_a137", dict(cx=128, cy=96, r=700, asps=35, start=0, end=1.57),
     (127, "ebfd085b")),
    ("arc_big_r400", dict(cx=128, cy=96, r=400, start=-1.57, end=0, sneg=True),
     (97, "cd7e5368")),
]

# r=15 VG-8020 point sets, from the G4-arcbnd capture.
_CAP = json.load(open(os.path.join(HERE, "g4_arc_boundary_capture.json")))
REF_POINTS = [
    ("arc_hpi_pi", dict(cx=60, cy=60, r=15, start=1.57, end=3.14),
     {tuple(p) for p in _CAP["round1"]["arc_hpi_pi_reconfirm"]["pts"]}),
    ("arc_wrap", dict(cx=60, cy=60, r=15, start=3, end=1),
     {tuple(p) for p in _CAP["round1"]["arc_wrap_reconfirm"]["pts"]}),
]


# --- the hypotheses: each is a boundary-vector function (raw_brad, signs,
# theta, r, asps, aspmaj) -> (Vx, Vy), everything else held at the tenant's.
def h_zerobas(theta, rb, sc, ss, r, asps, aspmaj):
    """H0: what the tenant does now -- QTAB at 1/256-turn angular resolution."""
    return M.bvec(rb, sc, ss, r, asps, aspmaj)


def _from_components(cx_, sy_, sc, ss, r, asps, aspmaj, rnd):
    """Shared tail: |cos|,|sin| magnitudes -> nudge -> minor scale -> -Vy."""
    vx = M.nudge(rnd(r * cx_), sc)
    if aspmaj:
        vx = M.circ_scale(vx, asps)
    vy = M.nudge(rnd(r * sy_), ss)
    if not aspmaj:
        vy = M.circ_scale(vy, asps)
    return vx, M.s16(-vy)


def _rh_up(x):
    return int(x + 0.5)


def h_exact_round(theta, rb, sc, ss, r, asps, aspmaj):
    """H1: exact trig, magnitudes rounded half-up. No angle quantisation."""
    return _from_components(abs(math.cos(theta)), abs(math.sin(theta)),
                            sc, ss, r, asps, aspmaj, _rh_up)


def h_exact_trunc(theta, rb, sc, ss, r, asps, aspmaj):
    """H2: exact trig, magnitudes truncated."""
    return _from_components(abs(math.cos(theta)), abs(math.sin(theta)),
                            sc, ss, r, asps, aspmaj, int)


def h_brad_exact_tab(theta, rb, sc, ss, r, asps, aspmaj):
    """H3: keep the 1/256-turn ANGLE quantisation, drop the 8-bit TABLE
    quantisation -- isolates which of the two quantisers is the divergence."""
    lo = rb & 0xFF
    return _from_components(abs(math.cos(2 * math.pi * ((lo + 64) & 0xFF) / 256)),
                            abs(math.sin(2 * math.pi * lo / 256)),
                            sc, ss, r, asps, aspmaj, _rh_up)


def h_tab_exact_brad(theta, rb, sc, ss, r, asps, aspmaj):
    """H4: the complement of H3 -- exact ANGLE, 8-bit table-grade magnitude
    (i.e. round(r*round(256*|trig|)/256))."""
    def mag(t):
        return (r * min(255, _rh_up(256 * t)) + 128) >> 8
    vx = M.nudge(mag(abs(math.cos(theta))), sc)
    if aspmaj:
        vx = M.circ_scale(vx, asps)
    vy = M.nudge(mag(abs(math.sin(theta))), ss)
    if not aspmaj:
        vy = M.circ_scale(vy, asps)
    return vx, M.s16(-vy)


HYPOTHESES = [
    ("H0 zerobas (QTAB, 1/256 turn)", h_zerobas),
    ("H1 exact trig, round half-up", h_exact_round),
    ("H2 exact trig, truncate", h_exact_trunc),
    ("H3 quantised ANGLE, exact table", h_brad_exact_tab),
    ("H4 exact ANGLE, quantised table", h_tab_exact_brad),
]


def draw_with(bfun, cx, cy, r, asps=256, aspmaj=0, start=None, end=None,
              sneg=False, eneg=False):
    """M.draw, with the boundary-vector computation swapped out."""
    arcf = start is not None or end is not None
    s = e = None
    big = False
    if arcf:
        ts = 0.0 if start is None else abs(start)
        te = 0.0 if end is None else abs(end)
        rs, sc, ss = M.boundary_prep(ts)
        re_, ec, es = M.boundary_prep(te)
        s = bfun(ts, rs, sc, ss, r, asps, aspmaj)
        e = bfun(te, re_, ec, es, r, asps, aspmaj)
        big = M.arcbig(rs, re_)
    px = set()
    for qx, qy in octant(r):
        for dx, dy in mirrors(qx, qy):
            if aspmaj:
                sx, sy = M.circ_scale(dx, asps), dy
            else:
                sx, sy = dx, M.circ_scale(dy, asps)
            if arcf and not M.keep(sx, sy, s, e, big):
                continue
            x, y = cx + sx, cy + sy
            if 0 <= x < W and 0 <= y < H:
                px.add((x, y))
    for want, v in ((sneg, s), (eneg, e)):
        if want and v is not None:
            for x, y in M.bres_line(cx, cy, cx + v[0], cy + v[1]):
                if 0 <= x < W and 0 <= y < H:
                    px.add((x, y))
    return px


def score(bfun):
    rows = []
    for lbl, kw, want in REF_PLANES:
        red = reduce_plane(plane(draw_with(bfun, **kw)))
        rows.append((lbl, (red[0], red[2]) == want, f"{red[0]} {red[2]}",
                     f"{want[0]} {want[1]}"))
    for lbl, kw, want in REF_POINTS:
        got = draw_with(bfun, **kw)
        rows.append((lbl, got == want, f"{len(got)} px",
                     f"{len(want)} px  d={len(got ^ want)}"))
    return rows


def main():
    print("=== D-ARCMASK: which arithmetic reproduces the VG-8020? ===")
    print("3 discriminating whole-plane rows + 2 r=15 regression point sets\n")
    best = []
    for name, fn in HYPOTHESES:
        rows = score(fn)
        n = sum(r[1] for r in rows)
        best.append((n, name))
        print(f"  {name}   -> {n}/{len(rows)}")
        for lbl, ok, got, want in rows:
            print(f"      {'OK  ' if ok else 'MISS'} {lbl:14} "
                  f"model={got:20} ref={want}")
        print()
    best.sort(reverse=True)
    print("=== ranking ===")
    for n, name in best:
        print(f"  {n}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
