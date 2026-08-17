#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARCMASK step 8 -- the INTEGER pipeline, simulated before any asm exists.

arcmask_refmodel2.py proves the reference's rule with host floats. This file is
the bridge to Z80: every operation below is one the tenant can actually run, at
the width it would run it, and the whole pipeline is scored against the same
banked planes. The circovf_asmsim.py discipline: simulate the instruction-level
arithmetic BEFORE building -- it caught a multiply that was wrong on 200037 of
200049 cases with no build and no boot.

The pipeline (P = parse tenant, sub/circleparse.asm; G = graphics tenant):

  P1  theta6 = ARGA rounded to 6 significant BCD digits, half-up. Models the
      reference evaluating the angle in SINGLE precision -- measured by
      ctl_card_r95 (1.5707963 vs pi/2 differ by 3e-8; the reference keeps the
      axis point, so it cannot be resolving that difference).
  P2  q  = fp_mul(theta6, C14)  where C14 = 4/pi at 14 BCD digits
  P3  o  = flt_to_int16(q)                       (raw octant count, unmasked)
  P4  f  = fp_sub(q, o)                          (fraction into the octant)
  P5  u  = flt_to_int16(fp_mul(f, 16384))        (u in 1/16384 octant)
      marshal (o, u) int16+int16 per boundary -- replaces (brad, sign_c, sign_s)

  G1  M  = (r * 46341) >> 16                     = floor(r/sqrt(2)), verified
                                                   exhaustively below
  G2  OM[o] = o*M for o=0..7                     (eight 24-bit adds, once)
  G3  pos_b = (u * M) >> 14                      (gfx_mul16u32, once per bound)
      g_b   = OM[o&7] + pos_b                    (24-bit)
      span  = (g_e - g_s) mod 8M; if g_s==g_e and raw (o,u) differ -> span = 8M
  G4  per emitted mirror point: octant is STATIC per mirror, step is qx (the
      loop counter, always min(|dx|,|dy|)):
          pos = qx (even octant) or M - qx (odd)
          gp  = OM[o] + pos
          keep iff (gp - g_s) mod 8M <= span     (24-bit sub/cmp -- replaces
                                                  four 16x16->32 multiplies
                                                  and two 32-bit compares)
  G5  spoke endpoint = the octant point at the boundary: walk the midpoint
      loop to step k_b, map by the static octant table. Replaces the QTAB
      boundary vector -- and the round-3 capture says the reference's spoke
      at -0.01 lands on (15,0), the octant point, where the nudged QTAB
      vector lands on (15,-1).

    python3 -u scratchpad/arcmask_asmsim2.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, getcontext

import arcmask_model as AM
from circovf_calib import W, H, octant, mirrors, plane, reduce_plane

HERE = os.path.dirname(os.path.abspath(__file__))
getcontext().prec = 40

TAU = 2 * math.pi

# 4/pi to 14 significant BCD digits (round: ...3516... -> ...352)
C14 = Decimal("1.2732395447352")


def bcd6(x: float) -> Decimal:
    """P1 -- round to 6 significant decimal digits, half-up."""
    if x == 0:
        return Decimal(0)
    d = Decimal(repr(x))
    q = Decimal(1).scaleb(d.adjusted() - 5)
    return d.quantize(q, rounding=ROUND_HALF_UP)


def fp14(d: Decimal, rounding=ROUND_DOWN) -> Decimal:
    """A 14-significant-digit BCD result (mathpack width)."""
    if d == 0:
        return Decimal(0)
    q = Decimal(1).scaleb(d.adjusted() - 13)
    return d.quantize(q, rounding=rounding)


def marshal(theta: float):
    """P1..P5 -> (o_raw, u14). theta is |angle| as the resident hands it over."""
    q = fp14(bcd6(theta) * C14)                     # P2
    o = int(q)                                      # P3 (trunc)
    f = q - o                                       # P4 (exact BCD subtract)
    u = int(fp14(f * 16384))                        # P5 (trunc)
    return o, u


def mmax_asm(r: int) -> int:
    """G1 -- floor(r/sqrt(2)), exactly, with tenant-runnable ops.

    46341/65536 > 1/sqrt(2), so the multiply's floor can only ever OVERSHOOT
    the true floor, and by at most 1 (error <= r*7.6e-7 < 0.025). One exact
    correction closes it: M is right iff 2*M*M <= r*r  (both fit 32 bits;
    gfx_mul16u32 + gfx_cmp32 are already in the tenant)."""
    m = (r * 46341) >> 16
    if 2 * m * m > r * r:
        m -= 1
    return m


# static octant + parity per mirror position, keyed the way gco_emit8 emits:
# (sign pattern, swapped) -> (octant, parity). parity 0: pos=qx; 1: pos=M-qx.
# screen offsets, BASIC angle = atan2(-sy, sx).
def mirror8(qx, qy):
    """The 8 mirrors WITH their static octant/parity, matching gco_emit8."""
    return (
        ((qy, -qx), 0, 0), ((qx, -qy), 1, 1), ((-qx, -qy), 2, 0),
        ((-qy, -qx), 3, 1), ((-qy, qx), 4, 0), ((-qx, qy), 5, 1),
        ((qx, qy), 6, 0), ((qy, qx), 7, 1),
    )


def octant_pt(k, r):
    """G5 -- the (qx, qy) of octant step k (a bare midpoint walk)."""
    last = None
    for qx, qy in octant(r):
        last = (qx, qy)
        if qx == k:
            return qx, qy
    return last                     # k beyond the walk -> its last point


