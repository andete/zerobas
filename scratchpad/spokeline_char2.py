#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SPOKELINE step 2 -- the CLAMP'S SCOPE, with a line model that is actually
the tenant's.

Round 1 (spokeline_char.py) measured:
  * the reference matches "clamp the endpoint, then draw" on ALL 8 rows --
    all four screen edges, the wide-slope row, and plain LINE with the same
    geometry (`line_bare` cd7e5368): THE CLAMP IS NOT THE SPOKE PATH'S, IT IS
    THE LINE'S.
  * the two "ZEROBAS != MODEL" flags were the MODEL's error, not the rig's:
    both machines agree on those rows, on the seam my python called
    "reversed". gfx_bres_init SORTS SO THE MAJOR AXIS ASCENDS (sub/graphics
    .asm) -- the direction was never a divergence; my convention was wrong.

So this round: a faithful zline() (major-ascending, ERR=DMAJ>>1, 45-degree =
x-major), CALIBRATED against every banked round-1 plane before predicting
anything; then rows that separate WHICH endpoints clamp:
  * both-off diagonal    -- clamp-BOTH vs clamp-END-ONLY diverge visibly
  * fully-off corner     -- clamp draws 1 px at (255,191); clip draws nothing
  * start-off rows       -- does the FIRST endpoint clamp? (three edges)
  * spoke-start rows     -- does the spoke's start (the CENTRE) clamp?
  * G3 revisit           -- clip_frac re-measured with the band that can see

    python3 -u scratchpad/spokeline_char2.py [--dry|--calib]
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, HERE)

from arcmask_verify import draw_pair                    # noqa: E402
from spokeline_char import spoke_endpoint, clamp_pt     # noqa: E402
from circovf_calib import W, H, plane, reduce_plane     # noqa: E402

LINIT = "COLOR15,4,7:SCREEN2"
PLANE = [(0, 6144)]
OUT = os.path.join(HERE, "spokeline_char2.json")

# D-DRAWCLAMP: REFUSE TO CLOBBER A BANK. This probe's own pre-fix planes were
# overwritten by its post-fix verification re-run (D-SPOKELINE §6) -- the
# measurement a whole slice rested on, gone to a second `python3 ...` with no
# argument. Pass --force to overwrite deliberately, or --out NAME to version it.

def bank_guard(path):
    import sys as _s
    if os.path.exists(path) and "--force" not in _s.argv:
        print(f"REFUSING to overwrite an existing bank: {path}\n"
              "  pass --force to overwrite, or --out NAME.json to version it")
        raise SystemExit(3)


def zline(x1, y1, x2, y2):
    """gfx_bres_init/next, faithfully: major axis ascends (start from p2 when
    the major delta is negative), DMAJ/DMIN, ERR = DMAJ>>1, err -= DMIN per
    major step, borrow -> err += DMAJ and step the minor. 45 deg = x-major."""
    adx, ady = abs(x2 - x1), abs(y2 - y1)
    steep = ady > adx
    if steep:
        if y2 < y1:
            x1, y1, x2, y2 = x2, y2, x1, y1
        dmaj, dmin = ady, adx
        smin = 0 if x2 == x1 else (1 if x2 > x1 else -1)
    else:
        if x2 < x1:
            x1, y1, x2, y2 = x2, y2, x1, y1
        dmaj, dmin = adx, ady
        smin = 0 if y2 == y1 else (1 if y2 > y1 else -1)
    err = dmaj >> 1
    cx, cy = x1, y1
    pts = [(cx, cy)]
    for _ in range(dmaj):
        if steep:
            cy += 1
        else:
            cx += 1
        err += dmin                          # gfx_bres_next: accumulate, and
        if err >= dmaj:                      # step the minor at err >= dmaj
            err -= dmaj
            if steep:
                cx += smin
            else:
                cy += smin
        pts.append((cx, cy))
    return pts


def vis(pts):
    return {(x, y) for x, y in pts if 0 <= x < W and 0 <= y < H}


def line_h(x1, y1, x2, y2, mode):
    """clamp-scope hypotheses."""
    if mode == "clip":
        return vis(zline(x1, y1, x2, y2))
    if mode == "clamp_end":
        fx, fy = clamp_pt(x2, y2)
        return vis(zline(x1, y1, fx, fy))
    ax, ay = clamp_pt(x1, y1)
    bx, by = clamp_pt(x2, y2)
    return vis(zline(ax, ay, bx, by))            # clamp_both


HYPS = ("clamp_both", "clamp_end", "clip")


def calibrate():
    """zline + clamp_end must reproduce every banked round-1 plane."""
    import spokeline_char as R1
    data = json.load(open(os.path.join(HERE, "spokeline_char.json")))
    ok = bad = 0
    for lbl, ops, kw, spoke, why in R1.CASES:
        if kw is None and spoke != "LINE":
            continue
        if spoke == "LINE":
            base, (cx, cy), (ex, ey) = set(), (128, 96), (129, -304)
        else:
            theta, r = spoke
            kw2 = dict(kw)
            kw2["sneg"] = False
            base = draw_pair(**kw2)
            vx, vy = spoke_endpoint(theta, r)
            cx, cy = kw["cx"], kw["cy"]
            ex, ey = cx + vx, cy + vy
        for who, mode in (("zb", "clip"), ("ref", "clamp_end")):
            want = reduce_plane(bytes.fromhex(data[lbl][who]))
            got = reduce_plane(plane(base | line_h(cx, cy, ex, ey, mode)))
            good = got == want
            ok += good
            bad += not good
            if not good:
                print(f"  MISS {lbl}/{who}: model {got[0]} {got[2]} "
                      f"vs measured {want[0]} {want[2]}")
    print(f"calibration: {ok} exact / {bad} missed of {ok + bad} banked planes")
    return bad


