#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARCMASK step 0 -- an OFFLINE model of the zerobas ARC MASK, calibrated
against MEASURED artifacts before it is allowed to predict anything.

circovf_calib.py models the octant loop + the minor scale and is calibrated
22/22, but it does NOT model the arc mask -- so every arc question so far has
had to be answered by booting two emulators and diffing. This adds the mask:

  * cpt_boundary_prep  (sub/circleparse.asm) -- brad = round(|theta|*128/pi)
    as a RAW int16, plus the three continuous quadrant compares that give
    sign_c / sign_s.
  * gfx_circ_bvec + QTAB + fold + gfx_circ_bvec_mag + gfx_circ_bvec_nudge
    (sub/graphics.asm) -- (brad, sign_c, sign_s) -> the boundary vector,
    with the near-cardinal +-1 nudge and the screen-convention Vy = -(sin).
  * gfx_circ_arcbig_calc -- ARCBIG from the RAW brad pair.
  * gfx_circ_keep -- cross(P,S)>=0 AND cross(E,P)>=0, OR'd when ARCBIG.
  * gco_spoke_s / gco_spoke_e -- the deferred spokes a NEGATIVE angle asks
    for, drawn AFTER the arc, as gfx_line_op segments from the centre.

⚠️ It must rebuild the whole 6144-byte PATTERN PLANE, not a (popcount, bbox)
summary -- D-CIRCDOM's K-CD3 missed for exactly that reason.

    python3 -u scratchpad/arcmask_model.py
"""
from __future__ import annotations

import math
import sys

from circovf_calib import W, H, octant, mirrors, plane, reduce_plane

# --- QTAB, verbatim from sub/graphics.asm ---------------------------------
QTAB = [
    0,   6,  13,  19,  25,  31,  38,  44,  50,  56,
    62,  68,  74,  80,  86,  92,  98, 104, 109, 115,
    121, 126, 132, 137, 142, 147, 152, 157, 162, 167,
    172, 177, 181, 185, 190, 194, 198, 202, 206, 209,
    213, 216, 220, 223, 226, 229, 231, 234, 237, 239,
    241, 243, 245, 247, 248, 250, 251, 252, 253, 254,
    255, 255, 255, 255, 255,
]
assert len(QTAB) == 65

# The 14-digit decimal constants cpt_boundary_prep compares against, exactly as
# the 18-byte FPNUM records spell them (sub/circleparse.asm).
HALF_PI = 1.57079632679489
PI_C = 3.14159265358979
THREE_HALF_PI = 4.71238898038468
K_128_PI = 40.7436654315252


def fold(b):
    """gfx_qtab_fold: m = b & 0x7F; if m > 64: m = 128 - m."""
    m = b & 0x7F
    return m if m <= 64 else 128 - m


def qtab(b):
    """gfx_qtab_lookup: QTAB[fold(b & 0xFF)]."""
    return QTAB[fold(b & 0xFF)]


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v >= 0x8000 else v


def cpt_round(x):
    """cpt_round: round-half-AWAY-from-zero, via trunc(|x|+0.5)."""
    return int(math.copysign(int(abs(x) + 0.5), x)) if x else 0


def boundary_prep(theta):
    """cpt_boundary_prep -> (raw_brad, sign_c, sign_s). theta is |angle|."""
    if theta == HALF_PI or theta == THREE_HALF_PI:
        sign_c = 0
    elif theta < HALF_PI or theta > THREE_HALF_PI:
        sign_c = 1
    else:
        sign_c = -1
    if theta == 0.0 or theta == PI_C:
        sign_s = 0
    elif theta < PI_C:
        sign_s = 1
    else:
        sign_s = -1
    return s16(cpt_round(theta * K_128_PI)), sign_c, sign_s


def bvec_mag(r, tab):
    """gfx_circ_bvec_mag: (r*tab+128)>>8, full width (gfx_mul16r)."""
    return (r * tab + 128) >> 8


def nudge(mag, sign):
    """gfx_circ_bvec_nudge."""
    if sign == 0:
        return 0
    if mag == 0:
        mag = 1
    return s16(-mag if sign < 0 else mag)


def circ_scale(v, asps):
    """gfx_circ_scale: identity arm at ASPS=256, else sign*((|v|*ASPS+128)>>8)."""
    if asps >> 8:
        return v
    o = (abs(v) * asps + 128) >> 8
    return s16(-o if v < 0 else o)


def bvec(raw_brad, sign_c, sign_s, r, asps, aspmaj):
    """gfx_circ_bvec -> (Vx, Vy). Only the LOW byte of brad reaches QTAB."""
    lo = raw_brad & 0xFF
    vx = nudge(bvec_mag(r, qtab(lo + 64)), sign_c)
    if aspmaj:
        vx = circ_scale(vx, asps)
    vy = nudge(bvec_mag(r, qtab(lo)), sign_s)
    if not aspmaj:
        vy = circ_scale(vy, asps)
    return vx, s16(-vy)              # screen convention: Vy = -(sin component)


def arcbig(raw_s, raw_e):
    """gfx_circ_arcbig_calc."""
    hl = (raw_e - raw_s) & 0xFFFF
    diff8 = hl & 0xFF
    if diff8:
        return diff8 >= 129
    return hl != 0


def keep(px, py, s, e, big):
    """gfx_circ_keep. c1 = cross(P,S)>=0, c2 = cross(E,P)>=0."""
    c1 = px * s[1] - py * s[0] >= 0
    c2 = e[0] * py - e[1] * px >= 0
    return (c1 or c2) if big else (c1 and c2)


def bres_line(x1, y1, x2, y2):
    """gfx_line_op's segment, as the plain integer Bresenham the tenant runs."""
    pts = []
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    sx = 1 if x2 >= x1 else -1
    sy = 1 if y2 >= y1 else -1
    x, y = x1, y1
    if dx >= dy:
        err = 2 * dy - dx
        for _ in range(dx + 1):
            pts.append((x, y))
            if err >= 0:
                y += sy
                err -= 2 * dx
            err += 2 * dy
            x += sx
    else:
        err = 2 * dx - dy
        for _ in range(dy + 1):
            pts.append((x, y))
            if err >= 0:
                x += sx
                err -= 2 * dy
            err += 2 * dx
            y += sy
    return pts


