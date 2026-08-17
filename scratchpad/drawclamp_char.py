#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DRAWCLAMP part B -- DOES THE CLAMP COVER `DRAW`?

D-SPOKELINE measured, on 23 whole-plane rows across all four edges, that the
VG-8020 CLAMPS BOTH endpoints of every LINE to the screen (X->0..255,
Y->0..191) and never clips the ideal line. `DRAW` was deliberately excluded:
`gdrw` calls `gfx_draw_seg` DIRECTLY, bypassing `gfx_line_op` and therefore
`gfx_clamp_coords`, so zerobas still per-pixel clips DRAW's segments.

⚠️ THE GATE'S EXISTING OFF-SCREEN DRAW ROW CANNOT SEE THIS. `clip_left`
(`PSET(5,5):DRAW"A0S4L100"`) is a HORIZONTAL segment, and for an axis-aligned
segment clamping the endpoint and clipping the ideal line produce THE SAME
PIXELS -- it is provably vacuous for this question, and it is scored here as
such rather than argued.

Hypotheses (a cursor model x a drawing model, collapsed to the four that can
differ):

    clip           cursor keeps the raw target, segments clip per pixel  <- zerobas
    clamp_both     cursor raw, BOTH endpoints clamp before rasterising   <- LINE's rule
    clamp_end      cursor raw, only the TARGET clamps
    curclamp_clip  cursor stores the CLAMPED target, segments still clip

Part A (drawclamp_wa.py) reads the cursor cell directly, so the cursor half is
measured, not inferred -- these four stay in play only until it lands.

    python3 -u scratchpad/drawclamp_char.py [--dry|--calib]
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, HERE)

from circovf_calib import W, H, plane, reduce_plane      # noqa: E402
from spokeline_char import clamp_pt, spoke_endpoint      # noqa: E402
from arcmask_verify import draw_pair                     # noqa: E402

LINIT = "COLOR15,4,7:SCREEN2"
PLANE = [(0, 6144)]
# ⚠️ VERSIONED BANK PATH -- D-SPOKELINE's third residual: a re-run probe that
# banks to a FIXED path overwrites its own pre-fix measurement. The phase is
# part of the filename, so a post-fix verification run cannot clobber this.
def bank_path(phase: str) -> str:
    return os.path.join(HERE, f"drawclamp_char.{phase}.json")


def zline(x1, y1, x2, y2):
    """gfx_bres_init/next, faithfully: major axis ascends (start from p2 when
    the major delta is negative), DMAJ/DMIN, ERR = DMAJ>>1, err += DMIN per
    major step, step the minor at err >= DMAJ. 45 deg = x-major."""
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
        err += dmin
        if err >= dmaj:
            err -= dmaj
            if steep:
                cx += smin
            else:
                cy += smin
        pts.append((cx, cy))
    return pts


def vis(pts):
    return {(x, y) for x, y in pts if 0 <= x < W and 0 <= y < H}


def seg_px(x1, y1, x2, y2, dmode):
    if dmode == "clip":
        return vis(zline(x1, y1, x2, y2))
    if dmode == "clamp_end":
        fx, fy = clamp_pt(x2, y2)
        return vis(zline(x1, y1, fx, fy))
    ax, ay = clamp_pt(x1, y1)
    bx, by = clamp_pt(x2, y2)
    return vis(zline(ax, ay, bx, by))


# hypothesis -> (cursor mode, drawing mode)
HYPS = {
    "clip":          ("raw", "clip"),
    "clamp_both":    ("raw", "clamp_both"),
    "clamp_end":     ("raw", "clamp_end"),
    "curclamp_clip": ("clamped", "clip"),
}


def calibrate():
    """zline + clamp_both must reproduce EVERY banked spokeline plane on BOTH
    machines. The banks are POST-FIX (2026-08-17 11:12-11:14), so after
    D-SPOKELINE both machines clamp -- which makes this a 2x-wide calibration
    of the very model this probe is about to predict DRAW with."""
    import spokeline_char2 as R2
    path = os.path.join(HERE, "spokeline_char2.json")
    if not os.path.exists(path):
        print("  no spokeline_char2.json bank -- CANNOT CALIBRATE")
        return 1
    data = json.load(open(path))
    ok = bad = skip = 0
    for lbl, ops, geo, why in R2.CASES:
        if geo is None or lbl not in data:
            skip += 1
            continue
        if isinstance(geo, tuple) and geo and geo[0] == "spoke":
            _, kw, theta, r = geo
            kw2 = dict(kw)
            kw2["sneg"] = False
            base = draw_pair(**kw2)
            x1, y1 = kw["cx"], kw["cy"]
            vx, vy = spoke_endpoint(theta, r)
            x2, y2 = x1 + vx, y1 + vy
        else:
            base, (x1, y1, x2, y2) = set(), geo
        want_px = plane(base | seg_px(x1, y1, x2, y2, "clamp_both"))
        got = reduce_plane(want_px)
        for who in ("ref", "zb"):
            hexs = data[lbl].get(who)
            if not hexs:
                skip += 1
                continue
            meas = reduce_plane(bytes.fromhex(hexs))
            good = meas == got
            ok += good
            bad += not good
            if not good:
                print(f"  MISS {lbl}/{who}: model {got[0]}px {got[2]} "
                      f"vs banked {meas[0]}px {meas[2]}")
    print(f"calibration: {ok} exact / {bad} missed of {ok + bad} banked planes"
          f"  ({skip} skipped)")
    return bad


