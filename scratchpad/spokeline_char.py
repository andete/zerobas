#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SPOKELINE step 1 -- characterize the reference's off-screen spoke line.

The residual: `arc_big_r400`'s spoke differs, ref bbox (128,0,129,96) vs ours
(128,0,128,96). Solved OFFLINE against the banked sha1: the reference's plane
`cd7e5368` is reproduced byte for byte by

    clamp the endpoint to the screen  (129,-304) -> (129,0)
    draw the line ENDPOINT -> CENTRE  (the reversed Bresenham seam)

and by NOTHING else tried: per-pixel clip of the true line cannot put column
129 on screen at all (crossover at y=-104), and the same clamped line drawn
centre->endpoint seams one row off (9ec5a88b != cd7e5368).

⚠️ THAT IS ONE PLANE CARRYING TWO CLAIMS, AND THREE SCREEN EDGES ARE
UNMEASURED. This probe separates them:

  * `tie_r90`     -- an ON-SCREEN spoke whose major axis is even (dy=90), so
                     the Bresenham TIE seams differently per direction, with
                     no clamping involved: the DIRECTION claim alone.
  * `top_wide`    -- a top-edge spoke whose clamp changes the slope by 80+
                     columns: clamp-vs-clip is unmissable, direction second.
  * `top_r400`    -- the original row, replicated in this batch.
  * `bot_r400` / `right_r400` / `left_r400` -- the three unmeasured edges.
  * `line_bare`   -- plain LINE with the SAME geometry as top_r400's spoke.
                     G3's clip rows are green, so if the reference clamps
                     here too the clamp is in LINE; if it clips, the clamp is
                     the SPOKE PATH's alone and the fix must not touch LINE.

Every row carries an exact zerobas prediction (rig guard) and per-hypothesis
reference predictions with a discriminating-power check -- a row whose
hypotheses all predict one plane is vacuous and says so.

    python3 -u scratchpad/spokeline_char.py [--dry]
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, HERE)

import arcmask_model as AM                              # noqa: E402
from arcmask_verify import draw_pair, marshal15         # noqa: E402
import arcmask_asmsim2 as A                             # noqa: E402
from circovf_calib import W, H, plane, reduce_plane     # noqa: E402

LINIT = "COLOR15,4,7:SCREEN2"
PLANE = [(0, 6144)]
OUT = os.path.join(HERE, "spokeline_char.json")


def clamp_pt(x, y):
    return max(0, min(W - 1, x)), max(0, min(H - 1, y))


def spoke_endpoint(theta, r):
    """The shipped endpoint: the octant point at the boundary (pre-scale,
    ASPS=256 rows only here)."""
    o, u = marshal15(abs(theta))
    M = A.mmax_asm(r)
    p = (u * M) >> 14
    k = p if (o & 7) % 2 == 0 else M - p
    qq = A.octant_pt(k, r)
    for (vx, vy), oo, par in A.mirror8(*qq):
        if oo == (o & 7):
            return vx, vy


def vis(pts):
    return {(x, y) for x, y in pts if 0 <= x < W and 0 <= y < H}


def spoke_h(cx, cy, ex, ey, mode):
    """The four spoke-line hypotheses."""
    if mode == "clip_fwd":                       # zerobas today
        return vis(AM.bres_line(cx, cy, ex, ey))
    if mode == "clip_rev":
        return vis(AM.bres_line(ex, ey, cx, cy))
    fx, fy = clamp_pt(ex, ey)
    if mode == "clamp_fwd":
        return vis(AM.bres_line(cx, cy, fx, fy))
    return vis(AM.bres_line(fx, fy, cx, cy))     # clamp_rev -- the candidate


HYPS = ("clamp_rev", "clamp_fwd", "clip_rev", "clip_fwd")

