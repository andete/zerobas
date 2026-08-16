#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCDOM characterization -- what a CIRCLE with r > 255 actually draws.

The `gfx_circ_scale` header (sub/graphics.asm:1362) claims a bounded domain
"|v|*ASPS assumed <=65535 (true for |v|<=255, ASPS<=256 -- the blessed r<=255
domain)", and docs/fixpoint8000-msx1-sweep.md §4.2 rests FOUR `$8000`
unreachability verdicts on it. scratchpad/circdom_scan.py measured the corpus:
the largest radius ever DRAWN anywhere in the tree is 200 (a scratchpad
error-funnel row), the largest a GATE draws is 20, and no row anywhere compares
the PIXELS of a circle with r > 20.

This asks the references directly. Two phases on BOTH machines:

  PHASE 1  behaviour: is a radius > 255 even accepted? (ON ERROR funnel)
  PHASE 2  the WHOLE SCREEN-2 pattern plane (all 6144 bytes -- no hand-picked
           window, so the readout cannot be blind to its own subject), reduced
           to popcount + bounding box + digest, compared ref vs zb.

    python3 -u scratchpad/circdom_char.py
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
PLANE = [(0, 6144)]            # the ENTIRE SCREEN-2 pattern plane


def prog(stmts):
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


# ---------------------------------------------------------------------------
# The row set. `why` states, BEFORE the run, what the row is for -- a row whose
# two sides agree can agree for the wrong reason, so each control names the
# reason it is supposed to be green.
#
# ASPS = round(minor_ratio*256), minor_ratio = aspect if aspect<1 else 1/aspect.
# The header's bound is on the PRODUCT |v|*ASPS, where v is the raw octant
# offset on the MINOR axis, |v| <= r. Overflow of gfx_mul16u starts at
# |v|*ASPS >= 65536.
# ---------------------------------------------------------------------------
CASES = [
    # label,           ops,                                 ASPS, max product, why
    ("r20_base", "CIRCLE(128,96),20,15", 256, 20 * 256,
     "the corpus ceiling: the largest radius any GATE draws"),
    ("r200", "CIRCLE(128,96),200,15", 256, 200 * 256,
     "largest radius drawn ANYWHERE in the tree; product 51200 still fits"),
    ("r255", "CIRCLE(128,96),255,15", 256, 255 * 256,
     "the last radius the stated bound blesses; product 65280, fits by 256"),
    ("r256", "CIRCLE(128,96),256,15", 256, 256 * 256,
     "PRODUCT = 65536 EXACTLY -- the first value that cannot fit in 16 bits"),
    ("r257", "CIRCLE(128,96),257,15", 256, 257 * 256,
     "one past the wrap"),
    ("r300", "CIRCLE(128,96),300,15", 256, 300 * 256,
     "well past the wrap; scale(300) should wrap to 44, landing ON screen"),
    ("r1000", "CIRCLE(128,96),1000,15", 256, 1000 * 256,
     "far outside; the header says 'may mis-rasterise, never crash'"),
    # --- aspect: the product bound and the radius bound come apart here -----
    ("r300_a03", "CIRCLE(128,96),300,15,,,.3", 77, 300 * 77,
     "THE DISCRIMINATOR: r=300 is OUTSIDE the stated r<=255 domain, but the "
     "product 23100 FITS. If the real bound is the product, this AGREES."),
    ("r200_a03", "CIRCLE(128,96),200,15,,,.3", 77, 200 * 77,
     "green control for r300_a03: same aspect, radius inside the stated domain, "
     "and VISIBLY drawn (not blank) -- so a PASS here is not 'both empty'"),
    ("r300_a09", "CIRCLE(128,96),300,15,,,.9", 230, 300 * 230,
     "product 69000 overflows with a radius the r300_a03 row shows is otherwise fine"),
    # r=700 at aspect .3 was DROPPED before the run: dy would be 207 at the only
    # QY that keeps |dx|<=128, so BOTH machines draw a blank screen and the row
    # cannot discriminate anything (D-NEG8K's vacuous-discriminator lesson).
    # Aspect .137 (ASPS=35) keeps the minor axis at ~94 px -- ON screen -- while
    # the product 24500 still fits. THAT is a row capable of speaking.
    ("r700_a0137", "CIRCLE(128,96),700,15,,,.137", 35, 700 * 35,
     "SHARPEST DISCRIMINATOR: r=700 is 2.7x outside the stated r<=255 domain, "
     "product 24500 FITS, and the ellipse is VISIBLE on both sides"),
    ("r1900_a0137", "CIRCLE(128,96),1900,15,,,.137", 35, 1900 * 35,
     "same aspect as r700_a0137, only the radius moved: product 66500 OVERFLOWS"),
    ("r900_a03", "CIRCLE(128,96),900,15,,,.3", 77, 900 * 77,
     "product 69300 overflows -- same aspect as r700_a03, only the radius moved"),
]