# --- the rows -------------------------------------------------------------
# Each row: (label, ops, base pixels, segs(cursor_mode) -> [(x1,y1,x2,y2)], why)
#
# `segs` takes the cursor mode because a BLANK move off screen is where the two
# cursor models separate; rows whose cursor never leaves the screen ignore it.

def S(*segs):
    return lambda cmode: list(segs)


def cur(pt, cmode):
    return clamp_pt(*pt) if cmode == "clamped" else pt


def blank_then(bpt, tx, ty):
    """A BLANK move to an off-screen point, then a drawn move: the cursor model
    decides where the second segment STARTS."""
    return lambda cmode: [cur(bpt, cmode) + (tx, ty)]


CASES = [
    ("dead_nodraw", 'PSET(10,10),15', {(10, 10)}, S(),
     "⭐ DEAD SUBJECT: a program with NO DRAW in it. Every hypothesis predicts "
     "the bare marker; anything else is the rig, not the reference."),

    ("ctl_draw_on", 'PSET(20,20),15:DRAW"A0S4M100,80"', {(20, 20)},
     S((20, 20, 100, 80)),
     "GREEN CONTROL: a sloped DRAW fully on screen. All four hypotheses "
     "coincide -- it proves the rig draws a DRAW at all."),

    ("gate_clip_left", 'PSET(5,5),15:DRAW"A0S4L100"', {(5, 5)},
     S((5, 5, -95, 5)),
     "⭐ THE GATE'S OWN off-screen DRAW row, re-scored. Predicted VACUOUS: a "
     "HORIZONTAL segment clamps and clips to the same pixels. If this prints "
     "power 1, the gate has been green on this question while blind to it."),

    ("dm_off_r", 'PSET(10,100),15:DRAW"A0S4M300,20"', {(10, 100)},
     S((10, 100, 300, 20)),
     "⭐ absolute M target off the RIGHT edge, SLOPED so clamp redraws the slope."),

    ("dm_off_negy", 'PSET(100,100),15:DRAW"A0S4M20,-80"', {(100, 100)},
     S((100, 100, 20, -80)),
     "⭐ absolute M with a NEGATIVE y operand (the abs/rel switch reads operand "
     "ONE's sign, so this is still absolute)."),

    ("dm_off_b", 'PSET(40,20),15:DRAW"A0S4M200,400"', {(40, 20)},
     S((40, 20, 200, 400)),
     "⭐ absolute M off the BOTTOM."),

    ("dm_alloff", 'PSET(10,10),15:DRAW"A0S4BM300,300;M400,400"', {(10, 10)},
     blank_then((300, 300), 400, 400),
     "⭐ the DRAW analogue of `alloff_corner`: a segment ENTIRELY off screen. "
     "clamp lights (255,191); clip lights NOTHING. The marker keeps a blank "
     "plane from being read as a dead boot."),

    ("dm_start_off_R", 'PSET(10,10),15:DRAW"A0S4BM300,20;M100,80"', {(10, 10)},
     blank_then((300, 20), 100, 80),
     "⭐ the START off the right edge, target on screen: does DRAW's first "
     "endpoint clamp? (clamp_end degenerates to clip here -- by design.)"),

    ("dm_start_off_L", 'PSET(50,100),15:DRAW"A0S4BM-100,+0;M200,150"',
     {(50, 100)},
     blank_then((-50, 100), 200, 150),
     "⭐ the START off the LEFT edge, reached by a RELATIVE blank move (an "
     "absolute M cannot take a negative x -- a sign on operand one makes it "
     "relative)."),

    ("dm_both_off", 'PSET(0,0),15:DRAW"A0S4BM-50,-50;M305,241"', {(0, 0)},
     blank_then((-50, -50), 305, 241),
     "⭐ BOTH endpoints off, opposite corners -- the row where all four "
     "hypotheses can separate at once."),

    ("dm_rel_off", 'PSET(100,100),15:DRAW"A0S4M+300,-60"', {(100, 100)},
     S((100, 100, 400, 40)),
     "⭐ a RELATIVE M off screen: the relative path is scaled AND rotated "
     "before the target is formed, so it is a different route to the same "
     "question."),

    ("dm_scaled_off", 'PSET(100,100),15:DRAW"A0S16M+40,-20"', {(100, 100)},
     S((100, 100, 260, 20)),
     "⭐ TYPED vs TRANSFORMED: the operands (40,-20) are nowhere near a screen "
     "bound; only the SCALED delta (x4) puts the target at (260,20), 5 px off "
     "the right edge. If a clamp shows here it is clamping the TARGET."),

    ("dm_rot_off", 'PSET(100,100),15:DRAW"A1S4M+250,+40"', {(100, 100)},
     S((100, 100, 140, -150)),
     "⭐ the same question through ROTATION: A1 maps (dx,dy)->(dy,-dx), so the "
     "typed (250,40) becomes (40,-250) and the target lands at (140,-150) -- "
     "off the TOP, an edge the typed operands never mention."),

    ("dm_dir_diag", 'PSET(200,100),15:DRAW"A0S4E100"', {(200, 100)},
     S((200, 100, 300, 0)),
     "⭐ a DIRECTION LETTER off screen: E is (1,-1) scaled, so the ideal line "
     "is exactly 45 deg while the clamped one is y-major -- a large, "
     "unmistakable difference in shape."),

    ("dm_two_seg", 'PSET(30,30),15:DRAW"A0S4M300,60;M60,150"', {(30, 30)},
     lambda cmode: [(30, 30, 300, 60), cur((300, 60), cmode) + (60, 150)],
     "⭐ TWO segments: the first leaves the screen, the second comes back. The "
     "second segment's start is the cursor, so this row reads the clamp AND "
     "the cursor in one plane."),
]


