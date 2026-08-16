#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCDOM round 2 -- the three round-1 MISSES, chased.

Round 1 (scratchpad/circdom_char.py) predicted 6 DIFF / 6 AGREE and scored 9
exact, 3 missed:

  * `r1000` was predicted DIFF and AGREED (both blank). The model "the product
    wraps, therefore pixels appear on screen" does not follow: with ASPS=256 the
    wrap is exactly `v mod 256`, and wherever that lands on screen the UNSCALED
    major-axis offset is already off screen, so the clip eats it. Reached by
    analogy, wrong -- traced through the source it is arithmetic.
  * `r300_a03` and `r200_a03` were predicted AGREE and DIFFERED -- by exactly one
    pixel of minor half-axis, at radii where the product FITS. That is a second
    divergence with nothing to do with the overflow.

Two data points are not a rule. This round asks whether the one-pixel divergence
is real, reproducible INSIDE the blessed r<=255 domain, and whether it tracks
`floor(aspect*256)` vs `round(aspect*256)`.

    python3 -u scratchpad/circdom_char2.py
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

LINIT = "COLOR15,4,7:SCREEN2"
PLANE = [(0, 6144)]


def prog(stmts):
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


def scale(v, a):
    """The tenant's own formula: (|v|*ASPS + 128) >> 8, 16-bit truncated mul."""
    return (((v * a) & 0xFFFF) + 128) >> 8


# label, ops, aspect*256 exact, floor, round-half-up, r, why
ASPECT_CASES = [
    ("a03_r128", "CIRCLE(128,96),128,15,,,.3", 76.8, 76, 77, 128,
     "floor 76 != round 77; r=128 is INSIDE the blessed domain and fully on screen"),
    ("a055_r128", "CIRCLE(128,96),128,15,,,.55", 140.8, 140, 141, 128,
     "second independent aspect where floor != round, same radius"),
    ("a07_r128", "CIRCLE(128,96),128,15,,,.7", 179.2, 179, 179, 128,
     "GREEN CONTROL: floor == round here, so the two models predict the SAME "
     "picture. A pass here says the rig can draw this shape identically."),
    ("a025_r128", "CIRCLE(128,96),128,15,,,.25", 64.0, 64, 64, 128,
     "GREEN CONTROL: aspect*256 is EXACT (64), no rounding decision at all"),
    ("a01_r255", "CIRCLE(128,96),255,15,,,.1", 25.6, 25, 26, 255,
     "floor 25 != round 26; needs r=255 for the 1/256 to reach a whole pixel"),
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


# --- the four round-1 phase-1 rows that returned None on BOTH sides ----------
# Both-None is NOT a divergence, it is a NO READING: the batched step budget is
# too short for a long draw. Re-asked boot-per-case with a real hold.
SLOW = [
    ("r1000", "CIRCLE(128,96),1000,15"),
    ("r700_a0137", "CIRCLE(128,96),700,15,,,.137"),
    ("r1900_a0137", "CIRCLE(128,96),1900,15,,,.137"),
    ("r900_a03", "CIRCLE(128,96),900,15,,,.3"),
    ("r32767", "CIRCLE(128,96),32767,15"),
]


def _answer(raw):
    if not raw:
        return None
    txt = " ".join("".join(raw).split())
    m = re.search(r"(K|E[ \d\-]*)", txt)
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else None


def phase_slow():
    print("=== PHASE S: the four round-1 NO-READINGS, re-asked boot-per-case ===")
    bad = 0
    for lbl, ops in SLOW:
        body = ["ON ERROR GOTO 40", f"SCREEN2:{ops}",
                'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END']
        r = omsx_repl.run_cases(REF, [("stored", body)], batch=False, step=25.0)[0]
        z = omsx_repl.run_cases(ZB, [("stored", body)], batch=False, step=25.0)[0]
        ra, za = _answer(r), _answer(z)
        state = "agree" if (ra is not None and ra == za) else (
            "NOREAD" if (ra is None and za is None) else "DIFF ")
        bad += state == "DIFF "
        print(f"  {state:6} {lbl:14} ref={str(ra):8} zb={str(za):8}")
    return bad


def phase_aspect():
    print()
    print("=== PHASE R: is the one-pixel minor-axis divergence real? ===")
    print("     predicted half-axis under each model, then the measurement")
    bad = 0
    for lbl, ops, exact, fl, rd, r, why in ASPECT_CASES:
        pf, pr = scale(r, fl), scale(r, rd)
        specs = [("stored", prog([LINIT, ops]))]
        rr = _reduce(omsx_repl.run_cases(REF, specs, batch=False,
                                         capture=("vram_segs", PLANE))[0])
        zz = _reduce(omsx_repl.run_cases(ZB, specs, batch=False,
                                         capture=("vram_segs", PLANE))[0])
        ok = rr is not None and rr == zz
        bad += not ok
        print(f"  {'agree' if ok else 'DIFF ':5} {lbl:11} aspect*256={exact:7.2f} "
              f"floor={fl:3d}->half {pf:3d}   round={rd:3d}->half {pr:3d}"
              f"{'   (models AGREE -- control)' if pf == pr else ''}")
        for tag, red in (("ref", rr), ("zb ", zz)):
            half = None
            if red and red[1]:
                half = (96 - red[1][1], red[1][3] - 96)
            print(f"        {tag}={red}   half-axis(up,down)={half}")
        print(f"        why: {why}")
    return bad


def main():
    b1 = phase_slow()
    b2 = phase_aspect()
    print()
    print(f"=== phase S divergences: {b1} / {len(SLOW)} ===")
    print(f"=== phase R divergences: {b2} / {len(ASPECT_CASES)} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
