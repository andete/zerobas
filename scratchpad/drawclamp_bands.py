#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DRAWCLAMP -- prove each PROPOSED GATE BAND can see the fix.

G3 shipped three off-screen LINE rows that were all blind, and D-SPOKELINE only
found that out by re-deriving them. So before any row goes into
basic_probe_graphics.py, its band is scored against the two BANKED planes:
`drawclamp_char.pre.json` (zerobas clipping) and `.post.json` (zerobas clamping,
== the reference). A band whose bytes are equal in both would be green forever
while saying nothing.

    python3 -u scratchpad/drawclamp_bands.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))

from basic_probe_graphics import band_segs  # noqa: E402

# gate label, probe row, x-range, y-range
BANDS = [
    ("clampD_diag",   "dm_both_off",    (0, 255),   (0, 191)),
    ("clampD_corner", "dm_alloff",      (232, 255), (168, 191)),
    ("clampD_start",  "dm_start_off_R", (0, 255),   (0, 88)),
    ("clampD_dir",    "dm_dir_diag",    (200, 255), (0, 104)),
    ("clampD_scaled", "dm_scaled_off",  (96, 255),  (16, 104)),
    ("clampD_rot",    "dm_rot_off",     (96, 144),  (0, 104)),
    ("clampD_two",    "dm_two_seg",     (24, 255),  (24, 152)),
    # the deliberate control: vacuous by geometry, and it must STAY green
    ("ctlD_clipleft", "gate_clip_left", (0, 24),    (0, 12)),
]


def slice_band(plane_hex, segs):
    b = bytes.fromhex(plane_hex)
    return b"".join(b[a:a + n] for a, n in segs)


def main() -> int:
    pre = json.load(open(os.path.join(HERE, "drawclamp_char.pre.json")))
    post = json.load(open(os.path.join(HERE, "drawclamp_char.post.json")))
    bad = 0
    print("=== can each proposed gate band SEE the fix? ===")
    print("    (pre = zerobas clipping, post = zerobas clamping = the reference)\n")
    for label, row, xr, yr in BANDS:
        segs = band_segs(xr, yr)
        a = slice_band(pre[row]["zb"], segs)
        b = slice_band(post[row]["zb"], segs)
        r = slice_band(post[row]["ref"], segs)
        nbytes = len(a)
        sees = a != b
        matches_ref = b == r
        ctl = label.startswith("ctlD_")
        ok = (not sees) if ctl else sees
        bad += not (ok and matches_ref)
        verdict = ("VACUOUS (as designed)" if ctl and not sees
                   else "SEES THE FIX" if sees
                   else "🔴 BLIND -- green before AND after")
        print(f"  {'ok ' if ok and matches_ref else 'BAD'} {label:14} "
              f"{nbytes:4d}B  {verdict}"
              f"{'' if matches_ref else '   🔴 post != reference'}")
    print(f"\n=== unusable bands: {bad} ===")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
