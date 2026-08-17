#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARCMASK step 3 -- MEASURE the reference's boundary ray, many angles.

What the three §6.1 rows can and cannot say (arcmask_invert.py):

  * The reference's kept set IS a contiguous angular wedge -- inverted from
    its own plane hash, uniquely, at 170/170 px. So sharpening S/E CAN in
    principle reach it; the mask shape is not the problem.
  * At r=200 the reference's rays sit at BASIC angles ~1.129 and ~2.006 for a
    CIRCLE asking 1.1 and 2.04 -- both pulled IN toward pi/2, by 6.6% of the
    distance from pi/2, consistently on both ends.
  * That is ONE reading. Two rays is not a rule. `arc_r700_a137`'s only
    resolvable boundary is at 1.57, which is pi/2 to within the bracket, so it
    cannot see a shrink ABOUT pi/2 at all, and every r=15 row in the tree
    resolves 0.03 rad as 0.45 px -- under a pixel. The corpus is blind here.

So: sweep the angle. r=95 at (128,96) is the largest FULLY VISIBLE circle on a
256x192 screen, so both rays of every row are readable; the r-ladder rows ask
whether the error scales with the radius (angular) or not (a fixed offset).

⚠️ EVERY ROW CARRIES AN EXACT ZEROBAS PREDICTION (arcmask_model.py, calibrated
5/5 on whole planes). That is the RIG GUARD: a torn capture, a wrong delivery
mode, or a machine that dropped out of SCREEN 2 shows up as a zerobas MISS, not
as a reference finding. D-CIRCOVF's one-sided rig failure read as 8/8
divergence including all four controls; the first row here is a DEAD SUBJECT
with no CIRCLE in it at all.

Planes are dumped verbatim to arcmask_sweep.json so every later question is
answered offline, without re-booting anything.

    python3 -u scratchpad/arcmask_sweep.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, HERE)

import omsx_repl                                        # noqa: E402
import arcmask_model as M                               # noqa: E402
from circovf_calib import plane, reduce_plane           # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                    "C-BIOS_MSX1_EU_REPACK_DISK")
LINIT = "COLOR15,4,7:SCREEN2"
PLANE = [(0, 6144)]
OUT = os.path.join(HERE, "arcmask_sweep.json")

# label, BASIC ops, model kwargs (None = no CIRCLE at all), why
CASES = [
    ("dead_nocircle", "PSET(10,10),15", None,
     "⭐ DEAD SUBJECT, FIRST. No CIRCLE in the program at all. If this reads "
     "anything but one pixel on both machines, the rig is lying and every row "
     "below it is uninterpretable. D-CIRCOVF spent three tool calls "
     "discovering this after the fact."),
    ("ctl_full_r95", "CIRCLE(128,96),95,15", dict(cx=128, cy=96, r=95),
     "GREEN CONTROL: the same circle with NO arc field. Same rasteriser, same "
     "radius, mask disabled -- so a divergence here is the octant loop, not "
     "the mask, and every arc row below is uninterpretable."),
    ("ctl_arc_r15", "CIRCLE(60,60),15,15,0,1.57", dict(cx=60, cy=60, r=15,
                                                       start=0, end=1.57),
     "GREEN CONTROL: the gate's own arc_0_hpi row, verbatim. Pins that a "
     "large-radius finding is about the RADIUS and not about arcs as such."),
    ("ctl_card_r95", "CIRCLE(128,96),95,15,0,1.5707963", dict(cx=128, cy=96,
                                                              r=95, start=0,
                                                              end=1.5707963),
     "GREEN CONTROL at r=95 with CARDINAL boundaries, where QTAB is exact and "
     "any shrink about pi/2 is zero by construction. If this diverges the "
     "story is not angular resolution."),
]

