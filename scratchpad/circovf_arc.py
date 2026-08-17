#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCOVF -- the COUPLED site: the arc mask at a large radius.

D-CIRCDOM predicted one coupling ("fixing the overflow makes `$8000` reachable
at gfx_circ_scale's re-negate"). That one turned out NOT to bind: with ASPS=256
handled as the identity, gfx_mul16r's output tops out at 32639 and the identity
arm at 32767, so the fixed point is never met (scratchpad/circovf_asmsim.py,
600k cases). A DIFFERENT coupling, which nobody predicted, does bind:

  gfx_cross_ge0's two 16-bit products were SAFE BEFORE THIS SLICE precisely
  because their inputs were byte-bounded by the `ld l,h / ld h,0` truncation
  the slice removes. |v| <= 255 gives products <= 65025. With the scale exact,
  components reach 32767 and the products reach 2^30.

So the arc mask had to be widened to 32-bit in the same slice -- not because it
was broken, but because fixing the scale would have broken it. This measures
that claim instead of asserting it: arcs at radii on both sides of where the
old 16-bit product would have wrapped, against the reference.

⚠️ No offline prediction here. The tenant's arc mask is a cross-product test
this session's model does not implement, so these rows are a straight
machine-vs-machine differential, with SMALL-radius arcs as the green controls
(they are already gate rows and must not move).

    python3 -u scratchpad/circovf_arc.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, HERE)

import omsx_repl                                    # noqa: E402
from circovf_calib import reduce_plane              # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                    "C-BIOS_MSX1_EU_REPACK_DISK")
LINIT = "COLOR15,4,7:SCREEN2"
PLANE = [(0, 6144)]


def prog(stmts):
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


def red(hexs):
    if not hexs:
        return None
    b = bytes.fromhex(hexs)
    return ("SHORT", len(b), None) if len(b) != 6144 else reduce_plane(b)


# label, ops, why
CASES = [
    ("arc_r15_ctl", "CIRCLE(60,60),15,15,0,1.57",
     "GREEN CONTROL -- this is the gate's own arc_0_hpi row, verbatim. "
     "Components <= 15, no product anywhere near 16 bits, before or after."),
    ("arc_r120_ctl", "CIRCLE(128,96),120,15,0,1.57",
     "SECOND GREEN CONTROL, 8x the radius but still |v|*|v| = 14400: inside "
     "16 bits on BOTH the old and the new arithmetic."),
    ("arc_r250_edge", "CIRCLE(128,96),250,15,0,1.57",
     "products reach 62500 -- the LAST radius the old 16-bit cross product "
     "could hold. Must agree on both arithmetics."),
    ("arc_r260_ovf", "CIRCLE(128,96),260,15,0,1.57",
     "products reach 67600: the FIRST radius where the old 16-bit cross "
     "product wraps once the scale stops truncating its inputs. Under the "
     "pre-slice build the inputs were byte-clamped so this could not happen; "
     "under a scale-only fix it would."),
    ("arc_r700_ovf", "CIRCLE(128,96),700,15,0,1.57",
     "deep in the overflow: products reach 490000, 7.5x a 16-bit word."),
    ("arc_r700_a137", "CIRCLE(128,96),700,15,0,1.57,.137",
     "the same arc on D-CIRCDOM's byte-identical ellipse -- arc mask AND "
     "minor scale together, at a radius where the scale's product fits."),
    ("arc_wrap_r300", "CIRCLE(128,96),300,15,3,1",
     "the gate's arc_wrap shape (end < start, sweep crosses 0) at a radius "
     "where the products overflow: a different branch of the mask."),
    ("arc_big_r400", "CIRCLE(128,96),400,15,-1.57,0",
     "the gate's spoke_270 shape at a large radius: exercises GFX_ARCBIG and "
     "the deferred spokes as well as the mask."),
]


def main():
    print("=== D-CIRCOVF: the arc mask at radii the old product could not hold ===")
    print(f"ref={REF}  zb={ZB}\n")
    bad = 0
    for lbl, ops, why in CASES:
        specs = [("stored", prog([LINIT, ops]))]
        r = red(omsx_repl.run_cases(REF, specs, batch=False,
                                    capture=("vram_segs", PLANE), step=25.0)[0])
        z = red(omsx_repl.run_cases(ZB, specs, batch=False,
                                    capture=("vram_segs", PLANE), step=25.0)[0])
        if r is None or z is None:
            verdict, noread = "NOREAD", True
        else:
            verdict, noread = ("agree" if r == z else "DIFF "), False
        bad += (verdict == "DIFF ") or noread
        print(f"  {verdict:6} {lbl:14} {ops}")
        print(f"        ref = {r}")
        print(f"        zb  = {z}")
        print(f"        why: {why}")
    print()
    print(f"=== divergences/noreads: {bad} / {len(CASES)} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