# label, ops, (x1,y1,x2,y2) for LINE rows or ("spoke", arc-kwargs, theta, r),
# why
CASES = [
    ("dead_nocircle", "PSET(10,10),15", None, "⭐ DEAD SUBJECT."),
    ("ctl_line_on", "LINE(10,20)-(200,150),15", (10, 20, 200, 150),
     "GREEN CONTROL: fully on screen, every hypothesis coincides -- a rig row."),
    ("both_off_diag", "LINE(-50,-50)-(305,241),15", (-50, -50, 305, 241),
     "⭐ WHICH ENDPOINTS: clamp-BOTH -> (0,0)-(255,191); clamp-END ->"
     " (-50,-50)-(255,191); clip -> the true diagonal. Three planes."),
    ("alloff_corner", "LINE(300,300)-(400,400),15", (300, 300, 400, 400),
     "⭐ fully off screen: clamp lights (255,191); clip lights NOTHING. G3's "
     "clip_alloff row captured the top-left band and could not see this."),
    ("start_off_L", "LINE(-40,20)-(100,80),15", (-40, 20, 100, 80),
     "start off the LEFT edge: does the FIRST endpoint clamp?"),
    ("start_off_R", "LINE(300,20)-(100,80),15", (300, 20, 100, 80),
     "start off the RIGHT edge."),
    ("start_off_B", "LINE(50,250)-(120,100),15", (50, 250, 120, 100),
     "start off the BOTTOM edge."),
    ("g3_frac_rev", "LINE(-7,-2)-(60,18),15", (-7, -2, 60, 18),
     "G3's clip_frac geometry, re-scored against the clamp hypotheses -- was "
     "its green ever discriminating?"),
    ("spoke_start_T", "CIRCLE(128,-60),200,15,-4.71,0",
     ("spoke", dict(cx=128, cy=-60, r=200, start=-4.71, end=0), 4.71, 200),
     "⭐ the spoke's START is the CENTRE, off the TOP: does the reference "
     "clamp the start of its internal line too?"),
    ("spoke_start_L", "CIRCLE(-60,96),200,15,-6.28,0",
     ("spoke", dict(cx=-60, cy=96, r=200, start=-6.28, end=0), 6.28, 200),
     "spoke start off the LEFT."),
]


def predictions():
    preds = {}
    for lbl, ops, geo, why in CASES:
        if geo is None:
            preds[lbl] = None
            continue
        if isinstance(geo, tuple) and geo and geo[0] == "spoke":
            _, kw, theta, r = geo
            kw2 = dict(kw)
            kw2["sneg"] = False
            base = draw_pair(**kw2)
            vx, vy = spoke_endpoint(theta, r)
            x1, y1 = kw["cx"], kw["cy"]
            x2, y2 = x1 + vx, y1 + vy
        else:
            base = set()
            x1, y1, x2, y2 = geo
        p = {h: reduce_plane(plane(base | line_h(x1, y1, x2, y2, h)))
             for h in HYPS}
        preds[lbl] = (p, (x1, y1, x2, y2))
    return preds


def main():
    if "--nocalib" not in sys.argv:
        print("--- calibrating zline against the banked round-1 planes ---")
        if calibrate():
            print("=== zline model REFUTED -- fix it before measuring ===")
            return 2
        print()
    preds = predictions()
    print("=== D-SPOKELINE round 2: the clamp's scope ===\n")
    for lbl, ops, geo, why in CASES:
        if preds[lbl] is None:
            print(f"  {lbl:14} {ops}   (rig row)")
            continue
        p, g = preds[lbl]
        distinct = len({v[2] for v in p.values()})
        print(f"  {lbl:14} {ops}   line={g}")
        for h in HYPS:
            print(f"      {h:10} {p[h]}")
        print(f"      DISCRIMINATING POWER: {distinct}"
              f"{'  ⚠️ VACUOUS' if distinct == 1 else ''}")
        print(f"      why: {why}")
    if "--dry" in sys.argv:
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
    for lbl, ops, geo, why in CASES:
        rh, zh = run(REF, ops), run(ZB, ops)
        rr, zz = red(rh), red(zh)
        out[lbl] = dict(ops=ops, ref=rh, zb=zh)
        names = [h for h in HYPS
                 if preds[lbl] and rr and preds[lbl][0][h][2] == rr[2]]
        flag = ""
        if preds[lbl] and zz and zz[2] != preds[lbl][0]["clip"][2]:
            zmiss += 1
            flag = "  🔴 ZEROBAS != MODEL"
        v = "agree" if rr == zz else "DIFF "
        print(f"  {v} {lbl:14} ref={rr}  matches: {names or 'NONE'}{flag}")
        print(f"        zb ={zz}")
    bank_guard(OUT)
    with open(OUT, "w") as f:
        json.dump(out, f)
    print(f"\n=== zerobas-model misses: {zmiss};  planes -> {OUT} ===")
    return 1 if zmiss else 0


if __name__ == "__main__":
    sys.exit(main())
