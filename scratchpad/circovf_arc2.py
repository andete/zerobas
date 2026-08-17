#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCOVF -- the arc mask, on rows that are NOT vacuous.

scratchpad/circovf_arc.py put four large-radius arcs at the screen centre and
four of them came back BOTH BLANK. Both-blank is not agreement (D-CIRCDOM §4.2:
`r200`/`r255` agreed for exactly that wrong reason) -- those rows say nothing
about the widened cross product, and a row set whose middle is vacuous cannot
carry a verdict.

Same fix as §1 of the slice: move the centre off screen along the MINOR axis so
the overflowing part of the figure is visible, then mask an ARC out of the part
that shows. At CIRCLE(128,445),284 the visible cap is |dy| in 254..284 with
|dx| <= 128, which in screen convention (Vy = -sin) is theta in about
[1.10, 2.04] -- so an arc inside that window draws, and its cross products reach
284*284 = 80656, past a 16-bit word.

    python3 -u scratchpad/circovf_arc2.py
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

CASES = [
    ("arcovf_right", "CIRCLE(128,445),284,15,1.1,1.5708",
     "right half of the visible cap. Components reach 284, so the cross "
     "products reach 80656 -- past a 16-bit word."),
    ("arcovf_left", "CIRCLE(128,445),284,15,1.5708,2.04",
     "left half of the same cap: the complementary sector, so between them "
     "they should reconstruct the full-circle row's 256 px."),
    ("arcovf_span", "CIRCLE(128,445),284,15,1.1,2.04",
     "the whole visible window as ONE arc -- must equal the full-circle row "
     "ovf_r284_top (256 px, sha1 05f66505) if the mask is right."),
    ("arcovf_wrap", "CIRCLE(128,445),284,15,2.04,1.1",
     "the SAME two angles reversed: sweep > pi, the GFX_ARCBIG branch, and "
     "the complement of arcovf_span -- so it must be BLANK on this window."),
    ("arcctl_r200", "CIRCLE(128,352),200,15,1.1,2.04",
     "GREEN CONTROL: same shape and geometry, r=200 so every cross product "
     "fits 16 bits on both arithmetics (200*200 = 40000)."),
    ("arcctl_r15", "CIRCLE(60,60),15,15,0,1.57",
     "SECOND GREEN CONTROL -- the gate's own arc_0_hpi row, verbatim."),
]


def prog(stmts):
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


def red(hexs):
    if not hexs:
        return None
    b = bytes.fromhex(hexs)
    return ("SHORT", len(b), None) if len(b) != 6144 else reduce_plane(b)


def main():
    print("=== D-CIRCOVF: the arc mask on rows that actually draw ===")
    print(f"ref={REF}  zb={ZB}\n")
    bad = vac = 0
    for lbl, ops, why in CASES:
        specs = [("stored", prog([LINIT, ops]))]
        r = red(omsx_repl.run_cases(REF, specs, batch=False,
                                    capture=("vram_segs", PLANE), step=25.0)[0])
        z = red(omsx_repl.run_cases(ZB, specs, batch=False,
                                    capture=("vram_segs", PLANE), step=25.0)[0])
        if r is None or z is None:
            v, noread = "NOREAD", True
        else:
            v, noread = ("agree" if r == z else "DIFF "), False
        blank = (r and r[0] == 0 and z and z[0] == 0)
        vac += bool(blank) and lbl != "arcovf_wrap"
        bad += (v == "DIFF ") or noread
        tag = ""
        if blank:
            tag = ("  (blank BY DESIGN -- the complement)"
                   if lbl == "arcovf_wrap" else "  ⚠️ VACUOUS: both blank")
        print(f"  {v:6} {lbl:13} {ops}{tag}")
        print(f"        ref = {r}")
        print(f"        zb  = {z}")
        print(f"        why: {why}")
    print()
    print(f"=== divergences/noreads: {bad} / {len(CASES)};  "
          f"unintended vacuous rows: {vac} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
