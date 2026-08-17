#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCOVF step 3 -- THE POSITIVE ORACLE, measured.

D-CIRCDOM established "zerobas is wrong when |v|*ASPS >= 65536". It did NOT
establish what RIGHT looks like: in all six of its DIFF rows the reference draws
0 px on screen, so they say only "zerobas paints where the reference paints
nothing". A fix written against that is written against an ABSENCE.

The geometry that blocked it, and the one move that unblocks it: an overflowing
point has a scaled minor offset >= 256, and the screen is 192 tall, so no
overflowing point can be on screen while the CENTRE is. Move the centre off
screen along the MINOR axis and the overflowing part of the figure lands on it.

Every row here is derived by scratchpad/circovf_search.py from the model in
scratchpad/circovf_calib.py, which reproduces all 22 of D-CIRCDOM §4.1's
published readings from arithmetic alone -- including the two its own
hand-written predictions missed (r257 at 88 px, r1000 blank).

FOUR HYPOTHESES are predicted per row, so the run can say WHICH the reference
implements rather than only that zerobas differs:

    H_EXACT  full-width product           (v*ASPS + 128) >> 8
    H_SAT    product saturates at 65535   (min(v*ASPS,65535) + 128) >> 8
    H_WRAP   zerobas today                ((v*ASPS & 0xFFFF) + 128) >> 8 & 0xFF
    H_BLANK  the reference refuses / draws nothing on screen

⚠️ Predictions are the WHOLE 6144-byte plane (popcount, bbox, sha1), not the
bbox summary -- D-CIRCDOM's K-CD3 missed because a prediction was computed off
the bbox while the row compares every byte.

⚠️ Each row is checked for DISCRIMINATING POWER before it is run: a row whose
hypotheses all predict the same plane is vacuous and is reported as such rather
than counted as agreement. That is what `r200` and `r255` turned out to be.

    python3 -u scratchpad/circovf_char.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, HERE)

import omsx_repl                                            # noqa: E402
from circovf_calib import mirrors, octant, plane, reduce_plane  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                    "C-BIOS_MSX1_EU_REPACK_DISK")

LINIT = "COLOR15,4,7:SCREEN2"
PLANE = [(0, 6144)]
W, H = 256, 192


def prog(stmts):
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


# --- the four scale hypotheses -------------------------------------------
def h_exact(v, a):
    o = (abs(v) * a + 128) >> 8
    return -o if v < 0 else o


def h_sat(v, a):
    o = (min(abs(v) * a, 0xFFFF) + 128) >> 8
    return -o if v < 0 else o


def h_wrap(v, a):
    o = ((((abs(v) * a) & 0xFFFF) + 128) >> 8) & 0xFF
    return -o if v < 0 else o


HYPS = (("H_EXACT", h_exact), ("H_SAT", h_sat), ("H_WRAP", h_wrap))


def predict(cx, cy, r, asps, maj, scale):
    px = set()
    for qx, qy in octant(r):
        for dx, dy in mirrors(qx, qy):
            if maj:
                sx, sy = scale(dx, asps), dy
            else:
                sx, sy = dx, scale(dy, asps)
            x, y = cx + sx, cy + sy
            if 0 <= x < W and 0 <= y < H:
                px.add((x, y))
    return reduce_plane(plane(px))


BLANK = reduce_plane(plane(set()))