# --- A. the angle sweep: both rays of every row are readable at r=95 -------
for _a, _b in [(0.2, 1.5), (0.5, 2.2), (0.8, 2.9), (1.1, 3.6), (1.4, 4.3),
               (1.8, 5.0), (2.4, 5.7), (2.75, 4.0), (4.7, 6.0), (0.35, 1.05)]:
    CASES.append((f"sw_{_a}_{_b}", f"CIRCLE(128,96),95,15,{_a},{_b}",
                  dict(cx=128, cy=96, r=95, start=_a, end=_b),
                  f"angle sweep: rays at {_a} and {_b} rad, r=95 fully visible"))

# --- B. the r-ladder: same angles, five radii. Angular error scales with r;
# a fixed pixel offset does not.
# ⚠️ cy MOVES WITH r. At (128,96) the r=190 row predicts a BLANK plane on both
# machines -- the whole 1.1..2.04 sector has |dy| >= 190*sin(1.1) = 169, off a
# 192-tall screen. Both-blank is not agreement (D-CIRCDOM §4.2), so the centre
# is dropped until the sector lands on the visible band, exactly the §1 move.
for _r, _cy in ((24, 96), (48, 96), (95, 96), (190, 280), (200, 352)):
    CASES.append((f"lad_r{_r}", f"CIRCLE(128,{_cy}),{_r},15,1.1,2.04",
                  dict(cx=128, cy=_cy, r=_r, start=1.1, end=2.04),
                  f"r-ladder at the SAME angles as arcctl_r200 (1.1, 2.04), "
                  f"r={_r}, centre y={_cy}"))


def prog(stmts):
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


def run(machine, ops):
    # ⚠️ THE FIRST TUPLE ELEMENT IS THE DELIVERY MODE, NOT A LABEL.
    specs = [("stored", prog([LINIT, ops]))]
    return omsx_repl.run_cases(machine, specs, batch=False,
                               capture=("vram_segs", PLANE), step=12.0)[0]


def reduce_hex(hexs):
    if not hexs:
        return None
    b = bytes.fromhex(hexs)
    if len(b) != 6144:
        return ("SHORT", len(b), None)
    return reduce_plane(b)


def main():
    print("=== D-ARCMASK: the reference's boundary ray, swept ===")
    print(f"ref={REF}  zb={ZB}\n")

    print("--- ZEROBAS PREDICTIONS (written before any boot; whole plane) ---")
    pred = {}
    for lbl, ops, kw, why in CASES:
        pred[lbl] = None if kw is None else reduce_plane(plane(M.draw(**kw)))
        print(f"  {lbl:14} {ops:38} {pred[lbl]}")
    print()
    if "--dry" in sys.argv:
        print("--dry: predictions only, no emulator booted")
        return 0

    print("--- MEASURED ---")
    out, zmiss, diff = {}, 0, 0
    for lbl, ops, kw, why in CASES:
        rh, zh = run(REF, ops), run(ZB, ops)
        rr, zz = reduce_hex(rh), reduce_hex(zh)
        out[lbl] = dict(ops=ops, ref=rh, zb=zh)
        if kw is not None:
            ok = zz == pred[lbl]
            zmiss += not ok
            flag = "" if ok else "  🔴 ZEROBAS MISS -- RIG SUSPECT"
        else:
            ok, flag = True, ""
        v = "agree" if rr == zz else "DIFF "
        diff += v == "DIFF "
        print(f"  {v} {lbl:14} {ops}{flag}")
        print(f"        ref = {rr}")
        print(f"        zb  = {zz}")
        if kw is not None and not ok:
            print(f"        predicted zb = {pred[lbl]}")
    with open(OUT, "w") as f:
        json.dump(out, f)
    print()
    print(f"=== {diff} DIFF / {len(CASES)} rows;  zerobas prediction misses: "
          f"{zmiss} ===")
    print(f"=== planes dumped to {OUT} ===")
    return 1 if zmiss else 0


if __name__ == "__main__":
    sys.exit(main())
