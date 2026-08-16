#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCDOM round 3 -- the OTHER half of the branch my own fix changed.

D-CIRCDOM changed cpt_asp_scale256 from `call cpt_round` to `call flt_to_int16`
on the strength of 3/3 discriminating aspects and 2/2 byte-identical controls --
ALL of them `aspect < 1`, i.e. the cpt_asp_le1 branch where minor_ratio = aspect
lands in ARGA directly.

The `aspect >= 1` branch reaches the SAME call, but only after computing
minor_ratio = 1/aspect through fp_div. No measured row distinguishes floor from
round-half-up there: the gate's two such rows are `,,,2` (1/2 -> 128.0 exact)
and `,,,3` (1/3 -> 85.33, floor == round). So the fix ships a rule at a caller
where the rule was never read -- knife your own justification.

Two things can be true and they are separable:
  * the TRUNCATION is right on this branch too   -> the discriminators agree
  * fp_div's precision matches the reference's   -> a prerequisite for the above

If a discriminator DIVERGES, the cause is fp_div, not the rounding: the
truncation is the same instruction on both branches.

ASPMAJ=1 here (y-major), so the MINOR axis is X -- the half-axis to read off the
bounding box is horizontal, not vertical, and Y is the unscaled radius.

    python3 -u scratchpad/circdom_char3.py
"""
from __future__ import annotations

import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

LINIT = "COLOR15,4,7:SCREEN2"
PLANE = [(0, 6144)]
R = 128


def prog(stmts):
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


def half(v, a):
    return (((v * a) & 0xFFFF) + 128) >> 8


# label, aspect literal, 1/aspect*256 exact, floor, round-half-up, why
CASES = [
    ("a17_r128", "1.7", 256 / 1.7, 150, 151,
     "DISCRIMINATOR: 1/1.7*256 = 150.59, floor 150 vs round 151"),
    ("a13_r128", "1.3", 256 / 1.3, 196, 197,
     "SECOND DISCRIMINATOR, independent aspect: 196.92, floor 196 vs round 197"),
    ("a11_r128", "1.1", 256 / 1.1, 232, 233,
     "THIRD: 232.73, floor 232 vs round 233 -- three, so a single agreement "
     "cannot carry the branch on its own"),
    ("a2_r128", "2", 128.0, 128, 128,
     "CONTROL: 1/2*256 is EXACT (128), both models predict the same picture. "
     "Green here says the rig draws a y-major ellipse identically at r=128."),
    ("a4_r128", "4", 64.0, 64, 64,
     "SECOND CONTROL, exact again (64)"),
]


def _reduce(hexs):
    if not hexs:
        return None
    b = bytes.fromhex(hexs)
    if len(b) != 6144:
        return ("SHORT", len(b))
    n = 0
    x0 = y0 = 10 ** 6
    x1 = y1 = -1
    for i, v in enumerate(b):
        if not v:
            continue
        row, rest = i // 256, i % 256
        col, y = rest // 8, row * 8 + (rest % 8)
        for bit in range(8):
            if v & (0x80 >> bit):
                n += 1
                x = col * 8 + bit
                x0, x1 = min(x0, x), max(x1, x)
                y0, y1 = min(y0, y), max(y1, y)
    return (n, None if x1 < 0 else (x0, y0, x1, y1), hashlib.sha1(b).hexdigest()[:8])


def main():
    print("=== D-CIRCDOM round 3: the aspect >= 1 branch (minor axis is X) ===")
    bad = 0
    for lbl, asp, exact, fl, rd, why in CASES:
        pf, pr = half(R, fl), half(R, rd)
        ops = f"CIRCLE(128,96),{R},15,,,{asp}"
        specs = [("stored", prog([LINIT, ops]))]
        rr = _reduce(omsx_repl.run_cases(REF, specs, batch=False,
                                         capture=("vram_segs", PLANE))[0])
        zz = _reduce(omsx_repl.run_cases(ZB, specs, batch=False,
                                         capture=("vram_segs", PLANE))[0])
        ok = rr is not None and rr == zz
        bad += not ok
        tag = "   (models AGREE -- control)" if pf == pr else ""
        print(f"  {'agree' if ok else 'DIFF ':5} {lbl:10} aspect={asp:4} "
              f"1/a*256={exact:7.2f}  floor={fl:3d}->xhalf {pf:3d}   "
              f"round={rd:3d}->xhalf {pr:3d}{tag}")
        for t, red in (("ref", rr), ("zb ", zz)):
            xh = (128 - red[1][0], red[1][2] - 128) if (red and red[1]) else None
            print(f"        {t}={red}   x-half(left,right)={xh}")
        print(f"        why: {why}")
    print()
    print(f"=== divergences: {bad} / {len(CASES)} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
