#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SPOKELINE step 3 -- do BOXES clamp too? (the fix's scope)

Round 2 pinned the rule for SEGMENTS: the reference clamps BOTH endpoints to
the screen before rasterising (clamp_both unique on six rows; a fully-off
LINE lights (255,191)). gfx_line_op also serves box outline and box fill:

  * BOX FILL is clamp-INVARIANT by construction -- the visible fill of a
    rectangle IS the fill of the clamped rectangle -- so it needs no row and
    can take the same clamp for free.
  * BOX OUTLINE is not: a clamped off-screen edge DRAWS AT THE CLAMP LINE
    (left edge at x=0) where a clipped one is invisible. Two rows decide.

DRAW is out of scope either way: gdrw calls gfx_draw_seg directly, bypassing
gfx_line_op -- its off-screen behaviour is unmeasured and stays unchanged.

    python3 -u scratchpad/spokeline_char3.py [--dry]
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, HERE)

from spokeline_char import clamp_pt                     # noqa: E402
from spokeline_char2 import zline, vis                  # noqa: E402
from circovf_calib import plane, reduce_plane           # noqa: E402

LINIT = "COLOR15,4,7:SCREEN2"
PLANE = [(0, 6144)]
OUT = os.path.join(HERE, "spokeline_char3.json")


def box_outline(x1, y1, x2, y2):
    """gfx_box_outline: four segments between the corners."""
    pts = set()
    for a, b in (((x1, y1), (x2, y1)), ((x1, y2), (x2, y2)),
                 ((x1, y1), (x1, y2)), ((x2, y1), (x2, y2))):
        pts |= set(zline(a[0], a[1], b[0], b[1]))
    return pts


def box_h(x1, y1, x2, y2, mode):
    if mode == "clip":
        return vis(box_outline(x1, y1, x2, y2))
    if mode == "clamp_corners":
        ax, ay = clamp_pt(x1, y1)
        bx, by = clamp_pt(x2, y2)
        return vis(box_outline(ax, ay, bx, by))
    # clamp_per_edge: each of the four segments clamps ITS OWN endpoints --
    # identical to clamp_corners for an axis-aligned box, kept as a check
    pts = set()
    for a, b in (((x1, y1), (x2, y1)), ((x1, y2), (x2, y2)),
                 ((x1, y1), (x1, y2)), ((x2, y1), (x2, y2))):
        (ax, ay), (bx, by) = clamp_pt(*a), clamp_pt(*b)
        pts |= set(zline(ax, ay, bx, by))
    return vis(pts)


HYPS = ("clamp_corners", "clamp_per_edge", "clip")

CASES = [
    ("dead_nocircle", "PSET(10,10),15", None, "⭐ DEAD SUBJECT."),
    ("box_on", "LINE(30,30)-(120,90),15,B", (30, 30, 120, 90),
     "GREEN CONTROL: on-screen box, all hypotheses coincide."),
    ("box_off_L", "LINE(-40,20)-(100,80),15,B", (-40, 20, 100, 80),
     "⭐ TL corner off-left: clamp draws the LEFT EDGE at x=0; clip has no "
     "left edge at all."),
    ("box_alloff", "LINE(300,300)-(400,400),15,B", (300, 300, 400, 400),
     "fully off: clamp -> a 1-px 'box' at (255,191); clip -> nothing."),
]


def predictions():
    preds = {}
    for lbl, ops, geo, why in CASES:
        if geo is None:
            preds[lbl] = None
            continue
        x1, y1, x2, y2 = geo
        preds[lbl] = {h: reduce_plane(plane(box_h(x1, y1, x2, y2, h)))
                      for h in HYPS}
    return preds


def main():
    preds = predictions()
    print("=== D-SPOKELINE round 3: box outlines ===\n")
    for lbl, ops, geo, why in CASES:
        if preds[lbl] is None:
            print(f"  {lbl:12} {ops}   (rig row)")
            continue
        p = preds[lbl]
        distinct = len({v[2] for v in p.values()})
        print(f"  {lbl:12} {ops}")
        for h in HYPS:
            print(f"      {h:14} {p[h]}")
        print(f"      DISCRIMINATING POWER: {distinct}"
              f"{'  ⚠️ VACUOUS' if distinct == 1 else ''}")
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
                 if preds[lbl] and rr and preds[lbl][h][2] == rr[2]]
        flag = ""
        if preds[lbl] and zz and zz[2] != preds[lbl]["clip"][2]:
            zmiss += 1
            flag = "  🔴 ZEROBAS != MODEL"
        v = "agree" if rr == zz else "DIFF "
        print(f"  {v} {lbl:12} ref={rr}  matches: {names or 'NONE'}{flag}")
        print(f"        zb ={zz}")
    with open(OUT, "w") as f:
        json.dump(out, f)
    print(f"\n=== zerobas-model misses: {zmiss};  planes -> {OUT} ===")
    return 1 if zmiss else 0


if __name__ == "__main__":
    sys.exit(main())