# label, ops, arc kwargs (for the zerobas/base plane), spoke (theta, r) or a
# bare-LINE endpoint pair, why
CASES = [
    ("dead_nocircle", "PSET(10,10),15", None, None,
     "⭐ DEAD SUBJECT first."),
    ("ctl_onscreen", "CIRCLE(128,96),95,15,-1.1,0",
     dict(cx=128, cy=96, r=95, start=-1.1, end=0, sneg=True), (1.1, 95),
     "GREEN CONTROL: fully on-screen spoke, no clamp, no tie -- all four "
     "hypotheses must coincide with the measured-green behaviour."),
    ("tie_r90", "CIRCLE(128,96),90,15,-1.565,0",
     dict(cx=128, cy=96, r=90, start=-1.565, end=0, sneg=True), (1.565, 90),
     "⭐ THE DIRECTION CLAIM ALONE: endpoint (1,-90) on screen, major axis "
     "90 (even) -> the Bresenham tie seams at y=51 (fwd) vs y=50 (rev), no "
     "clamping anywhere."),
    ("top_r400", "CIRCLE(128,96),400,15,-1.57,0",
     dict(cx=128, cy=96, r=400, start=-1.57, end=0, sneg=True), (1.57, 400),
     "the original residual row, replicated in this batch."),
    ("top_wide", "CIRCLE(128,96),400,15,-1.8,0",
     dict(cx=128, cy=96, r=400, start=-1.8, end=0, sneg=True), (1.8, 400),
     "⭐ THE CLAMP CLAIM, LOUD: endpoint (46,-295); clamp -> (46,0) redraws "
     "the slope by ~20 columns vs clip's exit at x~108."),
    ("bot_r400", "CIRCLE(128,96),400,15,-4.71,0",
     dict(cx=128, cy=96, r=400, start=-4.71, end=0, sneg=True), (4.71, 400),
     "the BOTTOM edge, unmeasured until now."),
    ("right_r400", "CIRCLE(128,96),400,15,-.1,0",
     dict(cx=128, cy=96, r=400, start=-0.1, end=0, sneg=True), (0.1, 400),
     "the RIGHT edge: endpoint (526,61), clamp x -> 255."),
    ("left_r400", "CIRCLE(128,96),400,15,-3.14,0",
     dict(cx=128, cy=96, r=400, start=-3.14, end=0, sneg=True), (3.14, 400),
     "the LEFT edge: endpoint (-272,95), clamp x -> 0."),
    ("line_bare", "LINE(128,96)-(129,-304),15", None, "LINE",
     "⭐ plain LINE, the SAME geometry as top_r400's spoke. Decides whether "
     "the clamp is LINE's or the spoke path's."),
]


def predictions():
    preds = {}
    for lbl, ops, kw, spoke, why in CASES:
        if kw is None and spoke != "LINE":
            preds[lbl] = None
            continue
        if spoke == "LINE":
            base = set()
            ex, ey = 129, -304
            cx, cy = 128, 96
        else:
            theta, r = spoke
            kw2 = dict(kw)
            kw2["sneg"] = False           # arc WITHOUT the spoke = the base
            base = draw_pair(**kw2)
            vx, vy = spoke_endpoint(theta, r)
            cx, cy = kw["cx"], kw["cy"]
            ex, ey = cx + vx, cy + vy
        p = {h: reduce_plane(plane(base | spoke_h(cx, cy, ex, ey, h)))
             for h in HYPS}
        preds[lbl] = (p, (ex, ey))
    return preds


def main():
    preds = predictions()
    print("=== D-SPOKELINE: the off-screen spoke line, hypotheses first ===\n")
    for lbl, ops, kw, spoke, why in CASES:
        if preds[lbl] is None:
            print(f"  {lbl:13} {ops}   (rig row)")
            continue
        p, (ex, ey) = preds[lbl]
        distinct = len({v[2] for v in p.values()})
        print(f"  {lbl:13} {ops}   endpoint=({ex},{ey})")
        for h in HYPS:
            print(f"      {h:9} {p[h]}")
        print(f"      DISCRIMINATING POWER: {distinct} distinct planes"
              f"{'  ⚠️ VACUOUS ROW' if distinct == 1 else ''}")
        print(f"      why: {why}")
    if "--dry" in sys.argv:
        print("\n--dry: predictions only")
        return 0

    import omsx_repl                                    # noqa: E402
    REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
    ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                        "C-BIOS_MSX1_EU_REPACK_DISK")

    def prog(stmts):
        return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]

    def run(machine, ops):
        specs = [("stored", prog([LINIT, ops]))]
        return omsx_repl.run_cases(machine, specs, batch=False,
                                   capture=("vram_segs", PLANE), step=15.0)[0]

    def red(hexs):
        if not hexs:
            return None
        b = bytes.fromhex(hexs)
        return ("SHORT", len(b), None) if len(b) != 6144 else reduce_plane(b)

    print(f"\n--- MEASURED  ref={REF}  zb={ZB} ---")
    out, zmiss = {}, 0
    for lbl, ops, kw, spoke, why in CASES:
        rh, zh = run(REF, ops), run(ZB, ops)
        rr, zz = red(rh), red(zh)
        out[lbl] = dict(ops=ops, ref=rh, zb=zh)
        names_r = [h for h in HYPS
                   if preds[lbl] and preds[lbl][0][h][2] == (rr or ("", "", ""))[2]]
        flag = ""
        if preds[lbl] and zz and zz[2] != preds[lbl][0]["clip_fwd"][2]:
            zmiss += 1
            flag = "  🔴 ZEROBAS != MODEL -- RIG SUSPECT"
        v = "agree" if rr == zz else "DIFF "
        print(f"  {v} {lbl:13} ref={rr}  matches: {names_r or 'NONE'}{flag}")
        print(f"        zb ={zz}")
    with open(OUT, "w") as f:
        json.dump(out, f)
    print(f"\n=== zerobas misses: {zmiss};  planes -> {OUT} ===")
    return 1 if zmiss else 0


if __name__ == "__main__":
    sys.exit(main())