# label, BASIC ops, cx, cy, r, ASPS, ASPMAJ, why
CASES = [
    # --- A. default aspect (ASPS=256): the plain-CIRCLE path, no aspect field.
    ("ovf_r284_top", "CIRCLE(128,445),284", 128, 445, 284, 256, 0,
     "⭐ THE ORACLE. Centre 254 px BELOW the screen, so the circle's TOP cap "
     "is what shows -- and at r=284 the cap straddles the |v|=256 overflow "
     "threshold. BOTH machines draw: zerobas the non-overflowing sliver, the "
     "reference (if its product is wide) the whole cap. The first row in the "
     "tree's history where an overflowing CIRCLE point can be SEEN."),
    ("ovf_r300_top", "CIRCLE(128,445),300", 128, 445, 300, 256, 0,
     "same centre, deeper into the overflow: every on-screen point overflows, "
     "so zerobas should go blank while the reference still draws a full cap. "
     "The exact inverse of D-CIRCDOM's six rows."),
    ("ctl_r255_top", "CIRCLE(128,445),255", 128, 445, 255, 256, 0,
     "GREEN CONTROL, same centre. |v| <= 255 so |v|*256 <= 65280 -- the "
     "product CANNOT overflow. All three hypotheses predict one plane. A pass "
     "says the off-screen centre is accepted and the rig clips a cap "
     "identically on both machines; without it, a blank zerobas above is "
     "explained equally well by 'the reference refused y=445'."),
    ("ctl_r200_top", "CIRCLE(128,352),200", 128, 352, 200, 256, 0,
     "SECOND GREEN CONTROL at a second off-screen centre, well inside the "
     "product bound. One control can be green for the wrong reason."),
    # --- B. explicit aspect < 1 -> x-major, minor is Y (a second code path).
    ("ovf_a05_r528", "CIRCLE(128,448),528,,,,.5", 128, 448, 528, 128, 0,
     "ASPS=128 (trunc(.5*256)), threshold |v| >= 512. Reaches the same wrap "
     "through cpt_asp_le1 rather than the default, so a fix that only "
     "special-cases ASPS=256 is caught here."),
    ("ctl_a05_r500", "CIRCLE(128,346),500,,,,.5", 128, 346, 500, 128, 0,
     "GREEN CONTROL for the aspect path: r=500 < 512, product 64000 FITS. "
     "Byte-identical expected, at a radius 2x outside the retired r<=255 claim."),
    # --- C. explicit aspect > 1 -> y-major, minor is X. The OTHER branch:
    # D-CIRCDOM round 3 shipped a fix on aspect<1 evidence only and the other
    # branch turned out to be wrong in exactly the same direction.
    ("ovf_a2_r528", "CIRCLE(262,96),528,,,,2", 262, 96, 528, 128, 1,
     "y-major: the MINOR axis is X, so the centre moves off screen "
     "HORIZONTALLY. Same ASPS=128 and same threshold, different axis and a "
     "different marshalling branch (fp_div, not ARGA direct). cx tuned so BOTH "
     "machines draw and they still differ -- zerobas paints MORE here (121 px "
     "of wrapped arc against the reference's 71), the opposite direction to "
     "the ovf rows above."),
    ("ctl_a2_r500", "CIRCLE(260,96),500,,,,2", 260, 96, 500, 128, 1,
     "GREEN CONTROL on the y-major branch, product 64000 fits, same shape and "
     "the same off-screen-centre geometry as the row above it."),
]


def run(machine, ops, label):
    # ⚠️ THE FIRST ELEMENT IS THE DELIVERY MODE, NOT A LABEL. Round 1 passed the
    # row label here, which run_cases reads as "not stored" -> DIRECT mode: each
    # line typed at the prompt, and prog()'s trailing `GOTO` becomes Undefined
    # line number. On the VG-8020 an error at the prompt drops SCREEN 2 back to
    # text and the font overwrites the pattern plane -- 5007 px of font, bbox
    # (0,0,255,127), IDENTICALLY for every row including the controls. zerobas is
    # insensitive to it and read correctly throughout, so a ONE-SIDED APPARATUS
    # FAILURE presented as 8/8 divergence. The four green controls are what
    # caught it: rows written to be byte-identical, that weren't.
    specs = [("stored", prog([LINIT, ops]))]
    return omsx_repl.run_cases(machine, specs, batch=False,
                               capture=("vram_segs", PLANE), step=25.0)[0]


def reduce_hex(hexs):
    if not hexs:
        return None
    b = bytes.fromhex(hexs)
    if len(b) != 6144:
        return ("SHORT", len(b), None)
    return reduce_plane(b)


def main():
    print("=== D-CIRCOVF: the positive oracle ===")
    print(f"ref={REF}  zb={ZB}\n")

    # --- predictions first, and a discriminating-power check on each row ---
    preds = {}
    print("--- PREDICTIONS (written before any boot; whole 6144-byte plane) ---")
    for lbl, ops, cx, cy, r, asps, maj, why in CASES:
        p = {n: predict(cx, cy, r, asps, maj, f) for n, f in HYPS}
        p["H_BLANK"] = BLANK
        preds[lbl] = p
        distinct = len({v for v in p.values()})
        print(f"  {lbl:14} {ops}")
        for n in ("H_EXACT", "H_SAT", "H_WRAP", "H_BLANK"):
            print(f"      {n:8} {p[n]}")
        print(f"      DISCRIMINATING POWER: {distinct} distinct planes"
              f"{'  ⚠️ VACUOUS ROW' if distinct == 1 else ''}")
        print(f"      why: {why}")
    print()
    if "--dry" in sys.argv:
        print("--dry: predictions only, no emulator booted")
        return 0

    print("--- MEASURED ---")
    bad = 0
    for lbl, ops, cx, cy, r, asps, maj, why in CASES:
        rr = reduce_hex(run(REF, ops, lbl))
        zz = reduce_hex(run(ZB, ops, lbl))
        p = preds[lbl]

        def name(red):
            if red is None:
                return "NOREAD"
            hits = [n for n in ("H_EXACT", "H_SAT", "H_WRAP", "H_BLANK")
                    if p[n] == red]
            return "+".join(hits) if hits else "UNMODELLED"

        agree = rr is not None and rr == zz
        bad += not agree
        print(f"  {'agree' if agree else 'DIFF ':5} {lbl:14} {ops}")
        print(f"        ref = {rr}   -> {name(rr)}")
        print(f"        zb  = {zz}   -> {name(zz)}")
    print()
    print(f"=== divergences: {bad} / {len(CASES)} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