def draw(cx, cy, r, asps=256, aspmaj=0, start=None, end=None,
         sneg=False, eneg=False):
    """The whole tenant: gfx_circle_op, arc mask and deferred spokes."""
    arcf = start is not None or end is not None
    s = e = None
    big = False
    if arcf:
        rs, sc, ss = boundary_prep(0.0 if start is None else abs(start))
        re_, ec, es = boundary_prep(0.0 if end is None else abs(end))
        s = bvec(rs, sc, ss, r, asps, aspmaj)
        e = bvec(re_, ec, es, r, asps, aspmaj)
        big = arcbig(rs, re_)
    px = set()
    for qx, qy in octant(r):
        for dx, dy in mirrors(qx, qy):
            if aspmaj:
                sx, sy = circ_scale(dx, asps), dy
            else:
                sx, sy = dx, circ_scale(dy, asps)
            if arcf and not keep(sx, sy, s, e, big):
                continue
            x, y = cx + sx, cy + sy
            if 0 <= x < W and 0 <= y < H:
                px.add((x, y))
    for want, v in ((sneg, s), (eneg, e)):
        if want and v is not None:
            for x, y in bres_line(cx, cy, cx + v[0], cy + v[1]):
                if 0 <= x < W and 0 <= y < H:
                    px.add((x, y))
    return px


# --- CALIBRATION: every arc reading this tree has published a zerobas value
# for. docs/circovf-msx1-oracle.md §6.1 (the three red rows) + the gate's own
# green arc rows, which agree on both machines so a zerobas model must hit them
# too. label, kwargs, measured zerobas (px, sha1).
CALIB = [
    ("arcctl_r200", dict(cx=128, cy=352, r=200, start=1.1, end=2.04),
     (181, "7956e005")),
    ("arc_r700_a137", dict(cx=128, cy=96, r=700, asps=35, start=0, end=1.57),
     (126, "752131e6")),
    ("arc_big_r400", dict(cx=128, cy=96, r=400, start=-1.57, end=0,
                          sneg=True),
     (97, "76352feb")),
]


def main():
    print("=== D-ARCMASK: offline arc-mask model vs MEASURED zerobas ===")
    print("(docs/circovf-msx1-oracle.md §6.1. Nothing here boots an emulator.)\n")
    bad = ok = 0
    for lbl, kw, want in CALIB:
        red = reduce_plane(plane(draw(**kw)))
        good = (red[0], red[2]) == want
        ok += good
        bad += not good
        print(f"  {'OK  ' if good else 'MISS'} {lbl:14} model={red}  "
              f"measured={want}")
    print()
    print(f"=== {ok} exact / {bad} missed, of {ok + bad} readings ===")
    print("=== zerobas model " + ("CALIBRATED" if not bad else "REFUTED") + " ===")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