def predictions():
    preds = {}
    for lbl, ops, base, segs, why in CASES:
        p = {}
        for h, (cmode, dmode) in HYPS.items():
            px = set(base)
            for s in segs(cmode):
                px |= seg_px(*s, dmode)
            p[h] = reduce_plane(plane(px))
        preds[lbl] = p
    return preds


def main() -> int:
    if "--nocalib" not in sys.argv:
        print("--- calibrating zline+clamp against the banked spokeline planes ---")
        if calibrate():
            print("=== MODEL REFUTED -- fix it before measuring ===")
            return 2
        print()
    preds = predictions()
    print("=== D-DRAWCLAMP part B: does the clamp cover DRAW? ===\n")
    live = 0
    for lbl, ops, base, segs, why in CASES:
        p = preds[lbl]
        distinct = len({v[2] for v in p.values()})
        live += distinct > 1
        print(f"  {lbl:16} {ops}")
        for h in HYPS:
            print(f"      {h:14} {p[h]}")
        print(f"      DISCRIMINATING POWER: {distinct}"
              f"{'  ⚠️ VACUOUS' if distinct == 1 else ''}")
        print(f"      why: {why}")
    print(f"\n  rows that can discriminate: {live} of {len(CASES)}")
    if "--dry" in sys.argv:
        return 0

    if "--phase" in sys.argv:
        phase = sys.argv[sys.argv.index("--phase") + 1]
    else:
        phase = "post" if "--post" in sys.argv else "pre"
    out = bank_path(phase)
    if os.path.exists(out) and "--force" not in sys.argv:
        print(f"REFUSING to overwrite an existing bank: {out}\n"
              "  (D-SPOKELINE's third residual -- pass --force or use --post)")
        return 3
    import omsx_repl  # noqa: E402
    REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
    ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                        "C-BIOS_MSX1_EU_REPACK_DISK")

    def prog(stmts):
        return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]

    def run(machine, ops):
        # ⚠️ the FIRST tuple element is the DELIVERY MODE, not a label.
        specs = [("stored", prog([LINIT, ops]))]
        return omsx_repl.run_cases(machine, specs, batch=False,
                                   capture=("vram_segs", PLANE), step=15.0)[0]

    def red(hexs):
        if not hexs:
            return None
        b = bytes.fromhex(hexs)
        return ("SHORT", len(b), None) if len(b) != 6144 else reduce_plane(b)

    print(f"\n--- MEASURED  ref={REF}  zb={ZB}  -> {os.path.basename(out)} ---")
    data, zmiss, diffs = {}, 0, 0
    for lbl, ops, base, segs, why in CASES:
        rh, zh = run(REF, ops), run(ZB, ops)
        rr, zz = red(rh), red(zh)
        data[lbl] = dict(ops=ops, ref=rh, zb=zh)
        names = [h for h in HYPS if rr and preds[lbl][h][2] == rr[2]]
        # THE RIG GUARD: zerobas must equal its OWN predicted hypothesis.
        flag = ""
        if zz and zz[2] != preds[lbl]["clip"][2]:
            zmiss += 1
            flag = "  🔴 ZEROBAS != MODEL"
        v = "agree" if rr == zz else "DIFF "
        diffs += rr != zz
        print(f"  {v} {lbl:16} ref={rr}  matches: {names or 'NONE'}{flag}")
        print(f"        zb ={zz}")
    with open(out, "w") as f:
        json.dump(data, f)
    print(f"\n=== DIFF rows: {diffs};  zerobas-model misses: {zmiss};"
          f"  planes -> {out} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
