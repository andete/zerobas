#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCOVF step 2 -- SEARCH for the rows worth booting an emulator for.

Uses the model calibrated in scratchpad/circovf_calib.py (22/22 measured
readings reproduced from arithmetic alone). Ranks candidate rows by what they
can DISCRIMINATE, not by how big the divergence looks:

  * "oracle"  -- the EXACT model puts overflowing points ON SCREEN. Only such a
                 row can read what a CORRECT overflowing circle looks like.
                 EVERY row D-CIRCDOM measured has ZERO of them, which is why the
                 fix has no positive oracle yet.
  * "partial" -- BOTH models draw something AND they differ. The strongest
                 shape available: a row where both sides are visible cannot be
                 explained away by "the reference refused the statement".
  * "control" -- no overflowing point anywhere, at the SAME off-screen centre.
                 A byte-identical control there is what makes the DIFF beside it
                 attributable to the overflow rather than to the centre.

The geometry, which is why this needs a search at all: overflow needs a scaled
minor offset >= 256, and the screen is 192 tall. So no overflowing point can
EVER be on screen while the centre is on screen. The centre has to leave the
screen along the MINOR axis. That one move is what every previous row missed.

Brute force is too slow (r up to 700 x cy up to 700 x ~4000 points). Instead,
per radius, keep only the points whose MAJOR-axis coordinate is on screen --
a few hundred -- then slide the 192-pixel window over their scaled minor
offsets. Same answer, ~1000x less work.

    python3 -u scratchpad/circovf_search.py
"""
from __future__ import annotations

import sys

from circovf_calib import (mirrors, octant, pixels, plane, reduce_plane,
                           scale_exact, scale_trunc)

W, H = 256, 192


def candidates(r, asps, maj, c_major):
    """Points whose MAJOR-axis screen coordinate is on screen, as
    (exact minor offset, trunc minor offset). The minor centre is free."""
    out = []
    for qx, qy in octant(r):
        for dx, dy in mirrors(qx, qy):
            major, minor = (dy, dx) if maj else (dx, dy)
            if 0 <= c_major + major < (H if maj else W):
                out.append((scale_exact(minor, asps), scale_trunc(minor, asps),
                            abs(minor) * asps >= 65536))
    return out


def best_minor_centre(cand, span):
    """Slide the `span`-wide screen window; return (c_minor, exact-on-screen,
    trunc-on-screen, overflowing-and-on-screen-under-exact)."""
    best = None
    lo = min((e for e, _, _ in cand), default=0)
    hi = max((e for e, _, _ in cand), default=0)
    for c in range(-hi, -lo + 1):
        ne = nt = hot = 0
        for e, t, ovf in cand:
            if 0 <= c + e < span:
                ne += 1
                hot += ovf
            if 0 <= c + t < span:
                nt += 1
        if hot and (best is None or (hot, ne) > (best[3], best[1])):
            best = (c, ne, nt, hot)
    return best


def row(cx, cy, r, asps, maj=0):
    pe, he = pixels(cx, cy, r, asps, maj, scale_exact)
    pt, _ = pixels(cx, cy, r, asps, maj, scale_trunc)
    return dict(cx=cx, cy=cy, r=r, asps=asps, maj=maj, ne=len(pe), nt=len(pt),
                hot=he, only_e=len(pe - pt), only_t=len(pt - pe),
                red_e=reduce_plane(plane(pe)), red_t=reduce_plane(plane(pt)))


def show(tag, d):
    print(f"  {tag:9} c=({d['cx']},{d['cy']}) r={d['r']:5d} ASPS={d['asps']:3d} "
          f"maj={d['maj']} | ref {d['ne']:4d}px  zb {d['nt']:4d}px | "
          f"ovf-on-screen {d['hot']:4d} | ref-only {d['only_e']:4d} "
          f"zb-only {d['only_t']:4d}")
    return d


def sweep(title, asps, maj, radii):
    print(f"\n-- {title} --")
    found = []
    for r in radii:
        cand = candidates(r, asps, maj, 96 if maj else 128)
        b = best_minor_centre(cand, H if not maj else W)
        if b is None:
            continue
        c, _, _, _ = b
        d = row(128, c, r, asps, maj) if not maj else row(c, 96, r, asps, maj)
        if d["hot"]:
            found.append(d)
    # a PARTIAL row (both draw) beats a bigger one-sided divergence
    found.sort(key=lambda d: (min(d["ne"], d["nt"]) > 0, d["hot"] + d["ne"]),
               reverse=True)
    for d in found[:8]:
        show("partial" if min(d["ne"], d["nt"]) else "oracle", d)
    return found


def main():
    print("=== D-CIRCOVF: candidate search (offline, calibrated model) ===")
    sweep("A. default aspect, ASPS=256 (wrap is exactly v mod 256)",
          256, 0, range(256, 620, 2))
    sweep("B. explicit aspect .5 -> ASPS=128, x-major (minor is Y)",
          128, 0, range(520, 1400, 8))
    sweep("C. explicit aspect 2 -> ASPS=128, y-major (minor is X) -- the "
          "OTHER branch", 128, 1, range(520, 1400, 8))

    print("\n-- D. CONTROLS: same off-screen centre, no overflow anywhere --")
    for cx, cy, r, asps, maj in ((128, 352, 200, 256, 0),
                                 (128, 352, 255, 256, 0),
                                 (128, 396, 500, 128, 0),
                                 (428, 96, 500, 128, 1)):
        show("control", row(cx, cy, r, asps, maj))
    return 0


if __name__ == "__main__":
    sys.exit(main())