BEHAV = [
    (lbl, ["ON ERROR GOTO 40", f"SCREEN2:{ops}",
           'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'])
    for lbl, ops, _, _, _ in CASES
]


def _answer(raw, tag="K|E"):
    if not raw:
        return None
    txt = " ".join("".join(raw).split())
    m = re.search(r"(K|E[ \d\-]*)", txt)
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else None


def reduce_plane(hexs):
    """popcount, bounding box (x0,y0,x1,y1) in pixels, and a digest."""
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
        # SCREEN 2 pattern layout: addr = (y>>3)*256 + (x>>3)*8 + (y&7)
        row = i // 256
        rest = i % 256
        col = rest // 8
        y = row * 8 + (rest % 8)
        for bit in range(8):
            if v & (0x80 >> bit):
                n += 1
                x = col * 8 + bit
                x0, x1 = min(x0, x), max(x1, x)
                y0, y1 = min(y0, y), max(y1, y)
    box = None if x1 < 0 else (x0, y0, x1, y1)
    return (n, box, hashlib.sha1(b).hexdigest()[:8])


def phase1():
    print("=== PHASE 1: is the radius accepted at all? (ON ERROR funnel) ===")
    specs = [("stored", body) for _, body in BEHAV]
    ref = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW", "CLS"))
    zb = omsx_repl.run_cases(ZB, specs, batch=True, reset=("NEW", "CLS"))
    bad = 0
    for (lbl, _), r, z in zip(BEHAV, ref, zb):
        ra, za = _answer(r), _answer(z)
        ok = ra is not None and ra == za
        bad += not ok
        print(f"  {'agree' if ok else 'DIFF ':5} {lbl:12} ref={str(ra):8} zb={str(za):8}")
    return bad


def phase2():
    print()
    print("=== PHASE 2: the WHOLE 6144-byte pattern plane, ref vs zb ===")
    print("     (popcount, bbox=(x0,y0,x1,y1), sha1[:8]; screen is 256x192)")
    bad = 0
    for lbl, ops, asps, prod, why in CASES:
        specs = [("stored", prog([LINIT, ops]))]
        r = omsx_repl.run_cases(REF, specs, batch=False, capture=("vram_segs", PLANE))[0]
        z = omsx_repl.run_cases(ZB, specs, batch=False, capture=("vram_segs", PLANE))[0]
        rr, zz = reduce_plane(r), reduce_plane(z)
        ok = rr is not None and rr == zz
        bad += not ok
        ovf = "OVERFLOWS" if prod > 65535 else "fits     "
        print(f"  {'agree' if ok else 'DIFF ':5} {lbl:12} ASPS={asps:3d} maxprod={prod:6d} {ovf}")
        print(f"        ref={rr}")
        print(f"        zb ={zz}")
        print(f"        why: {why}")
    return bad


def main():
    b1 = phase1()
    b2 = phase2()
    print()
    print(f"=== phase1 disagreements: {b1} / {len(BEHAV)} ===")
    print(f"=== phase2 disagreements: {b2} / {len(CASES)} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