def draw_asm(cx, cy, r, asps=256, aspmaj=0, start=None, end=None,
             sneg=False, eneg=False):
    arcf = start is not None or end is not None
    if arcf:
        M = mmax_asm(r)
        T = 8 * M
        os_, us = marshal(abs(start or 0.0))
        oe_, ue = marshal(abs(end or 0.0))
        ps, pe = (us * M) >> 14, (ue * M) >> 14      # G3, mul16u32 shape
        gs = (os_ & 7) * M + ps
        ge = (oe_ & 7) * M + pe
        span = (ge - gs) % T if T else 0
        if gs == ge and (os_, us) != (oe_, ue):
            span = T                                  # the full-wrap case
    px = set()
    for qx, qy in octant(r):
        for (sx, sy), o, par in mirror8(qx, qy):
            if arcf:
                pos = qx if par == 0 else M - qx
                gp = o * M + pos
                if T == 0 or (gp - gs) % T > span:
                    continue
            if aspmaj:
                sx = AM.circ_scale(sx, asps)
            else:
                sy = AM.circ_scale(sy, asps)
            x, y = cx + sx, cy + sy
            if 0 <= x < W and 0 <= y < H:
                px.add((x, y))
    if arcf:
        for want, (o, p) in ((sneg, (os_ & 7, ps)), (eneg, (oe_ & 7, pe))):
            if not want or M == 0:
                continue
            k = p if o % 2 == 0 else M - p
            qq = octant_pt(k, r)
            if qq is None:
                continue
            for (vx, vy), oo, par in mirror8(*qq):
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


def main():
    print("=== D-ARCMASK: the integer pipeline, simulated ===\n")

    # G1 exhaustive: the multiply must BE floor(r/sqrt(2)) on the whole domain
    bad = [r for r in range(32768) if mmax_asm(r) != int(r / math.sqrt(2))]
    print(f"G1  M=(r*46341)>>16 vs floor(r/sqrt2), r in 0..32767: "
          f"{len(bad)} mismatches" + (f"  🔴 {bad[:8]}" if bad else "  -- EXACT"))

    # the 54 banked planes
    import arcmask_refmodel2 as R2
    rows = R2.corpus()
    ok = 0
    misses = []
    for lbl, kw, want, zb in rows:
        got = reduce_plane(plane(draw_asm(**kw)))
        hit = got[2] == want[2] and got[0] == want[0]
        ok += hit
        if not hit:
            misses.append((lbl, got, want))
    print(f"\nplanes: {ok}/{len(rows)} whole 6144-byte planes exact "
          f"(float model: 53/54)")
    for lbl, got, want in misses:
        print(f"  MISS {lbl:22} sim={got[0]:4} {got[2]}  ref={want[0]:4} {want[2]}")

    # r=15 gate captures
    D = json.load(open(os.path.join(HERE, "g4_pointsets.json")))
    B = json.load(open(os.path.join(HERE, "g4_arc_boundary_capture.json")))
    r15 = 0
    for lbl, kw in (("arc_0_hpi", dict(cx=60, cy=60, r=15, start=0, end=1.57)),
                    ("arc_hpi_pi", dict(cx=60, cy=60, r=15, start=1.57, end=3.14)),
                    ("arc_wrap", dict(cx=60, cy=60, r=15, start=3, end=1)),
                    ("arc_full628", dict(cx=60, cy=60, r=15, start=0, end=6.28))):
        want = {tuple(p) for p in D[lbl]["pts"]}
        got = draw_asm(**kw)
        r15 += got == want
        if got != want:
            print(f"  🔴 r15 MISS {lbl}: symdiff {sorted(got ^ want)[:6]}")
    sweep = all(((61, 45) in draw_asm(cx=60, cy=60, r=15, start=float(v["a0"]),
                                      end=3.14)) == v["present"]
                for v in B["round2"].values())
    print(f"r=15 point sets: {r15}/4    near-cardinal sweep: "
          f"{'OK' if sweep else '🔴 MISS'}")

    # round3: the reference's spoke at -0.01 hits (75,60)
    got = draw_asm(cx=60, cy=60, r=15, start=-0.01, end=1.57, sneg=True)
    print(f"round3 spoke at -0.01 reaches (75,60): "
          f"{'YES -- matches the reference' if (75, 60) in got else '🔴 NO'} "
          f"(zerobas today draws to (75,59): "
          f"{'also hits' if (75, 59) in got else 'sim does not'})")

    # spokes that ARE gate-green today must stay identical: spoke_270/wedge2
    import arcmask_model as AMM
    same = True
    for th, r in ((1.57, 15), (0.1, 15), (1.57, 400)):
        rb, sc, ss = AMM.boundary_prep(th)
        bv = AMM.bvec(rb, sc, ss, r, 256, 0)
        o, u = marshal(th)
        M = mmax_asm(r)
        p = (u * M) >> 14
        k = p if (o & 7) % 2 == 0 else M - p
        qq = octant_pt(k, r)
        for (vx, vy), oo, par in mirror8(*qq):
            if oo == (o & 7):
                break
        tag = "SAME" if (vx, vy) == bv else f"DIFFERS  bvec={bv} octpt={(vx, vy)}"
        same = same and (vx, vy) == bv
        print(f"spoke endpoint |theta|={th} r={r}: {tag}")
    print("\n=== verdict: " + ("PIPELINE EXACT -- ready to price"
                               if ok == 53 and r15 == 4 and sweep and not bad
                               else "REFUTED -- do not build") + " ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
